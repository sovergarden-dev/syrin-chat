from __future__ import annotations

import ctypes
from enum import Enum
from typing import Any, Callable, Dict, Optional


class HotkeyAction(str, Enum):
    SEND_IMMEDIATE = "send_immediate"
    CANCEL_DRAFT = "cancel_draft"
    PANIC_STOP = "panic_stop"


class NativeUser32HotkeyApi:
    def __init__(self) -> None:
        try:
            self._user32 = ctypes.windll.user32
            self._setup_signatures()
        except (AttributeError, OSError):
            self._user32 = None

    def _setup_signatures(self) -> None:
        if not self._user32:
            return
        from ctypes import c_int, c_uint, c_void_p
        self._user32.RegisterHotKey.argtypes = [c_void_p, c_int, c_uint, c_uint]
        self._user32.RegisterHotKey.restype = c_int
        self._user32.UnregisterHotKey.argtypes = [c_void_p, c_int]
        self._user32.UnregisterHotKey.restype = c_int

    @property
    def is_available(self) -> bool:
        return self._user32 is not None

    def RegisterHotKey(self, hwnd: int, hotkey_id: int, fsModifiers: int, vk: int) -> int:
        if not self._user32:
            return 0
        return int(self._user32.RegisterHotKey(hwnd, hotkey_id, fsModifiers, vk))

    def UnregisterHotKey(self, hwnd: int, hotkey_id: int) -> int:
        if not self._user32:
            return 0
        return int(self._user32.UnregisterHotKey(hwnd, hotkey_id))


class GlobalHotkeyBridge:
    """Manages system-wide Win32 hotkeys for single-touch sending, cancel, and emergency panic stop."""

    def __init__(self, api: Any = None, hwnd: int = 0) -> None:
        if api is not None:
            self._api = api
        else:
            self._api = NativeUser32HotkeyApi()
        self.hwnd = hwnd
        self._next_id = 1
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._registered_ids: Dict[HotkeyAction, int] = {}

    def register_action(
        self,
        action: HotkeyAction,
        vk: int,
        modifiers: int = 0,
        callback: Optional[Callable[[], None]] = None,
    ) -> int:
        hotkey_id = self._next_id
        self._next_id += 1

        ok = self._api.RegisterHotKey(self.hwnd, hotkey_id, modifiers, vk)
        if not ok:
            return 0

        self._registered_ids[action] = hotkey_id
        if callback:
            self._callbacks[hotkey_id] = callback
        return hotkey_id

    def handle_hotkey_id(self, hotkey_id: int) -> bool:
        cb = self._callbacks.get(hotkey_id)
        if cb:
            cb()
            return True
        return False

    def unregister_all(self) -> None:
        for hotkey_id in list(self._callbacks.keys()):
            self._api.UnregisterHotKey(self.hwnd, hotkey_id)
        self._callbacks.clear()
        self._registered_ids.clear()

    @property
    def is_available(self) -> bool:
        return self._api.is_available


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


def make_qt_hotkey_filter(bridge: GlobalHotkeyBridge) -> Any:
    """Creates a QAbstractNativeEventFilter for PySide6 integration when available."""
    try:
        from PySide6.QtCore import QAbstractNativeEventFilter  # type: ignore
    except ImportError:
        return None

    class _QtNativeFilter(QAbstractNativeEventFilter):
        def __init__(self, b: GlobalHotkeyBridge) -> None:
            super().__init__()
            self._bridge = b

        def nativeEventFilter(self, event_type: Any, message: Any) -> Any:
            if event_type in (b"windows_generic_MSG", "windows_generic_MSG"):
                try:
                    import ctypes
                    from ctypes import wintypes
                    msg = wintypes.MSG.from_address(int(message))
                    if msg.message == WM_HOTKEY:
                        if self._bridge.handle_hotkey_id(int(msg.wParam)):
                            return True, 0
                except Exception:
                    pass
            return False, 0

    return _QtNativeFilter(bridge)

