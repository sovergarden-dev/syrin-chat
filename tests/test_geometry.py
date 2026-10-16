from __future__ import annotations

import unittest
from autochat.ui.geometry import (
    Rect,
    NormalizedRect,
    DpiScale,
    WindowAnchor,
)


class GeometryTests(unittest.TestCase):
    def test_rect_validation_and_properties(self) -> None:
        r = Rect(10, 20, 100, 200)
        self.assertEqual(r.x, 10)
        self.assertEqual(r.y, 20)
        self.assertEqual(r.width, 100)
        self.assertEqual(r.height, 200)
        self.assertEqual(r.right, 110)
        self.assertEqual(r.bottom, 220)

    def test_rect_invalid_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            Rect(0, 0, 0, 10)
        with self.assertRaises(ValueError):
            Rect(0, 0, 10, -5)

    def test_rect_contains_and_clamp(self) -> None:
        parent = Rect(0, 0, 1920, 1080)
        child = Rect(100, 100, 400, 300)
        self.assertTrue(parent.contains(child))

        out_of_bounds = Rect(1800, 1000, 300, 200)
        clamped = out_of_bounds.clamp_to(parent)
        self.assertEqual(clamped.right, 1920)
        self.assertEqual(clamped.bottom, 1080)
        self.assertEqual(clamped.width, 300)
        self.assertEqual(clamped.height, 200)

    def test_normalized_rect_conversion(self) -> None:
        parent = Rect(100, 100, 1000, 800)
        child = Rect(200, 300, 500, 400)

        norm = NormalizedRect.from_absolute(child, parent)
        self.assertAlmostEqual(norm.dx, 0.1)  # (200 - 100) / 1000
        self.assertAlmostEqual(norm.dy, 0.25)  # (300 - 100) / 800
        self.assertAlmostEqual(norm.width, 0.5)  # 500 / 1000
        self.assertAlmostEqual(norm.height, 0.5)  # 400 / 800

        reconstructed = norm.to_absolute(parent)
        self.assertEqual(reconstructed.x, 200)
        self.assertEqual(reconstructed.y, 300)
        self.assertEqual(reconstructed.width, 500)
        self.assertEqual(reconstructed.height, 400)

    def test_dpi_scaling(self) -> None:
        dpi = DpiScale(scale_factor=1.5)  # 150% scaling
        logical = Rect(100, 100, 200, 150)
        physical = dpi.logical_to_physical(logical)
        self.assertEqual(physical.x, 150)
        self.assertEqual(physical.y, 150)
        self.assertEqual(physical.width, 300)
        self.assertEqual(physical.height, 225)

        back_to_logical = dpi.physical_to_logical(physical)
        self.assertEqual(back_to_logical.x, 100)
        self.assertEqual(back_to_logical.y, 100)
        self.assertEqual(back_to_logical.width, 200)
        self.assertEqual(back_to_logical.height, 150)

    def test_window_anchor_update(self) -> None:
        initial_parent = Rect(200, 200, 1000, 800)
        initial_roi = Rect(300, 400, 400, 300)
        anchor = WindowAnchor.create(hwnd=12345, parent_rect=initial_parent, roi_rect=initial_roi)

        # Parent moves to new coordinates
        new_parent = Rect(400, 500, 1000, 800)
        updated_roi = anchor.compute_roi(new_parent)
        self.assertEqual(updated_roi.x, 500)
        self.assertEqual(updated_roi.y, 700)
        self.assertEqual(updated_roi.width, 400)
        self.assertEqual(updated_roi.height, 300)

    def test_window_anchor_clamps_when_parent_shrinks(self) -> None:
        initial_parent = Rect(0, 0, 1000, 1000)
        initial_roi = Rect(800, 800, 200, 200)
        anchor = WindowAnchor.create(hwnd=12345, parent_rect=initial_parent, roi_rect=initial_roi)

        # Parent shrinks to half size
        shrunk_parent = Rect(0, 0, 500, 500)
        clamped_roi = anchor.compute_roi(shrunk_parent)
        self.assertTrue(shrunk_parent.contains(clamped_roi))
        self.assertEqual(clamped_roi.right, 500)
        self.assertEqual(clamped_roi.bottom, 500)


if __name__ == "__main__":
    unittest.main()
