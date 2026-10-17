from __future__ import annotations

import unittest
from autochat.perception.frame import Frame
from autochat.perception.settling import FrameSettler, SettlerState
from autochat.perception.detector import DirtyFrameDetector


class FrameSettlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = DirtyFrameDetector(change_threshold=0.1)
        self.settler = FrameSettler(
            detector=self.detector,
            settling_window_seconds=0.2,
            max_wait_seconds=1.0,
        )

    def test_initial_state_is_idle(self) -> None:
        self.assertEqual(self.settler.state, SettlerState.IDLE)

    def test_first_frame_starts_accumulation(self) -> None:
        f0 = Frame(10, 10, 1, bytes([0] * 100))
        # First frame triggers detector baseline
        status = self.settler.process_frame(f0, timestamp=100.0)
        self.assertEqual(self.settler.state, SettlerState.ACCUMULATING)
        self.assertIsNone(status)

    def test_frame_settles_after_window_passes_without_motion(self) -> None:
        f0 = Frame(10, 10, 1, bytes([0] * 100))
        self.settler.process_frame(f0, timestamp=100.0)

        # Still same frame at 100.1s (< 0.2s window)
        res1 = self.settler.process_frame(f0, timestamp=100.1)
        self.assertIsNone(res1)
        self.assertEqual(self.settler.state, SettlerState.ACCUMULATING)

        # Still same frame at 100.25s (>= 0.2s window) -> Settled!
        res2 = self.settler.process_frame(f0, timestamp=100.25)
        self.assertIsNotNone(res2)
        self.assertEqual(self.settler.state, SettlerState.SETTLED)
        self.assertEqual(res2, f0)

    def test_intermediate_changes_reset_settling_window(self) -> None:
        f0 = Frame(10, 10, 1, bytes([0] * 100))
        self.settler.process_frame(f0, timestamp=100.0)

        # New change at 100.15s (typing animation continues)
        f1 = Frame(10, 10, 1, bytes([255] * 20 + [0] * 80))
        res1 = self.settler.process_frame(f1, timestamp=100.15)
        self.assertIsNone(res1)
        self.assertEqual(self.settler.state, SettlerState.ACCUMULATING)

        # At 100.25s, only 0.10s since f1 change -> not settled yet
        res2 = self.settler.process_frame(f1, timestamp=100.25)
        self.assertIsNone(res2)

        # At 100.36s, 0.21s since f1 change -> settled!
        res3 = self.settler.process_frame(f1, timestamp=100.36)
        self.assertIsNotNone(res3)
        self.assertEqual(res3, f1)

    def test_max_wait_forces_settling_even_with_constant_motion(self) -> None:
        f0 = Frame(10, 10, 1, bytes([0] * 100))
        self.settler.process_frame(f0, timestamp=100.0)

        # Constant jitter every 0.1s for 1.2s (> max_wait 1.0s)
        res = None
        for i in range(1, 13):
            t = 100.0 + i * 0.1
            f = Frame(10, 10, 1, bytes([(i * 10) % 256] * 100))
            res = self.settler.process_frame(f, timestamp=t)
            if res is not None:
                break

        self.assertIsNotNone(res)
        self.assertEqual(self.settler.state, SettlerState.SETTLED)


if __name__ == "__main__":
    unittest.main()
