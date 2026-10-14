"""Action-phase enforcement primitives — policy qualification, single-use permits, attempt ledger.

Thuần luật, không thao tác OS/network. không đọc màn hình, không gửi chat, không hotkey.
Các ngưỡng ở đây phải khớp `reference/master-plan-v3/project.json` và được kiểm
bằng `SpecConsistencyTests`; đổi ngưỡng phải đổi cả hai nơi trong cùng revision.

Không dùng module này để mở hành động thật khi chưa có gate report/app thật.
"""
from __future__ import annotations

import hashlib
import math
import threading
import uuid
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Optional

from .domain import AutonomyLevel

MAX_PERMIT_TTL_SECONDS = 10
MIN_L2_REVIEWS_FOR_L3 = 200
MIN_ACCEPTANCE_RATE_FOR_L3 = 0.70
MIN_SHADOW_TRIALS_FOR_L4 = 500
DUPLICATE_ATTEMPT_WINDOW_SECONDS_MIN = 600
ON_LOW_CONFIDENCE = ("suggest_only", "skip", "ask_confirmation", "retry_stronger")

_TOS_STATUSES = frozenset({"allowed", "unknown", "prohibited"})
_PROTECTION_STATUSES = frozenset({"absent", "present", "unknown"})
_SEND_METHODS = frozenset(
    {"none_user_types", "official_api", "uia_value_pattern", "clipboard_paste_safe"}
)
_HEX_DIGITS = frozenset("0123456789abcdef")


def _require_bool(value: object, name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name}: boolean_required")


def _require_nonnegative_int(value: object, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name}: nonnegative_integer_required")


def _require_positive_int(value: object, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}: positive_integer_required")


def _require_identity(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty_identity_required")


@dataclass(frozen=True)
class ProfilePolicy:
    enabled: bool
    read_consent: bool
    source_access_allowed: bool
    sensitive: bool
    requested: AutonomyLevel
    tos_status: str
    protection_status: str
    send_method: str
    recipient_allowlist: frozenset[str]
    disclosure: bool
    revision: str
    presence_idle_limit_seconds: float = 60

    def __post_init__(self) -> None:
        for name in (
            "enabled",
            "read_consent",
            "source_access_allowed",
            "sensitive",
            "disclosure",
        ):
            _require_bool(getattr(self, name), name)
        if not isinstance(self.requested, AutonomyLevel):
            raise ValueError("requested: autonomy_level_required")
        if self.tos_status not in _TOS_STATUSES:
            raise ValueError("tos_status_invalid")
        if self.protection_status not in _PROTECTION_STATUSES:
            raise ValueError("protection_status_invalid")
        if self.send_method not in _SEND_METHODS:
            raise ValueError("send_method_invalid")
        if not isinstance(self.recipient_allowlist, frozenset) or any(
            not isinstance(recipient, str) or not recipient.strip()
            for recipient in self.recipient_allowlist
        ):
            raise ValueError("recipient_allowlist_must_be_immutable_strings")
        _require_identity(self.revision, "revision")
        if (
            not isinstance(self.presence_idle_limit_seconds, (int, float))
            or isinstance(self.presence_idle_limit_seconds, bool)
            or not math.isfinite(self.presence_idle_limit_seconds)
            or not 10 <= self.presence_idle_limit_seconds <= 300
        ):
            raise ValueError("idle_limit_invalid")


@dataclass(frozen=True)
class Qualification:
    source_qualified: bool = False
    speaker_qualified: bool = False
    ocr_required: bool = False
    ocr_qualified: bool = False
    generation_qualified: bool = False
    action_qualified: bool = False
    decision_calibrated: bool = False
    gate_report_bound: bool = False
    l2_reviews: int = 0
    acceptance_rate: float = 0
    shadow_trials: int = 0
    shadow_misfires: int = 0
    critical_errors: int = 0

    def __post_init__(self) -> None:
        for name in (
            "source_qualified",
            "speaker_qualified",
            "ocr_required",
            "ocr_qualified",
            "generation_qualified",
            "action_qualified",
            "decision_calibrated",
            "gate_report_bound",
        ):
            _require_bool(getattr(self, name), name)
        for name in ("l2_reviews", "shadow_trials", "shadow_misfires", "critical_errors"):
            _require_nonnegative_int(getattr(self, name), name)
        if (
            not isinstance(self.acceptance_rate, (int, float))
            or isinstance(self.acceptance_rate, bool)
            or not math.isfinite(self.acceptance_rate)
            or not 0 <= self.acceptance_rate <= 1
        ):
            raise ValueError("acceptance_rate_invalid")


@dataclass(frozen=True)
class Eligibility:
    level: AutonomyLevel
    reasons: tuple[str, ...]


def effective_level(policy: ProfilePolicy, qualification: Qualification) -> Eligibility:
    if (
        not policy.enabled
        or not policy.read_consent
        or not policy.source_access_allowed
        or policy.sensitive
    ):
        return Eligibility(AutonomyLevel.L0, ("disabled_no_consent_or_sensitive",))
    cap = AutonomyLevel.L4
    reasons: list[str] = []
    if (
        not qualification.source_qualified
        or not qualification.speaker_qualified
        or (qualification.ocr_required and not qualification.ocr_qualified)
    ):
        cap = AutonomyLevel.L1
        reasons.append("source_speaker_or_ocr_not_qualified")
    if (
        policy.tos_status != "allowed"
        or policy.protection_status != "absent"
        or policy.send_method == "none_user_types"
    ):
        cap = min(cap, AutonomyLevel.L2)
        reasons.append("platform_or_adapter_caps_manual_only")
    if (
        not qualification.gate_report_bound
        or not qualification.generation_qualified
        or not qualification.action_qualified
        or qualification.critical_errors > 0
        or qualification.l2_reviews < MIN_L2_REVIEWS_FOR_L3
        or qualification.acceptance_rate < MIN_ACCEPTANCE_RATE_FOR_L3
    ):
        cap = min(cap, AutonomyLevel.L2)
        reasons.append("L3_evidence_not_ready")
    if (
        not qualification.decision_calibrated
        or not policy.disclosure
        or not policy.recipient_allowlist
        or qualification.shadow_trials < MIN_SHADOW_TRIALS_FOR_L4
        or qualification.shadow_misfires > 0
    ):
        cap = min(cap, AutonomyLevel.L3)
        reasons.append("L4_evidence_or_disclosure_not_ready")
    return Eligibility(min(policy.requested, cap), tuple(reasons))


def low_confidence_action(
    setting: str,
    *,
    hard_block: bool,
    stronger_ready: bool = False,
    budget_ok: bool = False,
    retries_used: int = 0,
) -> str:
    if setting not in ON_LOW_CONFIDENCE:
        raise ValueError("setting_invalid")
    if hard_block:
        return "blocked"
    if setting == "retry_stronger":
        if stronger_ready and budget_ok and retries_used == 0:
            return "retry_stronger"
        return "ask_confirmation"
    return setting


def draft_digest(final_text: str) -> str:
    if not isinstance(final_text, str) or not final_text.strip():
        raise ValueError("complete_nonempty_draft_required")
    return hashlib.sha256(final_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    hwnd: int
    pid: int
    process_start_token: str
    conversation_id: str
    conversation_revision: int
    source_epoch: str
    last_message_revision: int
    human_input_revision: int
    target_input_revision: int
    policy_revision: str
    cancel_generation: int
    draft_hash: str
    input_empty: bool
    target_foreground: bool
    source_valid: bool
    speaker_known: bool
    presence_known: bool
    user_idle_seconds: float
    draft_complete: bool
    guard_passed: bool
    hard_block: bool
    soft_uncertain: bool
    turn_complete: bool
    budget_ok: bool
    rate_ok: bool
    user_approved: bool
    countdown_completed: bool

    def __post_init__(self) -> None:
        _require_positive_int(self.hwnd, "hwnd")
        _require_positive_int(self.pid, "pid")
        for name in (
            "conversation_revision",
            "last_message_revision",
            "human_input_revision",
            "target_input_revision",
            "cancel_generation",
        ):
            _require_nonnegative_int(getattr(self, name), name)
        for name in (
            "process_start_token",
            "conversation_id",
            "source_epoch",
            "policy_revision",
        ):
            _require_identity(getattr(self, name), name)
        if (
            not isinstance(self.draft_hash, str)
            or len(self.draft_hash) != 64
            or any(char not in _HEX_DIGITS for char in self.draft_hash)
        ):
            raise ValueError("sha256_final_draft_required")
        for name in (
            "input_empty",
            "target_foreground",
            "source_valid",
            "speaker_known",
            "presence_known",
            "draft_complete",
            "guard_passed",
            "hard_block",
            "soft_uncertain",
            "turn_complete",
            "budget_ok",
            "rate_ok",
            "user_approved",
            "countdown_completed",
        ):
            _require_bool(getattr(self, name), name)
        if (
            not isinstance(self.user_idle_seconds, (int, float))
            or isinstance(self.user_idle_seconds, bool)
            or not math.isfinite(self.user_idle_seconds)
            or self.user_idle_seconds < 0
        ):
            raise ValueError("idle_seconds_invalid")


IDENTITY_FIELDS = (
    "hwnd",
    "pid",
    "process_start_token",
    "conversation_id",
    "conversation_revision",
    "source_epoch",
    "last_message_revision",
    "human_input_revision",
    "target_input_revision",
    "policy_revision",
    "cancel_generation",
    "draft_hash",
)


class SendPermit:
    """Single-use authorization, không thực hiện OS action.

    Actuator thật vẫn phải serialize cancellation, recheck ngay tại boundary
    điền/gửi và quản lý own-input revision sau khi điền. Lock ở đây không khóa
    Windows foreground hay server; không chứng minh atomic focus safety.
    """

    def __init__(
        self,
        expected: Snapshot,
        *,
        ttl_seconds: float = MAX_PERMIT_TTL_SECONDS,
        created_at: Optional[float] = None,
    ) -> None:
        if (
            not isinstance(ttl_seconds, (int, float))
            or isinstance(ttl_seconds, bool)
            or not math.isfinite(ttl_seconds)
            or not 0 < ttl_seconds <= MAX_PERMIT_TTL_SECONDS
        ):
            raise ValueError("permit_ttl_invalid")
        if not (
            expected.draft_complete
            and expected.guard_passed
            and expected.source_valid
            and expected.speaker_known
            and expected.turn_complete
            and expected.input_empty
            and expected.target_foreground
            and not expected.hard_block
            and not expected.soft_uncertain
        ):
            raise ValueError("guarded_current_context_required_before_permit")
        self.id = uuid.uuid4().hex
        self.expected = expected
        self.ttl_seconds = ttl_seconds
        if created_at is None:
            import time

            self.created_at = time.monotonic()
        else:
            if (
                not isinstance(created_at, (int, float))
                or isinstance(created_at, bool)
                or not math.isfinite(created_at)
            ):
                raise ValueError("permit_clock_invalid")
            self.created_at = created_at
        self._used = False
        self._lock = threading.Lock()

    def consume(
        self,
        *,
        action: str,
        current: Snapshot,
        policy: ProfilePolicy,
        qualification: Qualification,
        now: Optional[float] = None,
    ) -> tuple[bool, str]:
        with self._lock:
            if self._used:
                return False, "permit_already_used"
            # Cả failed recheck cũng burn permit: không tái dùng sau khi context đổi.
            self._used = True
            if now is None:
                import time

                tick = time.monotonic()
            else:
                tick = now
            if (
                not isinstance(tick, (int, float))
                or isinstance(tick, bool)
                or not math.isfinite(tick)
                or tick < self.created_at
            ):
                return False, "monotonic_clock_invalid"
            if tick - self.created_at >= self.ttl_seconds:
                return False, "permit_expired"
            if action not in {"fill", "send"}:
                return False, "action_invalid"
            for name in IDENTITY_FIELDS:
                if getattr(current, name) != getattr(self.expected, name):
                    return False, f"changed:{name}"
            if current.policy_revision != policy.revision:
                return False, "policy_revision_not_bound"
            required = {
                "input_empty": current.input_empty,
                "target_foreground": current.target_foreground,
                "source_valid": current.source_valid,
                "speaker_known": current.speaker_known,
                "draft_complete": current.draft_complete,
                "guard_passed": current.guard_passed,
                "turn_complete": current.turn_complete,
                "budget_ok": current.budget_ok,
                "rate_ok": current.rate_ok,
            }
            for name, satisfied in required.items():
                if not satisfied:
                    return False, f"required:{name}"
            if current.hard_block:
                return False, "hard_block"
            if current.soft_uncertain:
                return False, "low_confidence_manual_review_required"
            level = effective_level(policy, qualification).level
            if action == "fill":
                if level < AutonomyLevel.L3 or not current.user_approved:
                    return False, "L3_and_explicit_approval_required"
            else:
                if level < AutonomyLevel.L4:
                    return False, "L4_not_qualified"
                if current.conversation_id not in policy.recipient_allowlist:
                    return False, "recipient_not_allowlisted"
                if (
                    not current.presence_known
                    or current.user_idle_seconds > policy.presence_idle_limit_seconds
                ):
                    return False, "user_presence_required"
                if not current.countdown_completed:
                    return False, "countdown_incomplete"
            return True, "authorized_once_offline"


class DeliveryState(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"
    REJECTED_BEFORE_ACTION = "rejected_before_action"


@dataclass
class Attempt:
    key: str
    conversation_id: str
    draft_hash: str
    created_at: float
    state: DeliveryState = DeliveryState.PENDING
    native_delivery_id: Optional[str] = None


class AttemptLedger:
    """RAM reference. Production cần durable write-before-action + recovery.

    Chỉ metadata/hash; pending/unknown không tự retry. Việc đánh dấu confirmed
    phải có evidence adapter đã kiểm, không chỉ LLM bảo 'đã gửi'.
    """

    def __init__(self, duplicate_window_seconds: float = DUPLICATE_ATTEMPT_WINDOW_SECONDS_MIN):
        if (
            not isinstance(duplicate_window_seconds, (int, float))
            or isinstance(duplicate_window_seconds, bool)
            or not math.isfinite(duplicate_window_seconds)
            or duplicate_window_seconds < DUPLICATE_ATTEMPT_WINDOW_SECONDS_MIN
        ):
            raise ValueError("duplicate_window_invalid")
        self.duplicate_window_seconds = duplicate_window_seconds
        self._records: dict[str, Attempt] = {}
        self._lock = threading.Lock()

    def begin(
        self, key: str, conversation_id: str, draft_hash: str, *, now: float
    ) -> tuple[bool, str]:
        if not key or not conversation_id or len(draft_hash) != 64 or not math.isfinite(now):
            raise ValueError("attempt_identity_invalid")
        with self._lock:
            if key in self._records:
                return False, "attempt_key_already_exists"
            for record in self._records.values():
                if (
                    record.conversation_id == conversation_id
                    and record.draft_hash == draft_hash
                    and record.state != DeliveryState.REJECTED_BEFORE_ACTION
                    and now - record.created_at < self.duplicate_window_seconds
                ):
                    return False, "duplicate_pending_confirmed_or_unknown"
            self._records[key] = Attempt(key, conversation_id, draft_hash, now)
            return True, "reserved_before_action"

    def mark_unknown(self, key: str) -> None:
        with self._lock:
            record = self._records[key]
            if record.state != DeliveryState.PENDING:
                raise ValueError("only_pending_can_become_unknown")
            record.state = DeliveryState.UNKNOWN

    def confirm(self, key: str, native_delivery_id: str) -> None:
        if not native_delivery_id:
            raise ValueError("delivery_evidence_id_required")
        with self._lock:
            record = self._records[key]
            if record.state not in {DeliveryState.PENDING, DeliveryState.UNKNOWN}:
                raise ValueError("delivery_state_not_confirmable")
            record.state = DeliveryState.CONFIRMED
            record.native_delivery_id = native_delivery_id

    def reject_before_action(self, key: str) -> None:
        with self._lock:
            record = self._records[key]
            if record.state != DeliveryState.PENDING:
                raise ValueError("only_pending_can_be_rejected_before_action")
            record.state = DeliveryState.REJECTED_BEFORE_ACTION

    def state(self, key: str) -> DeliveryState:
        with self._lock:
            return self._records[key].state
