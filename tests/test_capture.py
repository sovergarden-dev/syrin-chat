from __future__ import annotations

import unittest
from autochat.perception.frame import Frame
from autochat.perception.capture import MockCaptureBackend, ScreenRegionCapture
from autochat.ui.geometry import Rect


class CaptureTests(unittest.TestCase):
    def test_mock_capture_returns_configured_frame(self) -> None:
        raw_data = bytes([255] * (50 * 50 * 4))
        target_frame = Frame(width=50, height=50, channels=4, data=raw_data)

        backend = MockCaptureBackend(default_frame=target_frame)
        self.assertIsInstance(backend, ScreenRegionCapture)

        captured = backend.capture_region(Rect(10, 10, 50, 50))
        self.assertIsNotNone(captured)
        self.assertEqual(captured.width, 50)
        self.assertEqual(captured.height, 50)
        self.assertEqual(captured.channels, 4)

    def test_mock_capture_crops_if_requested_smaller(self) -> None:
        raw_data = bytes([100] * (100 * 100 * 4))
        target_frame = Frame(width=100, height=100, channels=4, data=raw_data)

        backend = MockCaptureBackend(default_frame=target_frame)
        cropped = backend.capture_region(Rect(0, 0, 40, 30))
        self.assertIsNotNone(cropped)
        self.assertEqual(cropped.width, 40)
        self.assertEqual(cropped.height, 30)

    def test_mock_capture_returns_none_when_empty(self) -> None:
        backend = MockCaptureBackend(default_frame=None)
        captured = backend.capture_region(Rect(0, 0, 50, 50))
        self.assertIsNone(captured)


if __name__ == "__main__":
    unittest.main()
