from __future__ import annotations

import ctypes
from enum import Enum
import random
import time
from typing import Any, Optional


class InputMode(str, Enum):
    CLIPBOARD = "clipboard"
    HUMAN_KEYPRESS = "human_keypress"


class NativeWin32InputApi:
    """Real Windows API caller using ctypes for clipboard and keyboard injection."""

    def __init__(self) -> None:
        try:
            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32
        except (AttributeError, OSError):
            self._user32 = None
            self._kernel32 = None

    @property
    def is_available(self) -> bool:
        return self._user32 is not None and self._kernel32 is not None

    def GetForegroundWindow(self) -> int:
        if not self._user32:
            return 0
        return int(self._user32.GetForegroundWindow())

    def SetForegroundWindow(self, hwnd: int) -> int:
        if not self._user32 or hwnd == 0:
            return 0
        return int(self._user32.SetForegroundWindow(hwnd))

    def OpenClipboard(self, hwnd: int) -> int:
        if not self._user32:
            return 0
        return int(self._user32.OpenClipboard(hwnd))

    def CloseClipboard(self) -> int:
        if not self._user32:
            return 0
        return int(self._user32.CloseClipboard())

    def EmptyClipboard(self) -> int:
        if not self._user32:
            return 0
        return int(self._user32.EmptyClipboard())

    def SetClipboardText(self, text: str) -> bool:
        if not self.is_available:
            return False
        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13
        try:
            encoded = text.encode("utf-16-le") + b"\x00\x00"
            h_mem = self._kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
            if not h_mem:
                return False
            p_mem = self._kernel32.GlobalLock(h_mem)
            if not p_mem:
                self._kernel32.GlobalFree(h_mem)
                return False
            ctypes.memmove(p_mem, encoded, len(encoded))
            self._kernel32.GlobalUnlock(h_mem)

            if not self.OpenClipboard(0):
                self._kernel32.GlobalFree(h_mem)
                return False
            self.EmptyClipboard()
            self._user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            self.CloseClipboard()
            return True
        except Exception:
            return False

    def GetClipboardText(self) -> str:
        if not self.is_available:
            return ""
        CF_UNICODETEXT = 13
        try:
            if not self.OpenClipboard(0):
                return ""
            h_data = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not h_data:
                self.CloseClipboard()
                return ""
            p_data = self._kernel32.GlobalLock(h_data)
            if not p_data:
                self.CloseClipboard()
                return ""
            text = ctypes.wstring_at(p_data)
            self._kernel32.GlobalUnlock(h_data)
            self.CloseClipboard()
            return text
        except Exception:
            return ""

    def SendKeyCombo(self, combo: str) -> bool:
        if not self.is_available:
            return False
        VK_CONTROL = 0x11
        VK_V = 0x56
        VK_RETURN = 0x0D
        KEYEVENTF_KEYUP = 0x0002

        try:
            if combo == "ctrl_v":
                # Key down Ctrl + V
                self._user32.keybd_event(VK_CONTROL, 0, 0, 0)
                self._user32.keybd_event(VK_V, 0, 0, 0)
                time.sleep(0.01)
                # Key up V + Ctrl
                self._user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
                self._user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
                return True
            elif combo == "enter":
                self._user32.keybd_event(VK_RETURN, 0, 0, 0)
                time.sleep(0.01)
                self._user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                return True
            return False
        except Exception:
            return False

    def SendUnicodeChar(self, char: str) -> bool:
        if not self.is_available:
            return False
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002
        try:
            code = ord(char)
            # Guard against surrogate pairs / non-BMP characters for 16-bit wScan
            if code > 0xFFFF:
                return False
            self._user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
            self._user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
            return True
        except Exception:
            return False


class Win32InputDispatcher:
    """Handles focus restoration and safe text injection into target applications."""

    def __init__(
        self,
        api: Any = None,
        restore_clipboard: bool = True,
        restore_delay_seconds: float = 0.05,
    ) -> None:
        if api is not None:
            self._api = api
        else:
            self._api = NativeWin32InputApi()
        self.restore_clipboard = restore_clipboard
        self.restore_delay_seconds = restore_delay_seconds

    def focus(self, hwnd: int) -> bool:
        if hwnd <= 0:
            return False
        current = self._api.GetForegroundWindow()
        if current == hwnd:
            return True
        ok = self._api.SetForegroundWindow(hwnd)
        return bool(ok)

    def inject_and_send(
        self,
        text: str,
        mode: InputMode = InputMode.CLIPBOARD,
        min_delay: float = 0.02,
        max_delay: float = 0.05,
    ) -> bool:
        if not isinstance(text, str) or not text.strip():
            return False

        if mode == InputMode.HUMAN_KEYPRESS:
            d_min = max(0.0, min(min_delay, max_delay))
            d_max = max(0.0, max(min_delay, max_delay))
            for char in text:
                if not self._api.SendUnicodeChar(char):
                    return False
                if d_max > 0:
                    time.sleep(random.uniform(d_min, d_max))
            return bool(self._api.SendKeyCombo("enter"))

        orig_clipboard = ""
        if self.restore_clipboard:
            try:
                orig_clipboard = self._api.GetClipboardText()
            except Exception:
                orig_clipboard = ""

        try:
            # 1. Put text on clipboard
            if not self._api.SetClipboardText(text):
                return False

            # 2. Paste via Ctrl+V
            if not self._api.SendKeyCombo("ctrl_v"):
                return False

            # Short wait for target window to process paste
            if self.restore_delay_seconds > 0:
                time.sleep(self.restore_delay_seconds)

            # 3. Send Enter
            if not self._api.SendKeyCombo("enter"):
                return False

            return True
        finally:
            # 4. Restore original clipboard
            if self.restore_clipboard and orig_clipboard:
                try:
                    self._api.SetClipboardText(orig_clipboard)
                except Exception:
                    pass
