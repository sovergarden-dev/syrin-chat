from __future__ import annotations

import unittest
from autochat.ui.win32 import (
    WS_EX_NOACTIVATE,
    WS_EX_TOPMOST,
    WDA_EXCLUDEFROMCAPTURE,
    Win32Bridge,
)
from autochat.ui.geometry import Rect


class MockUser32:
    def __init__(self) -> None:
        self.styles = {}
        self.affinities = {}
        self.foreground = 1001

    def GetWindowLongW(self, hwnd: int, index: int) -> int:
        return self.styles.get((hwnd, index), 0)

    def SetWindowLongW(self, hwnd: int, index: int, new_long: int) -> int:
        old = self.styles.get((hwnd, index), 0)
        self.styles[(hwnd, index)] = new_long
        return old

    def SetWindowDisplayAffinity(self, hwnd: int, affinity: int) -> int:
        self.affinities[hwnd] = affinity
        return 1

    def GetForegroundWindow(self) -> int:
        return self.foreground

    def SetForegroundWindow(self, hwnd: int) -> int:
        self.foreground = hwnd
        return 1

    def GetWindowRect(self, hwnd: int, rect_ptr) -> int:
        target = getattr(rect_ptr, "_obj", rect_ptr)
        target.left = 100
        target.top = 100
        target.right = 900
        target.bottom = 700
        return 1


class Win32BridgeTests(unittest.TestCase):
    def test_apply_no_activate_sets_correct_bits(self) -> None:
        mock_u32 = MockUser32()
        bridge = Win32Bridge(user32=mock_u32)
        success = bridge.apply_no_activate(hwnd=555)
        self.assertTrue(success)
        style = mock_u32.GetWindowLongW(555, -20)
        self.assertTrue(bool(style & WS_EX_NOACTIVATE))

    def test_apply_exclude_from_capture(self) -> None:
        mock_u32 = MockUser32()
        bridge = Win32Bridge(user32=mock_u32)
        success = bridge.apply_exclude_from_capture(hwnd=555)
        self.assertTrue(success)
        self.assertEqual(mock_u32.affinities.get(555), WDA_EXCLUDEFROMCAPTURE)

    def test_get_and_set_foreground(self) -> None:
        mock_u32 = MockUser32()
        bridge = Win32Bridge(user32=mock_u32)
        self.assertEqual(bridge.get_foreground_window(), 1001)
        self.assertTrue(bridge.set_foreground_window(2002))
        self.assertEqual(bridge.get_foreground_window(), 2002)

    def test_get_window_rect(self) -> None:
        mock_u32 = MockUser32()
        bridge = Win32Bridge(user32=mock_u32)
        rect = bridge.get_window_rect(1001)
        self.assertIsNotNone(rect)
        self.assertEqual(rect, Rect(100, 100, 800, 600))


if __name__ == "__main__":
    unittest.main()
