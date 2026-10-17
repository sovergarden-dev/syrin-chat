from __future__ import annotations

import unittest
from autochat.ui.win32_input import InputMode, Win32InputDispatcher


class MockWin32Api:
    def __init__(self) -> None:
        self.foreground_hwnd = 100
        self.clipboard_data = "original clipboard text"
        self.sent_inputs = []
        self.sent_chars = []

    def GetForegroundWindow(self) -> int:
        return self.foreground_hwnd

    def SetForegroundWindow(self, hwnd: int) -> int:
        self.foreground_hwnd = hwnd
        return 1

    def OpenClipboard(self, hwnd: int) -> int:
        return 1

    def CloseClipboard(self) -> int:
        return 1

    def EmptyClipboard(self) -> int:
        return 1

    def SetClipboardText(self, text: str) -> bool:
        self.clipboard_data = text
        return True

    def GetClipboardText(self) -> str:
        return self.clipboard_data

    def SendKeyCombo(self, combo: str) -> bool:
        self.sent_inputs.append(combo)
        return True

    def SendUnicodeChar(self, char: str) -> bool:
        self.sent_chars.append(char)
        return True


class Win32InputDispatcherTests(unittest.TestCase):
    def test_focus_already_foreground(self) -> None:
        mock_api = MockWin32Api()
        mock_api.foreground_hwnd = 200
        dispatcher = Win32InputDispatcher(api=mock_api)

        # Calling focus on already foreground window returns True
        self.assertTrue(dispatcher.focus(200))
        self.assertEqual(mock_api.foreground_hwnd, 200)

    def test_focus_switches_foreground(self) -> None:
        mock_api = MockWin32Api()
        mock_api.foreground_hwnd = 100
        dispatcher = Win32InputDispatcher(api=mock_api)

        self.assertTrue(dispatcher.focus(300))
        self.assertEqual(mock_api.foreground_hwnd, 300)

    def test_inject_and_send_preserves_clipboard(self) -> None:
        mock_api = MockWin32Api()
        mock_api.clipboard_data = "user secret copied"
        dispatcher = Win32InputDispatcher(api=mock_api, restore_clipboard=True)

        success = dispatcher.inject_and_send("Tin nhắn AI soạn sẵn")
        self.assertTrue(success)

        # Sent Ctrl+V and Enter
        self.assertIn("ctrl_v", mock_api.sent_inputs)
        self.assertIn("enter", mock_api.sent_inputs)

        # Clipboard restored back to user's original data
        self.assertEqual(mock_api.clipboard_data, "user secret copied")

    def test_inject_and_send_human_keypress(self) -> None:
        mock_api = MockWin32Api()
        dispatcher = Win32InputDispatcher(api=mock_api)
        success = dispatcher.inject_and_send(
            "Hello",
            mode=InputMode.HUMAN_KEYPRESS,
            min_delay=0.001,
            max_delay=0.002,
        )
        self.assertTrue(success)
        self.assertEqual(mock_api.sent_chars, list("Hello"))
        self.assertIn("enter", mock_api.sent_inputs)
        # Clipboard was not touched
        self.assertEqual(mock_api.clipboard_data, "original clipboard text")

    def test_inject_and_send_empty_fails_gracefully(self) -> None:
        mock_api = MockWin32Api()
        dispatcher = Win32InputDispatcher(api=mock_api)
        self.assertFalse(dispatcher.inject_and_send(""))
        self.assertEqual(mock_api.sent_inputs, [])


if __name__ == "__main__":
    unittest.main()
