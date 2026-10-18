from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from autochat.cli_live import main_live


class CliLiveTests(unittest.TestCase):
    def test_cli_live_mock_once_emits_json_summary(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = main_live(["--mock", "--once"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        # Ensure output contains valid JSON line
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        self.assertTrue(len(lines) > 0)
        last_obj = json.loads(lines[-1])
        self.assertIn("steps_executed", last_obj)
        self.assertIn("status", last_obj)
        self.assertEqual(last_obj["steps_executed"], 1)

    def test_cli_live_mock_max_steps(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = main_live(["--mock", "--max-steps", "3", "--interval", "0.001"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        last_obj = json.loads(lines[-1])
        self.assertEqual(last_obj["steps_executed"], 3)


if __name__ == "__main__":
    unittest.main()
