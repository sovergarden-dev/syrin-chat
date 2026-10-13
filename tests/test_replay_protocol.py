from __future__ import annotations

from io import StringIO
import json
import unittest

from autochat.protocol import ReplayInputError, load_events, run_replay
from autochat.domain import (
    AutonomyLevel,
    Decision,
    DraftCandidate,
    RuntimePolicy,
    SpeakerState,
)
from autochat.replay import ReplayCoordinator


def event_record(event_id: str, occurrence_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "profile_id": "fixture-profile",
        "conversation_id": "conversation-001",
        "source_epoch": "source-epoch-001",
        "occurrence_id": occurrence_id,
        "speaker_state": "other",
        "text_nfc": "ok",
        "observed_monotonic": 100.0,
        "source_complete": True,
    }


class ReplayProtocolTests(unittest.TestCase):
    def test_loader_preserves_real_repeated_text_as_distinct_occurrences(self) -> None:
        stream = StringIO(
            "\n".join(
                (
                    json.dumps(event_record("event-001", "occurrence-001"), ensure_ascii=False),
                    json.dumps(event_record("event-002", "occurrence-002"), ensure_ascii=False),
                )
            )
        )

        events = load_events(stream)

        self.assertEqual([event.event_id for event in events], ["event-001", "event-002"])
        self.assertEqual([event.occurrence_id for event in events], ["occurrence-001", "occurrence-002"])
        self.assertTrue(all(event.text_nfc == "ok" for event in events))
        self.assertTrue(all(event.speaker_state is SpeakerState.OTHER for event in events))

    def test_loader_rejects_duplicate_json_keys_without_echoing_sensitive_text(self) -> None:
        dangerous = json.dumps(event_record("event-001", "occurrence-001"), ensure_ascii=False)
        dangerous = dangerous.replace('"text_nfc": "ok"', '"text_nfc": "ok", "text_nfc": "MÃ-BÍ-MẬT"')

        with self.assertRaises(ReplayInputError) as raised:
            load_events(StringIO(dangerous))

        self.assertEqual(str(raised.exception), "line 1: invalid_json_object")
        self.assertNotIn("MÃ-BÍ-MẬT", str(raised.exception))

    def test_replay_report_contains_only_metadata_counts(self) -> None:
        class Gate:
            def evaluate(self, context):
                return Decision(True, True, True, frozenset(), "fixture_reply_needed")

        class Generator:
            def generate(self, context, decision):
                return DraftCandidate(
                    "Mình đã xem.", "fixture-local", "fixture-registry-v1", "complete"
                )

        first = event_record("event-self", "occurrence-self")
        first["speaker_state"] = "self"
        events = load_events(
            StringIO(
                "\n".join(
                    (
                        json.dumps(first, ensure_ascii=False),
                        json.dumps(event_record("event-other", "occurrence-other"), ensure_ascii=False),
                    )
                )
            )
        )
        coordinator = ReplayCoordinator(
            profile_id="fixture-profile",
            policy=RuntimePolicy(
                profile_enabled=True,
                read_consent=True,
                source_access_allowed=True,
                requested_level=AutonomyLevel.L2,
                policy_revision="fixture-policy-v1",
            ),
            decision_gate=Gate(),
            generator=Generator(),
        )

        report = run_replay(events, coordinator)

        self.assertEqual(report.events_seen, 2)
        self.assertEqual(report.waiting, 1)
        self.assertEqual(report.suggested, 1)
        self.assertEqual(report.blocked, 0)
        self.assertNotIn("Mình đã xem.", repr(report))
        self.assertEqual(dict(report.reason_counts), {
            "speaker_not_other": 1,
            "review_required_l2": 1,
        })


if __name__ == "__main__":
    unittest.main()
