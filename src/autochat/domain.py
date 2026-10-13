from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from math import isfinite
from typing import FrozenSet
from unicodedata import normalize


class AutonomyLevel(IntEnum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class SpeakerState(str, Enum):
    SELF = "self"
    OTHER = "other"
    UNKNOWN = "unknown"


def _require_exact_bool(value: object, field: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{field}: boolean_required")


def _require_nonempty(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty_string_required")


@dataclass(frozen=True)
class RuntimePolicy:
    profile_enabled: bool
    read_consent: bool
    source_access_allowed: bool
    requested_level: AutonomyLevel
    policy_revision: str

    def __post_init__(self) -> None:
        for field in ("profile_enabled", "read_consent", "source_access_allowed"):
            _require_exact_bool(getattr(self, field), field)
        if not isinstance(self.requested_level, AutonomyLevel):
            raise ValueError("requested_level: autonomy_level_required")
        _require_nonempty(self.policy_revision, "policy_revision")

    @property
    def effective_level(self) -> AutonomyLevel:
        if not (self.profile_enabled and self.read_consent and self.source_access_allowed):
            return AutonomyLevel.L0
        return min(self.requested_level, AutonomyLevel.L2)


@dataclass(frozen=True)
class MessageEvent:
    event_id: str
    profile_id: str
    conversation_id: str
    source_epoch: str
    occurrence_id: str
    speaker_state: SpeakerState
    text_nfc: str
    observed_monotonic: float
    source_complete: bool

    def __post_init__(self) -> None:
        for field in (
            "event_id",
            "profile_id",
            "conversation_id",
            "source_epoch",
            "occurrence_id",
        ):
            _require_nonempty(getattr(self, field), field)
        if not isinstance(self.speaker_state, SpeakerState):
            raise ValueError("speaker_state: speaker_state_required")
        _require_nonempty(self.text_nfc, "text_nfc")
        if normalize("NFC", self.text_nfc) != self.text_nfc:
            raise ValueError("text_nfc: nfc_normalization_required")
        if not isinstance(self.observed_monotonic, (int, float)) or isinstance(
            self.observed_monotonic, bool
        ) or not isfinite(self.observed_monotonic) or self.observed_monotonic < 0:
            raise ValueError("observed_monotonic: nonnegative_finite_number_required")
        _require_exact_bool(self.source_complete, "source_complete")


@dataclass(frozen=True)
class Decision:
    addressed_to_user: bool
    needs_reply: bool
    turn_complete: bool
    risk_flags: FrozenSet[str]
    rationale_code: str

    def __post_init__(self) -> None:
        for field in ("addressed_to_user", "needs_reply", "turn_complete"):
            _require_exact_bool(getattr(self, field), field)
        if not isinstance(self.risk_flags, frozenset) or any(
            not isinstance(flag, str) or not flag.strip() for flag in self.risk_flags
        ):
            raise ValueError("risk_flags: immutable_nonempty_strings_required")
        _require_nonempty(self.rationale_code, "rationale_code")


@dataclass(frozen=True)
class DraftCandidate:
    reply_text: str
    route_id: str
    model_registry_revision: str
    finish_status: str

    def __post_init__(self) -> None:
        for field in ("reply_text", "route_id", "model_registry_revision", "finish_status"):
            _require_nonempty(getattr(self, field), field)
