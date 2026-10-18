from __future__ import annotations

import argparse
import json
import sys
import time
from typing import List, Optional
from .engine.providers import OllamaProvider, SyrinPoolProvider
from .engine.reflex import ReflexRule, ReflexTier
from .engine.two_tier import DeepReasoningTier, TwoTierEngine
from .guard import ConversationRateLimiter
from .loop.live import LiveAgentLoop, LoopCycleResult
from .perception.capture import GdiCaptureBackend, MockCaptureBackend, ScreenRegionCapture
from .perception.detector import DirtyFrameDetector
from .perception.frame import Frame
from .perception.ocr import MockOcrBackend, OcrLine, OcrResult
from .perception.parser import TranscriptParser
from .perception.settling import FrameSettler
from .ui.actuator import InputInjector, StagedInputActuator
from .ui.geometry import Rect
from .ui.win32_input import InputMode, Win32InputDispatcher


class MockInjector:
    def __init__(self) -> None:
        self.injected_texts: List[str] = []

    def focus(self, hwnd: int) -> bool:
        return True

    def inject_and_send(self, text: str) -> bool:
        self.injected_texts.append(text)
        return True


class SimpleStaticProvider:
    def __init__(self, response: str = "Đang hỗ trợ đồng đội đây!") -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


def main_live(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AutoChat live agent runner")
    parser.add_argument("--mock", action="store_true", help="Run with mock capture and OCR")
    parser.add_argument("--real", action="store_true", help="Run with real GDI screen capture")
    parser.add_argument("--roi", type=str, default="0,0,100,50", help="ROI format x,y,w,h")
    parser.add_argument("--provider", type=str, default="mock", choices=["mock", "ollama", "syrin"])
    parser.add_argument("--ollama-endpoint", type=str, default="http://localhost:11434")
    parser.add_argument("--syrin-endpoint", type=str, default="http://localhost:9100")
    parser.add_argument("--username", type=str, default="MyBot")
    parser.add_argument("--once", action="store_true", help="Run exactly one step and exit")
    parser.add_argument("--max-steps", type=int, default=1, help="Maximum number of loop cycles to execute")
    parser.add_argument("--interval", type=float, default=0.05, help="Sleep interval in seconds between cycles")
    parser.add_argument("--warmup", action="store_true", default=False, help="Enable initial stale history absorption")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    steps_to_run = 1 if args.once else args.max_steps

    # Parse ROI
    try:
        parts = [int(p.strip()) for p in args.roi.split(",")]
        if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
            roi = Rect(parts[0], parts[1], parts[2], parts[3])
        else:
            roi = Rect(0, 0, 100, 50)
    except Exception:
        roi = Rect(0, 0, 100, 50)

    # Setup capture backend
    if args.real:
        gdi = GdiCaptureBackend()
        capture: ScreenRegionCapture = gdi if gdi.is_available else MockCaptureBackend(
            default_frame=Frame(roi.width, roi.height, 4, bytes([128] * (roi.width * roi.height * 4)))
        )
    else:
        raw_frame = Frame(roi.width, roi.height, 4, bytes([128] * (roi.width * roi.height * 4)))
        capture = MockCaptureBackend(default_frame=raw_frame)

    detector = DirtyFrameDetector(change_threshold=0.05)
    settler = FrameSettler(detector=detector, settling_window_seconds=0.05)
    ocr = MockOcrBackend()
    ocr.set_result(OcrResult(lines=[OcrLine(text="Teammate: Xin chào")]))
    transcript_parser = TranscriptParser(my_username=args.username)

    # Provider selection
    if args.provider == "ollama":
        provider_impl = OllamaProvider(endpoint=args.ollama_endpoint)
    elif args.provider == "syrin":
        provider_impl = SyrinPoolProvider(endpoint=args.syrin_endpoint)
    else:
        provider_impl = SimpleStaticProvider()

    rule = ReflexRule(pattern=r"(?i)\bchào\b", canned_response="Chào đồng đội!")
    reflex = ReflexTier([rule])
    reasoning = DeepReasoningTier(provider=provider_impl)
    engine = TwoTierEngine(reflex_tier=reflex, reasoning_tier=reasoning)

    # Injector selection
    if args.real:
        dispatcher = Win32InputDispatcher()
        injector: InputInjector = (
            dispatcher if getattr(dispatcher._api, "is_available", False) else MockInjector()
        )
    else:
        injector = MockInjector()

    actuator = StagedInputActuator(injector=injector)
    rate_limiter = ConversationRateLimiter(max_per_10min=5, min_interval=5.0)

    loop = LiveAgentLoop(
        capture=capture,
        roi=roi,
        settler=settler,
        ocr=ocr,
        parser=transcript_parser,
        engine=engine,
        actuator=actuator,
        warmup=args.warmup,
        rate_limiter=rate_limiter,
    )

    executed_steps = 0
    cycle_results = []
    base_time = time.time()

    for i in range(steps_to_run):
        t = base_time + (i * 0.1)
        res = loop.step(timestamp=t)
        cycle_results.append(str(res.value))
        executed_steps += 1
        if i < steps_to_run - 1 and args.interval > 0:
            time.sleep(args.interval)

    # Emit metadata-only structured JSON summary
    summary = {
        "status": "completed",
        "steps_executed": executed_steps,
        "cycle_results": cycle_results,
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main_live())
