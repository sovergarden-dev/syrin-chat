from __future__ import annotations

from enum import Enum
from typing import List, Optional
from ..engine.two_tier import TwoTierEngine
from ..guard import ConversationRateLimiter, check_outbound_draft
from ..perception.capture import ScreenRegionCapture
from ..perception.ocr import OcrBackend
from ..perception.parser import ParsedMessage, TranscriptParser
from ..perception.settling import FrameSettler
from ..ui.actuator import StagedInputActuator
from ..ui.geometry import Rect


class LoopCycleResult(str, Enum):
    NO_FRAME = "no_frame"
    ACCUMULATING = "accumulating"
    NO_ACTION = "no_action"
    RATE_LIMITED = "rate_limited"
    BLOCKED_BY_GUARD = "blocked_by_guard"
    DISPATCHED_TO_STAGE = "dispatched_to_stage"


class LiveAgentLoop:
    """Coordinates perception, reasoning, and staging in real-time execution cycles."""

    def __init__(
        self,
        capture: ScreenRegionCapture,
        roi: Rect,
        settler: FrameSettler,
        ocr: OcrBackend,
        parser: TranscriptParser,
        engine: TwoTierEngine,
        actuator: StagedInputActuator,
        target_hwnd: int = 1,
        countdown_seconds: float = 3.0,
        warmup: bool = False,
        rate_limiter: Optional[ConversationRateLimiter] = None,
        conversation_id: str = "default",
    ) -> None:
        self.capture = capture
        self.roi = roi
        self.settler = settler
        self.ocr = ocr
        self.parser = parser
        self.engine = engine
        self.actuator = actuator
        self.target_hwnd = target_hwnd
        self.countdown_seconds = countdown_seconds
        self.warmup = warmup
        self.rate_limiter = rate_limiter
        self.conversation_id = conversation_id
        self._warmed_up = not warmup
        self._history: List[ParsedMessage] = []
        self._has_dispatched_since_other = False

    def _append_history(self, msg: ParsedMessage) -> None:
        self._history.append(msg)
        if len(self._history) > 100:
            self._history.pop(0)

    def step(self, timestamp: float) -> LoopCycleResult:
        # 1. Capture screen ROI
        frame = self.capture.capture_region(self.roi)
        if frame is None:
            return LoopCycleResult.NO_FRAME

        # 2. Frame settling filter
        settled_frame = self.settler.process_frame(frame, timestamp=timestamp)
        if settled_frame is None:
            return LoopCycleResult.ACCUMULATING

        # 3. OCR recognition on settled frame
        ocr_result = self.ocr.recognize(settled_frame)
        if not ocr_result.lines:
            return LoopCycleResult.NO_ACTION

        # 4. Parse messages
        messages = self.parser.parse(ocr_result)
        if not messages:
            return LoopCycleResult.NO_ACTION

        # 5. Baseline Warmup Absorption (skip responding to existing stale chat)
        if not self._warmed_up:
            for msg in messages:
                self._append_history(msg)
            self._warmed_up = True
            return LoopCycleResult.NO_ACTION

        # 6. Process new incoming messages
        action_taken = False
        for msg in messages:
            if msg.is_self:
                self._append_history(msg)
                continue

            if self.rate_limiter and self._has_dispatched_since_other:
                self.rate_limiter.mark_other_message(self.conversation_id, now=timestamp)
                self._has_dispatched_since_other = False

            # Process through Two-Tier Engine
            draft, _ = self.engine.process_message(msg, history=self._history)
            self._append_history(msg)

            if not draft:
                continue

            # 6. Outbound Safety Guard
            violations = check_outbound_draft(draft)
            if violations:
                return LoopCycleResult.BLOCKED_BY_GUARD

            # 7. Rate limit gate check
            if self.rate_limiter:
                allowed, _ = self.rate_limiter.try_acquire(self.conversation_id, now=timestamp)
                if not allowed:
                    return LoopCycleResult.RATE_LIMITED

            # 8. Stage into actuator for user preview & autopilot countdown
            if self.actuator.stage(
                draft,
                target_hwnd=self.target_hwnd,
                countdown_seconds=self.countdown_seconds,
            ):
                self._has_dispatched_since_other = True
                action_taken = True
                break

        if action_taken:
            return LoopCycleResult.DISPATCHED_TO_STAGE

        return LoopCycleResult.NO_ACTION
