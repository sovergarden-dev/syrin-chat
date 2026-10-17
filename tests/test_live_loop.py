from __future__ import annotations

import unittest
from typing import List, Optional
from autochat.engine.reflex import ReflexRule, ReflexTier
from autochat.engine.two_tier import (
    DeepReasoningTier,
    TwoTierEngine,
)
from autochat.guard import check_outbound_draft
from autochat.loop.live import LiveAgentLoop, LoopCycleResult
from autochat.perception.capture import MockCaptureBackend
from autochat.perception.frame import Frame
from autochat.perception.ocr import MockOcrBackend, OcrLine, OcrResult
from autochat.perception.parser import TranscriptParser
from autochat.perception.settling import FrameSettler
from autochat.perception.detector import DirtyFrameDetector
from autochat.ui.actuator import StagedInputActuator
from autochat.ui.geometry import Rect


class DummyActuator(StagedInputActuator):
    def __init__(self) -> None:
        self.staged_texts: List[str] = []

    def stage(self, text: str, target_hwnd: int = 1, countdown_seconds: float = 0.0) -> bool:
        if check_outbound_draft(text):
            return False
        self.staged_texts.append(text)
        return True


class DummyProvider:
    def __init__(self, response: str = "Đang combat rồng, 15s nữa tới!") -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


class LiveAgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        # 1. Capture backend
        self.raw_frame = Frame(width=100, height=50, channels=4, data=bytes([100] * 20000))
        self.capture = MockCaptureBackend(default_frame=self.raw_frame)
        self.roi = Rect(x=0, y=0, width=100, height=50)

        # 2. Perception: Detector, Settler, OCR, Parser
        self.detector = DirtyFrameDetector(change_threshold=0.05)
        self.settler = FrameSettler(
            detector=self.detector,
            settling_window_seconds=0.1,
            max_wait_seconds=0.5,
        )
        self.ocr = MockOcrBackend()
        self.parser = TranscriptParser(my_username="MyBotPlayer")

        # 3. Engine
        rule = ReflexRule(pattern=r"(?i)\bhi\b", canned_response="Hello bồ tèo!")
        reflex = ReflexTier(rules=[rule])
        reasoning = DeepReasoningTier(provider=DummyProvider())
        self.engine = TwoTierEngine(reflex_tier=reflex, reasoning_tier=reasoning)

        # 4. Actuator
        self.actuator = DummyActuator()

        # 5. Live Loop
        self.loop = LiveAgentLoop(
            capture=self.capture,
            roi=self.roi,
            settler=self.settler,
            ocr=self.ocr,
            parser=self.parser,
            engine=self.engine,
            actuator=self.actuator,
        )

    def test_cycle_settles_and_triggers_reflex_into_actuator(self) -> None:
        # Setup OCR result for teammate message
        line = OcrLine(text="Teammate1: hi")
        self.ocr.set_result(OcrResult(lines=[line], full_text="Teammate1: hi"))

        # Frame 1 at t=10.0: dirty detected, starts accumulating
        r1 = self.loop.step(timestamp=10.0)
        self.assertEqual(r1, LoopCycleResult.ACCUMULATING)
        self.assertEqual(len(self.actuator.staged_texts), 0)

        # Frame 2 at t=10.15: quiet window passed (> 0.1s) -> settles, OCR runs, reflex triggers, stages!
        r2 = self.loop.step(timestamp=10.15)
        self.assertEqual(r2, LoopCycleResult.DISPATCHED_TO_STAGE)
        self.assertEqual(len(self.actuator.staged_texts), 1)
        self.assertEqual(self.actuator.staged_texts[0], "Hello bồ tèo!")

    def test_cycle_drops_self_messages_safely(self) -> None:
        # Message sent by self should not stage any reply
        line = OcrLine(text="MyBotPlayer: hi")
        self.ocr.set_result(OcrResult(lines=[line], full_text="MyBotPlayer: hi"))

        self.loop.step(timestamp=10.0)
        r2 = self.loop.step(timestamp=10.15)
        self.assertEqual(r2, LoopCycleResult.NO_ACTION)
        self.assertEqual(len(self.actuator.staged_texts), 0)

    def test_cycle_blocks_unsafe_draft_from_staging(self) -> None:
        # Reasoning provider produces unsafe draft (PII or blocked rule)
        unsafe_provider = DummyProvider(response="Số CCCD của tôi là 012345678901")
        unsafe_engine = TwoTierEngine(
            reflex_tier=ReflexTier([]),
            reasoning_tier=DeepReasoningTier(provider=unsafe_provider),
        )
        loop = LiveAgentLoop(
            capture=self.capture,
            roi=self.roi,
            settler=self.settler,
            ocr=self.ocr,
            parser=self.parser,
            engine=unsafe_engine,
            actuator=self.actuator,
        )
        line = OcrLine(text="Teammate1: Hỏi thông tin cá nhân đi")
        self.ocr.set_result(OcrResult(lines=[line], full_text=line.text))

        loop.step(timestamp=10.0)
        r2 = loop.step(timestamp=10.15)
        self.assertEqual(r2, LoopCycleResult.BLOCKED_BY_GUARD)
        self.assertEqual(len(self.actuator.staged_texts), 0)

    def test_warmup_absorbs_initial_lines_without_staging(self) -> None:
        loop = LiveAgentLoop(
            capture=self.capture,
            roi=self.roi,
            settler=self.settler,
            ocr=self.ocr,
            parser=self.parser,
            engine=self.engine,
            actuator=self.actuator,
            warmup=True,
        )
        line = OcrLine(text="Teammate1: hi")
        self.ocr.set_result(OcrResult(lines=[line], full_text="Teammate1: hi"))

        # Step 1: Accumulating
        loop.step(timestamp=10.0)
        # Step 2: Settles, but warmup absorbs it as baseline
        r2 = loop.step(timestamp=10.15)
        self.assertEqual(r2, LoopCycleResult.NO_ACTION)
        self.assertEqual(len(self.actuator.staged_texts), 0)


if __name__ == "__main__":
    unittest.main()
