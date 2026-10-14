from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite
from threading import RLock
from typing import Dict, List, Optional, Tuple
from unicodedata import normalize


class PIIRedactionError(ValueError):
    pass


# Order matters: longest/most specific matchers run first so shorter
# patterns cannot swallow part of a longer identifier.
_RX_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_RX_CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_RX_CCCD = re.compile(r"\b\d{12}\b")
_RX_PHONE = re.compile(r"(?:\+84|0)(?:3|5|7|8|9)\d{8}\b")
_RX_OTP = re.compile(
    r"(?i)(?:otp|mã xác thực|ma xac thuc|verification code|passcode)[^\d]{0,20}(\b\d{4,8}\b)"
)


def _reject_control_chars(text: str) -> None:
    if not isinstance(text, str):
        raise PIIRedactionError("input_not_text")
    for char in text:
        if char == "\x00":
            raise PIIRedactionError("nul_byte")
        if ord(char) < 32 and char not in ("\t", "\n", "\r"):
            raise PIIRedactionError("control_character")


def redact_pii(text: str) -> Tuple[str, Tuple[str, ...]]:
    _reject_control_chars(text)
    categories: List[str] = []

    def apply(code: str, pattern: re.Pattern[str]) -> None:
        nonlocal text
        matches = list(pattern.finditer(text))
        if matches:
            categories.append(code)
            for match in reversed(matches):
                start, end = match.span()
                text = text[:start] + f"[REDACTED:{code.upper()}]" + text[end:]

    apply("email", _RX_EMAIL)
    apply("card", _RX_CARD)
    apply("cccd", _RX_CCCD)
    apply("phone", _RX_PHONE)

    otp_matches = list(_RX_OTP.finditer(text))
    if otp_matches:
        categories.append("otp")
        for match in reversed(otp_matches):
            tx_start, tx_end = match.span(1)
            text = text[:tx_start] + "[REDACTED:OTP]" + text[tx_end:]

    return text, tuple(sorted(set(categories)))


_INBOUND_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "money_request": (
        "chuyển khoản", "tiền", "vay", "mượn", "stk", "ngân hàng",
        "triệu", "nghìn", "bank",
    ),
    "otp_or_secret": (
        "otp", "mật khẩu", "password", "mã xác nhận", "ma xac nhan",
        "cccd", "cmnd", "cvv", "private key", "seed phrase",
    ),
    "prompt_injection": (
        "bỏ qua mọi chỉ dẫn", "ignore previous instructions",
        "system prompt", "gửi toàn bộ dữ liệu",
    ),
    "bot_identity_probe": (
        "có phải là bot", "có phải ai không", "are you a bot",
        "are you an ai", "phải người thật không",
    ),
}


def check_inbound_hard_rules(text: str) -> Tuple[str, ...]:
    normalized = normalize("NFC", text).lower()
    violations = []
    for category, keywords in _INBOUND_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in normalized:
                violations.append(category)
                break
    return tuple(violations)


def check_outbound_draft(
    text: str,
    *,
    max_chars: int = 160,
    require_disclosure: bool = False,
    disclosure_text: str = " · (trợ lý AI)",
) -> Tuple[str, ...]:
    violations: List[str] = []
    try:
        _reject_control_chars(text)
    except PIIRedactionError:
        violations.append("draft_nonprintable")
        return tuple(violations)
    if not text.strip():
        violations.append("draft_empty")
    if len(text) > max_chars:
        violations.append("draft_too_long")
    _, categories = redact_pii(text)
    if categories:
        violations.append("pii_leaked")
    if require_disclosure and not text.endswith(disclosure_text):
        violations.append("disclosure_missing")
    return tuple(violations)


@dataclass
class _ConversationState:
    window: List[float]
    last_send_time: Optional[float]
    consecutive_count: int


class ConversationRateLimiter:
    def __init__(
        self,
        max_per_10min: int = 3,
        max_consecutive: int = 2,
        min_interval: float = 15.0,
        now: float = 0.0,
    ) -> None:
        self._validate_parameter(max_per_10min, "max_per_10min", positive=True)
        self._validate_parameter(max_consecutive, "max_consecutive", positive=True)
        self._validate_parameter(min_interval, "min_interval", positive=False)
        self._validate_parameter(now, "now", positive=False)
        self.max_per_10min = max_per_10min
        self.max_consecutive = max_consecutive
        self.min_interval = min_interval
        self._states: Dict[str, _ConversationState] = {}
        self._lock = RLock()

    @staticmethod
    def _validate_parameter(value: object, name: str, *, positive: bool) -> None:
        if type(value) is bool:
            raise ValueError(f"{name}: integer_required")
        if positive:
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name}: positive_integer_required")
        else:
            if not isinstance(value, (int, float)) or type(value) is bool:
                raise ValueError(f"{name}: number_required")
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name}: nonnegative_finite_number_required")

    @staticmethod
    def _validate_call(conversation_id: object, now: object) -> None:
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            raise ValueError("conversation_id: nonempty_string_required")
        if type(now) is bool:
            raise ValueError("now: number_required")
        if not isinstance(now, (int, float)):
            raise ValueError("now: number_required")
        if not isfinite(now) or now < 0:
            raise ValueError("now: nonnegative_finite_number_required")

    def _state(self, conversation_id: str) -> _ConversationState:
        if conversation_id not in self._states:
            self._states[conversation_id] = _ConversationState([], None, 0)
        return self._states[conversation_id]

    def try_acquire(self, conversation_id: str, now: float) -> Tuple[bool, str]:
        self._validate_call(conversation_id, now)
        with self._lock:
            state = self._state(conversation_id)
            cutoff = now - 600.0
            state.window = [ts for ts in state.window if ts > cutoff]
            if state.last_send_time is not None and now - state.last_send_time < self.min_interval:
                return False, "min_interval"
            if state.consecutive_count >= self.max_consecutive:
                return False, "max_consecutive"
            if len(state.window) >= self.max_per_10min:
                return False, "max_per_10min"
            state.window.append(now)
            state.consecutive_count += 1
            state.last_send_time = now
            return True, "allowed"

    def mark_other_message(self, conversation_id: str, now: float) -> None:
        self._validate_call(conversation_id, now)
        with self._lock:
            self._state(conversation_id).consecutive_count = 0
