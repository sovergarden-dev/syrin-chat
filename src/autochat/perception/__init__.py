from __future__ import annotations

from .capture import GdiCaptureBackend, MockCaptureBackend, ScreenRegionCapture
from .detector import DirtyFrameDetector
from .frame import Frame
from .ocr import (
    MockOcrBackend,
    OcrBackend,
    OcrLine,
    OcrResult,
    OcrWord,
    WinRtOcrBackend,
)
from .parser import ParsedMessage, TranscriptParser
from .settling import FrameSettler, SettlerState

__all__ = [
    "DirtyFrameDetector",
    "Frame",
    "FrameSettler",
    "GdiCaptureBackend",
    "MockCaptureBackend",
    "MockOcrBackend",
    "OcrBackend",
    "OcrLine",
    "OcrResult",
    "OcrWord",
    "ParsedMessage",
    "ScreenRegionCapture",
    "SettlerState",
    "TranscriptParser",
    "WinRtOcrBackend",
]
