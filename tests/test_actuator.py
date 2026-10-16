from __future__ import annotations

import unittest
from autochat.ui.actuator import StagedInputActuator, StagedInputStatus


class MockInjector:
    def __init__(self) -> None:
        self.injected_texts = []
        self.focused_hwnds = []

    def focus(self, hwnd: int) -> bool:
        self.focused_hwnds.append(hwnd)
        return True

    def inject_and_send(self, text: str) -> bool:
        self.injected_texts.append(text)
        return True


class StagedInputActuatorTests(unittest.TestCase):
    def test_stage_and_manual_dispatch(self) -> None:
        injector = MockInjector()
        actuator = StagedInputActuator(injector=injector)

        actuator.stage(text="Dạ em hiểu rồi ạ.", target_hwnd=12345)
        self.assertEqual(actuator.status, StagedInputStatus.STAGED)
        self.assertEqual(actuator.staged_text, "Dạ em hiểu rồi ạ.")

        ok, reason = actuator.trigger_dispatch()
        self.assertTrue(ok)
        self.assertEqual(actuator.status, StagedInputStatus.COMPLETED)
        self.assertEqual(injector.focused_hwnds, [12345])
        self.assertEqual(injector.injected_texts, ["Dạ em hiểu rồi ạ."])

    def test_edit_staged_text_before_dispatch(self) -> None:
        injector = MockInjector()
        actuator = StagedInputActuator(injector=injector)

        actuator.stage(text="Câu gốc ban đầu", target_hwnd=12345)
        actuator.edit_text("Câu đã được người dùng chỉnh sửa")
        self.assertEqual(actuator.staged_text, "Câu đã được người dùng chỉnh sửa")

        actuator.trigger_dispatch()
        self.assertEqual(injector.injected_texts, ["Câu đã được người dùng chỉnh sửa"])

    def test_countdown_autopilot_triggers_dispatch(self) -> None:
        injector = MockInjector()
        actuator = StagedInputActuator(injector=injector)

        actuator.stage(text="Tự động gửi sau 3s", target_hwnd=12345, countdown_seconds=3.0)
        self.assertEqual(actuator.status, StagedInputStatus.COUNTING_DOWN)

        # Tick 2 seconds
        actuator.tick(2.0)
        self.assertEqual(actuator.status, StagedInputStatus.COUNTING_DOWN)
        self.assertAlmostEqual(actuator.countdown_remaining, 1.0)
        self.assertEqual(injector.injected_texts, [])

        # Tick remaining 1 second
        actuator.tick(1.0)
        self.assertEqual(actuator.status, StagedInputStatus.COMPLETED)
        self.assertEqual(injector.injected_texts, ["Tự động gửi sau 3s"])

    def test_cancel_during_countdown_aborts_send(self) -> None:
        injector = MockInjector()
        actuator = StagedInputActuator(injector=injector)

        actuator.stage(text="Sắp gửi", target_hwnd=12345, countdown_seconds=3.0)
        actuator.tick(1.0)
        actuator.cancel()

        self.assertEqual(actuator.status, StagedInputStatus.CANCELLED)
        actuator.tick(5.0)
        self.assertEqual(injector.injected_texts, [])

    def test_guard_blocks_dirty_staged_text(self) -> None:
        injector = MockInjector()
        actuator = StagedInputActuator(injector=injector)

        # CCCD leak
        actuator.stage(text="CCCD của em là 079123456789", target_hwnd=12345)
        ok, reason = actuator.trigger_dispatch()
        self.assertFalse(ok)
        self.assertEqual(actuator.status, StagedInputStatus.BLOCKED)
        self.assertIn("pii_leaked", reason)
        self.assertEqual(injector.injected_texts, [])


if __name__ == "__main__":
    unittest.main()
