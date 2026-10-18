from __future__ import annotations

from enum import Enum
from typing import Optional
from .detector import DirtyFrameDetector
from .frame import Frame


class SettlerState(str, Enum):
    IDLE = "idle"
    ACCUMULATING = "accumulating"
    SETTLED = "settled"


class FrameSettler:
    """Buffers consecutive frames and waits for a quiet window before emitting a stable frame to OCR."""

    def __init__(
        self,
        detector: DirtyFrameDetector,
        settling_window_seconds: float = 0.2,
        max_wait_seconds: float = 1.0,
    ) -> None:
        if settling_window_seconds <= 0:
            raise ValueError("settling_window_seconds must be positive")
        if max_wait_seconds < settling_window_seconds:
            raise ValueError("max_wait_seconds must be >= settling_window_seconds")

        self.detector = detector
        self.settling_window_seconds = float(settling_window_seconds)
        self.max_wait_seconds = float(max_wait_seconds)

        self._state = SettlerState.IDLE
        self._last_change_time: Optional[float] = None
        self._first_change_time: Optional[float] = None
        self._candidate_frame: Optional[Frame] = None

    @property
    def state(self) -> SettlerState:
        return self._state

    def reset(self) -> None:
        self._state = SettlerState.IDLE
        self._last_change_time = None
        self._first_change_time = None
        self._candidate_frame = None
        self.detector.reset()

    def process_frame(self, frame: Frame, timestamp: float) -> Optional[Frame]:
        if not isinstance(frame, Frame):
            raise ValueError("frame must be a Frame instance")

        is_dirty = self.detector.is_dirty(frame)

        if is_dirty:
            self._candidate_frame = frame
            self._last_change_time = timestamp
            if self._first_change_time is None:
                self._first_change_time = timestamp
            self._state = SettlerState.ACCUMULATING

            # Even if motion is continuous, force settling when max wait budget is exhausted
            elapsed_total = timestamp - self._first_change_time
            if elapsed_total >= self.max_wait_seconds:
                self._state = SettlerState.SETTLED
                result_frame = self._candidate_frame
                self._last_change_time = None
                self._first_change_time = None
                self._candidate_frame = None
                self.detector.reset()
                return result_frame

            return None

        # Frame did not change
        if self._state == SettlerState.ACCUMULATING:
            if self._last_change_time is None or self._candidate_frame is None:
                return None

            elapsed_since_change = timestamp - self._last_change_time
            elapsed_total = timestamp - (self._first_change_time or timestamp)

            # Settled condition: quiet window elapsed OR max wait exceeded
            if (
                elapsed_since_change >= self.settling_window_seconds
                or elapsed_total >= self.max_wait_seconds
            ):
                self._state = SettlerState.SETTLED
                result_frame = self._candidate_frame
                # Reset tracking for next batch
                self._last_change_time = None
                self._first_change_time = None
                self._candidate_frame = None
                self.detector.reset()
                return result_frame

        return None
