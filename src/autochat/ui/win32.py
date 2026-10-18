from __future__ import annotations

import ctypes
from ctypes import Structure, c_int, c_long, c_ssize_t, c_uint, c_void_p, byref
from typing import Any, Optional
from .geometry import Rect

# Win32 Extended Window Styles
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000

# Window Display Affinity
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

# Window Long Indices
GWL_EXSTYLE = -20


class RECT(Structure):
    _fields_ = [
        ("left", c_long),
        ("top", c_long),
        ("right", c_long),
        ("bottom", c_long),
    ]


class Win32Bridge:
    def __init__(self, user32: Any = None) -> None:
        if user32 is not None:
            self._user32 = user32
        else:
            try:
                self._user32 = ctypes.windll.user32
                self._setup_signatures()
            except (AttributeError, OSError):
                self._user32 = None

    def _setup_signatures(self) -> None:
        if not self._user32:
            return
        if hasattr(self._user32, "GetWindowLongPtrW"):
            self._user32.GetWindowLongPtrW.argtypes = [c_void_p, c_int]
            self._user32.GetWindowLongPtrW.restype = c_ssize_t
        if hasattr(self._user32, "SetWindowLongPtrW"):
            self._user32.SetWindowLongPtrW.argtypes = [c_void_p, c_int, c_ssize_t]
            self._user32.SetWindowLongPtrW.restype = c_ssize_t
        self._user32.GetWindowRect.argtypes = [c_void_p, c_void_p]
        self._user32.GetWindowRect.restype = c_int
        self._user32.GetForegroundWindow.restype = c_void_p
        self._user32.SetForegroundWindow.argtypes = [c_void_p]
        self._user32.SetForegroundWindow.restype = c_int
        if hasattr(self._user32, "SetWindowDisplayAffinity"):
            self._user32.SetWindowDisplayAffinity.argtypes = [c_void_p, c_uint]
            self._user32.SetWindowDisplayAffinity.restype = c_int

    @property
    def is_available(self) -> bool:
        return self._user32 is not None

    def apply_no_activate(self, hwnd: int) -> bool:
        if not self._user32:
            return False
        try:
            get_fn = getattr(self._user32, "GetWindowLongPtrW", getattr(self._user32, "GetWindowLongW", None))
            set_fn = getattr(self._user32, "SetWindowLongPtrW", getattr(self._user32, "SetWindowLongW", None))
            if not get_fn or not set_fn:
                return False
            current_style = get_fn(hwnd, GWL_EXSTYLE)
            new_style = current_style | WS_EX_NOACTIVATE
            set_fn(hwnd, GWL_EXSTYLE, new_style)
            return True
        except Exception:
            return False

    def apply_exclude_from_capture(self, hwnd: int) -> bool:
        if not self._user32:
            return False
        try:
            res = self._user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            return bool(res)
        except Exception:
            return False

    def get_foreground_window(self) -> int:
        if not self._user32:
            return 0
        try:
            return int(self._user32.GetForegroundWindow())
        except Exception:
            return 0

    def set_foreground_window(self, hwnd: int) -> bool:
        if not self._user32 or hwnd == 0:
            return False
        try:
            res = self._user32.SetForegroundWindow(hwnd)
            return bool(res)
        except Exception:
            return False

    def get_window_rect(self, hwnd: int) -> Optional[Rect]:
        if not self._user32 or hwnd == 0:
            return None
        rect = RECT()
        try:
            ok = self._user32.GetWindowRect(hwnd, byref(rect))
            if not ok:
                return None
            width = max(1, rect.right - rect.left)
            height = max(1, rect.bottom - rect.top)
            return Rect(x=rect.left, y=rect.top, width=width, height=height)
        except Exception:
            return None
