from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from .perception.capture import GdiCaptureBackend, MockCaptureBackend
from .perception.detector import DirtyFrameDetector
from .perception.frame import Frame
from .ui.geometry import Rect
from .ui.win32_input import NativeWin32InputApi


class MockSmokeClipboardApi:
    def __init__(self) -> None:
        self.text = "user_original_data"

    @property
    def is_available(self) -> bool:
        return True

    def GetClipboardText(self) -> str:
        return self.text

    def SetClipboardText(self, text: str) -> bool:
        self.text = text
        return True


def check_detector(iterations: int = 50) -> Dict[str, Any]:
    detector = DirtyFrameDetector(change_threshold=0.05)
    f1 = Frame(100, 100, 4, bytes([0] * (100 * 100 * 4)))
    f2 = Frame(100, 100, 4, bytes([255] * (100 * 100 * 4)))

    detector.is_dirty(f1)

    start = time.perf_counter()
    for _ in range(iterations):
        detector.is_dirty(f2)
        detector.is_dirty(f1)
    elapsed = time.perf_counter() - start

    total_diffs = iterations * 2
    avg_us = (elapsed / total_diffs) * 1_000_000

    return {
        "check": "detector",
        "status": "passed",
        "iterations": total_diffs,
        "elapsed_seconds": round(elapsed, 4),
        "microseconds_per_diff": round(avg_us, 2),
    }


def check_capture(mock: bool = False, x: int = 0, y: int = 0, width: int = 100, height: int = 50) -> Dict[str, Any]:
    rect = Rect(x, y, width, height)
    if mock:
        frame_data = bytes([128] * (width * height * 4))
        backend = MockCaptureBackend(default_frame=Frame(width, height, 4, frame_data))
    else:
        backend = GdiCaptureBackend()
        if not backend.is_available:
            return {
                "check": "capture",
                "status": "skipped",
                "reason": "GDI capture is only available on native Windows",
            }

    start = time.perf_counter()
    frame = backend.capture_region(rect)
    elapsed_ms = (time.perf_counter() - start) * 1000

    if frame is None:
        return {
            "check": "capture",
            "status": "failed",
            "reason": "capture_region returned None",
        }

    non_zero = sum(1 for b in frame.data if b != 0)
    non_zero_ratio = non_zero / len(frame.data) if frame.data else 0.0

    return {
        "check": "capture",
        "status": "passed",
        "width": frame.width,
        "height": frame.height,
        "channels": frame.channels,
        "bytes_size": len(frame.data),
        "non_zero_ratio": round(non_zero_ratio, 4),
        "capture_latency_ms": round(elapsed_ms, 2),
    }


def check_clipboard(mock: bool = False) -> Dict[str, Any]:
    api: Any = MockSmokeClipboardApi() if mock else NativeWin32InputApi()

    if not api.is_available:
        return {
            "check": "clipboard",
            "status": "skipped",
            "reason": "Win32 clipboard API is only available on Windows",
        }

    original = api.GetClipboardText()
    test_probe = f"__autochat_probe_{int(time.time())}__"

    try:
        write_ok = api.SetClipboardText(test_probe)
        read_back = api.GetClipboardText()
        matched = (read_back == test_probe)
    finally:
        api.SetClipboardText(original)
        restored_check = api.GetClipboardText()
        restored_ok = (restored_check == original)

    status = "passed" if (write_ok and matched and restored_ok) else "failed"

    return {
        "check": "clipboard",
        "status": status,
        "write_verified": write_ok,
        "read_matched": matched,
        "restored_cleanly": restored_ok,
    }


def check_providers() -> Dict[str, Any]:
    ollama_ok = False
    syrin_ok = False

    # Probe Ollama on 11434
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                ollama_ok = True
    except Exception:
        ollama_ok = False

    # Probe Syrin Pool on 9100
    try:
        req = urllib.request.Request("http://localhost:9100/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                syrin_ok = True
    except Exception:
        syrin_ok = False

    return {
        "check": "providers",
        "status": "passed",
        "ollama_available": ollama_ok,
        "syrin_pool_available": syrin_ok,
    }


def main_smoke(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AutoChat hardware and environment smoke test runner")
    subparsers = parser.add_subparsers(dest="command", help="Diagnostic check to run")

    det_parser = subparsers.add_parser("detector", help="Benchmark DirtyFrameDetector diff speed")
    det_parser.add_argument("--iterations", type=int, default=50)

    cap_parser = subparsers.add_parser("capture", help="Test screen capture")
    cap_parser.add_argument("--mock", action="store_true")
    cap_parser.add_argument("--x", type=int, default=0)
    cap_parser.add_argument("--y", type=int, default=0)
    cap_parser.add_argument("--width", type=int, default=100)
    cap_parser.add_argument("--height", type=int, default=50)

    clip_parser = subparsers.add_parser("clipboard", help="Test non-destructive clipboard preservation")
    clip_parser.add_argument("--mock", action="store_true")

    subparsers.add_parser("providers", help="Probe local Ollama and Syrin Pool endpoints")
    all_parser = subparsers.add_parser("all", help="Run all environment checks")
    all_parser.add_argument("--mock", action="store_true")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    command = args.command or "all"

    if command == "detector":
        res = check_detector(iterations=args.iterations)
        print(json.dumps(res))
    elif command == "capture":
        res = check_capture(mock=args.mock, x=args.x, y=args.y, width=args.width, height=args.height)
        print(json.dumps(res))
    elif command == "clipboard":
        res = check_clipboard(mock=args.mock)
        print(json.dumps(res))
    elif command == "providers":
        res = check_providers()
        print(json.dumps(res))
    elif command == "all":
        is_mock = getattr(args, "mock", False)
        summary = {
            "detector": check_detector(iterations=50),
            "capture": check_capture(mock=is_mock),
            "clipboard": check_clipboard(mock=is_mock),
            "providers": check_providers(),
        }
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main_smoke())
