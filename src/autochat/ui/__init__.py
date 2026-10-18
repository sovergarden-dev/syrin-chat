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

from .hotkey import (
    GlobalHotkeyBridge,
    HotkeyAction,
    NativeUser32HotkeyApi,
    WM_HOTKEY,
    make_qt_hotkey_filter,
)
from .win32_input import InputMode, NativeWin32InputApi, Win32InputDispatcher

__all__ = [
    "DpiScale",
    "FloatingAssistantOverlay",
    "GlobalHotkeyBridge",
    "HotkeyAction",
    "InputInjector",
    "InputMode",
    "NativeUser32HotkeyApi",
    "NativeWin32InputApi",
    "NormalizedRect",
    "OverlayConfig",
    "OverlayState",
    "Rect",
    "StagedInputActuator",
    "StagedInputStatus",
    "WDA_EXCLUDEFROMCAPTURE",
    "WDA_MONITOR",
    "WDA_NONE",
    "WM_HOTKEY",
    "WS_EX_LAYERED",
    "WS_EX_NOACTIVATE",
    "WS_EX_TOPMOST",
    "WS_EX_TRANSPARENT",
    "Win32Bridge",
    "Win32InputDispatcher",
    "WindowAnchor",
    "is_qt_available",
    "make_qt_hotkey_filter",
    "setup_overlay_window",
]

