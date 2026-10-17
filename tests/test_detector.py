from __future__ import annotations

import unittest
from autochat.perception.frame import Frame
from autochat.perception.detector import DirtyFrameDetector
from autochat.ui.geometry import Rect


class FrameTests(unittest.TestCase):
    def test_frame_creation_and_properties(self) -> None:
        raw = bytes([128] * (10 * 20 * 4))
        frame = Frame(width=10, height=20, channels=4, data=raw)
        self.assertEqual(frame.width, 10)
        self.assertEqual(frame.height, 20)
        self.assertEqual(frame.channels, 4)
        self.assertEqual(len(frame.data), 800)

    def test_frame_invalid_data_length(self) -> None:
        with self.assertRaises(ValueError):
            Frame(width=10, height=20, channels=4, data=b"too_short")

    def test_frame_crop(self) -> None:
        # 4x4 image with 1 channel
        data = bytes(range(16))
        frame = Frame(width=4, height=4, channels=1, data=data)
        # Crop 2x2 from top-left (1, 1)
        cropped = frame.crop(Rect(x=1, y=1, width=2, height=2))
        self.assertEqual(cropped.width, 2)
        self.assertEqual(cropped.height, 2)
        self.assertEqual(cropped.channels, 1)
        # Row 1: index 5, 6; Row 2: index 9, 10
        self.assertEqual(list(cropped.data), [5, 6, 9, 10])


class DirtyFrameDetectorTests(unittest.TestCase):
    def test_initial_frame_is_dirty(self) -> None:
        detector = DirtyFrameDetector(change_threshold=0.05)
        frame = Frame(width=10, height=10, channels=1, data=bytes([0] * 100))
        self.assertTrue(detector.is_dirty(frame))

    def test_identical_frame_is_not_dirty(self) -> None:
        detector = DirtyFrameDetector(change_threshold=0.05)
        frame1 = Frame(width=10, height=10, channels=1, data=bytes([100] * 100))
        frame2 = Frame(width=10, height=10, channels=1, data=bytes([100] * 100))

        self.assertTrue(detector.is_dirty(frame1))  # Baseline
        self.assertFalse(detector.is_dirty(frame2))  # Unchanged

    def test_sub_threshold_noise_is_not_dirty(self) -> None:
        detector = DirtyFrameDetector(change_threshold=0.10, pixel_delta_threshold=30)
        # 100 pixels, all 100
        f1 = Frame(width=10, height=10, channels=1, data=bytes([100] * 100))
        # 3 pixels changed slightly (below 10% change threshold)
        data2 = bytearray([100] * 100)
        data2[0] = 150
        data2[1] = 150
        data2[2] = 150
        f2 = Frame(width=10, height=10, channels=1, data=bytes(data2))

        self.assertTrue(detector.is_dirty(f1))
        self.assertFalse(detector.is_dirty(f2))

    def test_text_change_is_dirty(self) -> None:
        detector = DirtyFrameDetector(change_threshold=0.05, pixel_delta_threshold=30)
        f1 = Frame(width=10, height=10, channels=1, data=bytes([0] * 100))
        # 20 pixels turned bright white (text added)
        data2 = bytearray([0] * 100)
        for i in range(20):
            data2[i] = 255
        f2 = Frame(width=10, height=10, channels=1, data=bytes(data2))

        self.assertTrue(detector.is_dirty(f1))
        self.assertTrue(detector.is_dirty(f2))  # 20% changed > 5% threshold


if __name__ == "__main__":
    unittest.main()
