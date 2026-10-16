from __future__ import annotations

from .actuator import InputInjector, StagedInputActuator, StagedInputStatus
from .geometry import DpiScale, NormalizedRect, Rect, WindowAnchor
from .overlay import (
    FloatingAssistantOverlay,
    OverlayConfig,
    OverlayState,
    is_qt_available,
    setup_overlay_window,
)
from .win32 import (
    WDA_EXCLUDEFROMCAPTURE,
    WDA_MONITOR,
    WDA_NONE,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOPMOST,
    WS_EX_TRANSPARENT,
    Win32Bridge,
)

__all__ = [
    "DpiScale",
    "FloatingAssistantOverlay",
    "InputInjector",
    "NormalizedRect",
    "OverlayConfig",
    "OverlayState",
    "Rect",
    "StagedInputActuator",
    "StagedInputStatus",
    "WDA_EXCLUDEFROMCAPTURE",
    "WDA_MONITOR",
    "WDA_NONE",
    "WS_EX_LAYERED",
    "WS_EX_NOACTIVATE",
    "WS_EX_TOPMOST",
    "WS_EX_TRANSPARENT",
    "Win32Bridge",
    "WindowAnchor",
    "is_qt_available",
    "setup_overlay_window",
]

