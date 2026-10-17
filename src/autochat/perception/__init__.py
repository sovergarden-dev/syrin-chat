from __future__ import annotations

from .capture import GdiCaptureBackend, MockCaptureBackend, ScreenRegionCapture
from .detector import DirtyFrameDetector
from .frame import Frame

__all__ = [
    "DirtyFrameDetector",
    "Frame",
    "GdiCaptureBackend",
    "MockCaptureBackend",
    "ScreenRegionCapture",
]
