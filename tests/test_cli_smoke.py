from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from autochat.cli_smoke import main_smoke


class CliSmokeTests(unittest.TestCase):
    def test_smoke_detector_benchmark(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = main_smoke(["detector", "--iterations", "50"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        self.assertTrue(len(lines) > 0)
        result = json.loads(lines[-1])
        self.assertEqual(result["check"], "detector")
        self.assertEqual(result["status"], "passed")
        self.assertIn("microseconds_per_diff", result)

    def test_smoke_capture_mock(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = main_smoke(["capture", "--mock"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        result = json.loads(output.splitlines()[-1])
        self.assertEqual(result["check"], "capture")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["width"], 100)
        self.assertEqual(result["height"], 50)

    def test_smoke_clipboard_mock_api(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = main_smoke(["clipboard", "--mock"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        result = json.loads(output.splitlines()[-1])
        self.assertEqual(result["check"], "clipboard")
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["restored_cleanly"])


if __name__ == "__main__":
    unittest.main()
