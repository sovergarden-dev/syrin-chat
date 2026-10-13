from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from autochat.cli import main


class CliTests(unittest.TestCase):
    def test_replay_cli_emits_metadata_only_when_no_model_is_configured(self) -> None:
        event = {
            "event_id": "event-001",
            "profile_id": "fixture-profile",
            "conversation_id": "conversation-001",
            "source_epoch": "source-epoch-001",
            "occurrence_id": "occurrence-001",
            "speaker_state": "other",
            "text_nfc": "MÃ-BÍ-MẬT không được xuất ra báo cáo.",
            "observed_monotonic": 100.0,
            "source_complete": True,
        }
        with TemporaryDirectory() as directory:
            replay_path = Path(directory) / "fixture.jsonl"
            replay_path.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--input", str(replay_path)])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["events_seen"], 1)
        self.assertEqual(payload["suggested"], 0)
        self.assertEqual(payload["waiting"], 1)
        self.assertNotIn("MÃ-BÍ-MẬT", output.getvalue())


if __name__ == "__main__":
    unittest.main()
