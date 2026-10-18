from __future__ import annotations

import unittest
from autochat.engine.reflex import ReflexRule, ReflexTier
from autochat.engine.two_tier import DeepReasoningTier, TwoTierEngine
from autochat.guard import ConversationRateLimiter
from autochat.loop.live import LiveAgentLoop, LoopCycleResult
from autochat.perception.capture import MockCaptureBackend
from autochat.perception.frame import Frame
from autochat.perception.ocr import MockOcrBackend, OcrLine, OcrResult
from autochat.perception.parser import TranscriptParser
from autochat.perception.settling import FrameSettler
from autochat.perception.detector import DirtyFrameDetector
from autochat.ui.geometry import Rect


class DummyActuator:
    def __init__(self) -> None:
        self.staged = []

    def stage(self, text: str, target_hwnd: int = 1, countdown_seconds: float = 0.0) -> bool:
        self.staged.append(text)
        return True


class DummyProvider:
    def generate(self, prompt: str) -> str:
        return "Cứu bồ ngay đây!"


class LiveLoopRateLimitingTests(unittest.TestCase):
    def setUp(self) -> None:
        raw_frame = Frame(10, 10, 1, bytes([100] * 100))
        self.capture = MockCaptureBackend(default_frame=raw_frame)
        self.roi = Rect(0, 0, 10, 10)
        self.detector = DirtyFrameDetector(change_threshold=0.01)
        self.settler = FrameSettler(detector=self.detector, settling_window_seconds=0.1)
        self.ocr = MockOcrBackend()
        self.parser = TranscriptParser(my_username="MyBot")
        self.engine = TwoTierEngine(
            reflex_tier=ReflexTier([]),
            reasoning_tier=DeepReasoningTier(provider=DummyProvider()),
        )
        self.actuator = DummyActuator()
        self.rate_limiter = ConversationRateLimiter(
            max_per_10min=2,
            max_consecutive=2,
            min_interval=10.0,
        )
        self.loop = LiveAgentLoop(
            capture=self.capture,
            roi=self.roi,
            settler=self.settler,
            ocr=self.ocr,
            parser=self.parser,
            engine=self.engine,
            actuator=self.actuator,
            rate_limiter=self.rate_limiter,
            conversation_id="conv-game-1",
        )

    def test_rate_limiter_blocks_burst_messages(self) -> None:
        # 1. Message 1 at t=10.0 -> stages
        f1 = Frame(10, 10, 1, bytes([0] * 100))
        self.capture.set_frame(f1)
        self.ocr.set_result(OcrResult(lines=[OcrLine(text="PlayerA: Cứu 1")]))
        self.loop.step(timestamp=10.0)
        res1 = self.loop.step(timestamp=10.15)
        self.assertEqual(res1, LoopCycleResult.DISPATCHED_TO_STAGE)
        self.assertEqual(len(self.actuator.staged), 1)

        # 2. Message 2 at t=15.0 (only 5s later < min_interval 10s) -> RATE_LIMITED!
        f2 = Frame(10, 10, 1, bytes([60] * 100))
        self.capture.set_frame(f2)
        self.ocr.set_result(OcrResult(lines=[OcrLine(text="PlayerA: Cứu 2")]))
        self.loop.step(timestamp=15.0)
        res2 = self.loop.step(timestamp=15.15)
        self.assertEqual(res2, LoopCycleResult.RATE_LIMITED)
        self.assertEqual(len(self.actuator.staged), 1)

        # 3. Message 3 at t=25.0 (> 10s later) -> DISPATCHED_TO_STAGE!
        f3 = Frame(10, 10, 1, bytes([130] * 100))
        self.capture.set_frame(f3)
        self.ocr.set_result(OcrResult(lines=[OcrLine(text="PlayerA: Cứu 3")]))
        self.loop.step(timestamp=25.0)
        res3 = self.loop.step(timestamp=25.15)
        self.assertEqual(res3, LoopCycleResult.DISPATCHED_TO_STAGE)
        self.assertEqual(len(self.actuator.staged), 2)

        # 4. Message 4 at t=40.0 (already reached max_per_10min = 2) -> RATE_LIMITED!
        f4 = Frame(10, 10, 1, bytes([200] * 100))
        self.capture.set_frame(f4)
        self.ocr.set_result(OcrResult(lines=[OcrLine(text="PlayerA: Cứu 4")]))
        self.loop.step(timestamp=40.0)
        res4 = self.loop.step(timestamp=40.15)
        self.assertEqual(res4, LoopCycleResult.RATE_LIMITED)
        self.assertEqual(len(self.actuator.staged), 2)


if __name__ == "__main__":
    unittest.main()
