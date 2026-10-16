from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from autochat.ui.geometry import Rect
from autochat.ui.overlay import OverlayConfig, OverlayState


class OverlayStateTests(unittest.TestCase):
    def test_overlay_config_defaults(self) -> None:
        cfg = OverlayConfig()
        self.assertEqual(cfg.border_width, 2)
        self.assertEqual(cfg.border_color, "#00E5FF")
        self.assertTrue(cfg.exclude_from_capture)
        self.assertTrue(cfg.no_activate)

    def test_overlay_state_roi_update(self) -> None:
        state = OverlayState(initial_roi=Rect(100, 100, 400, 300))
        self.assertEqual(state.current_roi, Rect(100, 100, 400, 300))
        self.assertFalse(state.is_locked)

        state.update_roi(Rect(150, 150, 500, 350))
        self.assertEqual(state.current_roi, Rect(150, 150, 500, 350))

        state.toggle_lock()
        self.assertTrue(state.is_locked)

        # Attempt to update when locked should be ignored or raise
        state.update_roi(Rect(200, 200, 600, 400))
        self.assertEqual(state.current_roi, Rect(150, 150, 500, 350))

    def test_overlay_state_presets(self) -> None:
        state = OverlayState(initial_roi=Rect(100, 100, 400, 300))
        state.save_preset("zalo", Rect(50, 50, 350, 250))
        state.save_preset("game_mmo", Rect(200, 400, 600, 200))

        self.assertEqual(state.get_preset("zalo"), Rect(50, 50, 350, 250))
        self.assertEqual(state.get_preset("game_mmo"), Rect(200, 400, 600, 200))
        self.assertIsNone(state.get_preset("unknown"))

        state.apply_preset("zalo")
        self.assertEqual(state.current_roi, Rect(50, 50, 350, 250))


if __name__ == "__main__":
    unittest.main()
