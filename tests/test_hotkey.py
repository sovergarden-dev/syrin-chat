from __future__ import annotations

import unittest
from autochat.ui.hotkey import GlobalHotkeyBridge, HotkeyAction


class MockUser32HotkeyApi:
    def __init__(self) -> None:
        self.registered_hotkeys = {}
        self.next_id = 1

    def RegisterHotKey(self, hwnd: int, hotkey_id: int, fsModifiers: int, vk: int) -> int:
        self.registered_hotkeys[hotkey_id] = (fsModifiers, vk)
        return 1

    def UnregisterHotKey(self, hwnd: int, hotkey_id: int) -> int:
        if hotkey_id in self.registered_hotkeys:
            del self.registered_hotkeys[hotkey_id]
            return 1
        return 0


class HotkeyBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_api = MockUser32HotkeyApi()
        self.bridge = GlobalHotkeyBridge(api=self.mock_api)
        self.dispatched_actions = []

    def test_register_standard_hotkeys(self) -> None:
        self.bridge.register_action(
            HotkeyAction.SEND_IMMEDIATE,
            vk=0x77,  # VK_F8
            modifiers=0,
            callback=lambda: self.dispatched_actions.append("send"),
        )
        self.bridge.register_action(
            HotkeyAction.CANCEL_DRAFT,
            vk=0x1B,  # VK_ESCAPE
            modifiers=0,
            callback=lambda: self.dispatched_actions.append("cancel"),
        )
        self.bridge.register_action(
            HotkeyAction.PANIC_STOP,
            vk=0x58,  # 'X'
            modifiers=0x0001 | 0x0002 | 0x0004,  # MOD_ALT | MOD_CONTROL | MOD_SHIFT
            callback=lambda: self.dispatched_actions.append("panic"),
        )

        self.assertEqual(len(self.mock_api.registered_hotkeys), 3)

        # Simulate receiving hotkey messages
        self.bridge.handle_hotkey_id(1)
        self.assertEqual(self.dispatched_actions, ["send"])

        self.bridge.handle_hotkey_id(2)
        self.assertEqual(self.dispatched_actions, ["send", "cancel"])

        self.bridge.handle_hotkey_id(3)
        self.assertEqual(self.dispatched_actions, ["send", "cancel", "panic"])

    def test_unregister_all_hotkeys(self) -> None:
        self.bridge.register_action(
            HotkeyAction.SEND_IMMEDIATE,
            vk=0x77,
            modifiers=0,
            callback=lambda: None,
        )
        self.assertEqual(len(self.mock_api.registered_hotkeys), 1)

        self.bridge.unregister_all()
        self.assertEqual(len(self.mock_api.registered_hotkeys), 0)


if __name__ == "__main__":
    unittest.main()
