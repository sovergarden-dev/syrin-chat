from __future__ import annotations

import math
from enum import Enum
from threading import RLock
from typing import Protocol, Tuple
from ..guard import check_outbound_draft


class StagedInputStatus(str, Enum):
    IDLE = "idle"
    STAGED = "staged"
    COUNTING_DOWN = "counting_down"
    INJECTING = "injecting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class InputInjector(Protocol):
    def focus(self, hwnd: int) -> bool: ...
    def inject_and_send(self, text: str) -> bool: ...


class StagedInputActuator:
    def __init__(self, injector: InputInjector, max_chars: int = 160) -> None:
        if not hasattr(injector, "focus") or not hasattr(injector, "inject_and_send"):
            raise ValueError("injector must implement focus and inject_and_send")
        self._injector = injector
        self._max_chars = max_chars
        self._status = StagedInputStatus.IDLE
        self._staged_text = ""
        self._target_hwnd = 0
        self._countdown_remaining = 0.0
        self._lock = RLock()

    @property
    def status(self) -> StagedInputStatus:
        with self._lock:
            return self._status

    @property
    def staged_text(self) -> str:
        with self._lock:
            return self._staged_text

    @property
    def countdown_remaining(self) -> float:
        with self._lock:
            return self._countdown_remaining

    @property
    def target_hwnd(self) -> int:
        with self._lock:
            return self._target_hwnd

    def stage(self, text: str, target_hwnd: int, countdown_seconds: float = 0.0) -> None:
        if not isinstance(text, str):
            raise ValueError("text must be string")
        if not isinstance(target_hwnd, int) or target_hwnd <= 0:
            raise ValueError("target_hwnd must be positive integer")
        if (
            not isinstance(countdown_seconds, (int, float))
            or isinstance(countdown_seconds, bool)
            or not math.isfinite(countdown_seconds)
            or countdown_seconds < 0.0
        ):
            raise ValueError("countdown_seconds must be non-negative finite float")

        with self._lock:
            self._staged_text = text
            self._target_hwnd = target_hwnd
            if countdown_seconds > 0.0:
                self._countdown_remaining = float(countdown_seconds)
                self._status = StagedInputStatus.COUNTING_DOWN
            else:
                self._countdown_remaining = 0.0
                self._status = StagedInputStatus.STAGED

    def edit_text(self, new_text: str) -> None:
        if not isinstance(new_text, str):
            raise ValueError("new_text must be string")
        with self._lock:
            if self._status not in (StagedInputStatus.STAGED, StagedInputStatus.COUNTING_DOWN):
                raise RuntimeError(f"cannot edit text in state: {self._status}")
            self._staged_text = new_text

    def cancel(self) -> None:
        with self._lock:
            if self._status in (StagedInputStatus.STAGED, StagedInputStatus.COUNTING_DOWN):
                self._status = StagedInputStatus.CANCELLED
                self._countdown_remaining = 0.0

    def tick(self, delta_seconds: float) -> Tuple[bool, str]:
        if (
            not isinstance(delta_seconds, (int, float))
            or isinstance(delta_seconds, bool)
            or not math.isfinite(delta_seconds)
            or delta_seconds < 0.0
        ):
            raise ValueError("delta_seconds must be non-negative finite float")

        with self._lock:
            if self._status != StagedInputStatus.COUNTING_DOWN:
                return False, f"not_counting_down:{self._status.value}"
            self._countdown_remaining = max(0.0, self._countdown_remaining - delta_seconds)
            if self._countdown_remaining <= 0.0:
                return self._dispatch_internal()
            return False, "waiting_countdown"

    def trigger_dispatch(self) -> Tuple[bool, str]:
        with self._lock:
            return self._dispatch_internal()

    def _dispatch_internal(self) -> Tuple[bool, str]:
        if self._status not in (StagedInputStatus.STAGED, StagedInputStatus.COUNTING_DOWN):
            return False, f"invalid_state_for_dispatch:{self._status.value}"

        violations = check_outbound_draft(self._staged_text, max_chars=self._max_chars)
        if violations:
            self._status = StagedInputStatus.BLOCKED
            return False, f"outbound_guard:{','.join(violations)}"

        self._status = StagedInputStatus.INJECTING
        try:
            focused = self._injector.focus(self._target_hwnd)
            if not focused:
                self._status = StagedInputStatus.BLOCKED
                return False, "focus_failed"
            injected = self._injector.inject_and_send(self._staged_text)
            if not injected:
                self._status = StagedInputStatus.BLOCKED
                return False, "injection_failed"
            self._status = StagedInputStatus.COMPLETED
            return True, "dispatched"
        except Exception as exc:
            self._status = StagedInputStatus.BLOCKED
            return False, f"injection_error:{type(exc).__name__}"
