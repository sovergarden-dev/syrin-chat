from __future__ import annotations

import threading
import unittest

from autochat.domain import (
    AutonomyLevel,
    Decision,
    DraftCandidate,
    MessageEvent,
    RuntimePolicy,
    SpeakerState,
)
from autochat.replay import ReplayCoordinator, SuggestionState


class StaticDecisionGate:
    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        self.contexts = []

    def evaluate(self, context):
        self.contexts.append(context)
        return self.decision


class StaticGenerator:
    def __init__(self, candidate: DraftCandidate) -> None:
        self.candidate = candidate
        self.contexts = []

    def generate(self, context, decision):
        self.contexts.append((context, decision))
        return self.candidate


class ReplayFlowTests(unittest.TestCase):
    def test_complete_other_message_produces_reviewable_l2_draft(self) -> None:
        decision_gate = StaticDecisionGate(
            Decision(
                addressed_to_user=True,
                needs_reply=True,
                turn_complete=True,
                risk_flags=frozenset(),
                rationale_code="fixture_reply_needed",
            )
        )
        generator = StaticGenerator(
            DraftCandidate(
                reply_text="Mình đã nhận. Cảm ơn bạn.",
                route_id="fixture-local",
                model_registry_revision="fixture-registry-v1",
                finish_status="complete",
            )
        )
        coordinator = ReplayCoordinator(
            profile_id="fixture-profile",
            policy=RuntimePolicy(
                profile_enabled=True,
                read_consent=True,
                source_access_allowed=True,
                requested_level=AutonomyLevel.L4,
                policy_revision="fixture-policy-v1",
            ),
            decision_gate=decision_gate,
            generator=generator,
        )
        event = MessageEvent(
            event_id="event-001",
            profile_id="fixture-profile",
            conversation_id="conversation-001",
            source_epoch="source-epoch-001",
            occurrence_id="occurrence-001",
            speaker_state=SpeakerState.OTHER,
            text_nfc="Bạn đã xem giúp mình chưa?",
            observed_monotonic=100.0,
            source_complete=True,
        )

        result = coordinator.ingest(event)

        self.assertEqual(result.state, SuggestionState.SUGGESTED)
        self.assertEqual(result.effective_level, AutonomyLevel.L2)
        self.assertEqual(result.context_revision, 1)
        self.assertEqual(result.draft.reply_text, "Mình đã nhận. Cảm ơn bạn.")
        self.assertEqual(result.draft.route_id, "fixture-local")
        self.assertEqual(len(decision_gate.contexts), 1)
        self.assertEqual(len(generator.contexts), 1)

    def test_l0_does_not_retain_or_process_an_observed_event(self) -> None:
        decision_gate = StaticDecisionGate(
            Decision(True, True, True, frozenset(), "fixture_reply_needed")
        )
        generator = StaticGenerator(
            DraftCandidate("Đã nhận.", "fixture-local", "fixture-registry-v1", "complete")
        )
        coordinator = ReplayCoordinator(
            profile_id="fixture-profile",
            policy=RuntimePolicy(
                profile_enabled=True,
                read_consent=False,
                source_access_allowed=True,
                requested_level=AutonomyLevel.L2,
                policy_revision="fixture-policy-v1",
            ),
            decision_gate=decision_gate,
            generator=generator,
        )

        result = coordinator.ingest(
            MessageEvent(
                event_id="event-without-consent",
                profile_id="fixture-profile",
                conversation_id="conversation-001",
                source_epoch="source-epoch-001",
                occurrence_id="occurrence-001",
                speaker_state=SpeakerState.OTHER,
                text_nfc="Tin không được phép đọc.",
                observed_monotonic=100.0,
                source_complete=True,
            )
        )

        self.assertEqual(result.state, SuggestionState.OFF)
        self.assertEqual(result.context_revision, 0)
        self.assertEqual(decision_gate.contexts, [])
        self.assertEqual(generator.contexts, [])


class SafetyFlowTests(unittest.TestCase):
    def _coordinator(self):
        gate = StaticDecisionGate(
            Decision(True, True, True, frozenset(), "fixture_reply_needed")
        )
        generator = StaticGenerator(
            DraftCandidate("Đã nhận.", "fixture-local", "fixture-registry-v1", "complete")
        )
        return (
            ReplayCoordinator(
                profile_id="fixture-profile",
                policy=RuntimePolicy(
                    profile_enabled=True,
                    read_consent=True,
                    source_access_allowed=True,
                    requested_level=AutonomyLevel.L2,
                    policy_revision="fixture-policy-v1",
                ),
                decision_gate=gate,
                generator=generator,
            ),
            gate,
            generator,
        )

    def test_unknown_speaker_never_reaches_decision_or_generation(self) -> None:
        coordinator, gate, generator = self._coordinator()

        result = coordinator.ingest(
            MessageEvent(
                event_id="event-unknown-speaker",
                profile_id="fixture-profile",
                conversation_id="conversation-001",
                source_epoch="source-epoch-001",
                occurrence_id="occurrence-001",
                speaker_state=SpeakerState.UNKNOWN,
                text_nfc="Không rõ ai gửi.",
                observed_monotonic=100.0,
                source_complete=True,
            )
        )

        self.assertEqual(result.state, SuggestionState.WAITING)
        self.assertEqual(result.reason_code, "speaker_not_other")
        self.assertEqual(gate.contexts, [])
        self.assertEqual(generator.contexts, [])

    def test_incomplete_source_never_reaches_decision_or_generation(self) -> None:
        coordinator, gate, generator = self._coordinator()

        result = coordinator.ingest(
            MessageEvent(
                event_id="event-incomplete-source",
                profile_id="fixture-profile",
                conversation_id="conversation-001",
                source_epoch="source-epoch-001",
                occurrence_id="occurrence-001",
                speaker_state=SpeakerState.OTHER,
                text_nfc="Tin bị cắt dở.",
                observed_monotonic=100.0,
                source_complete=False,
            )
        )

        self.assertEqual(result.state, SuggestionState.WAITING)
        self.assertEqual(result.reason_code, "source_incomplete")
        self.assertEqual(gate.contexts, [])
        self.assertEqual(generator.contexts, [])


class CancellationTests(unittest.TestCase):
    def test_cancel_is_not_blocked_by_generation_and_invalidates_draft(self) -> None:
        started = threading.Event()
        release = threading.Event()
        cancel_finished = threading.Event()

        class BlockingGenerator:
            def generate(self, context, decision):
                started.set()
                if not release.wait(2):
                    raise TimeoutError("test did not release generation")
                return DraftCandidate(
                    "Đã nhận.", "fixture-local", "fixture-registry-v1", "complete"
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
            decision_gate=StaticDecisionGate(
                Decision(True, True, True, frozenset(), "fixture_reply_needed")
            ),
            generator=BlockingGenerator(),
        )
        outcome = {}

        def ingest() -> None:
            outcome["result"] = coordinator.ingest(
                MessageEvent(
                    event_id="event-cancel-001",
                    profile_id="fixture-profile",
                    conversation_id="conversation-001",
                    source_epoch="source-epoch-001",
                    occurrence_id="occurrence-001",
                    speaker_state=SpeakerState.OTHER,
                    text_nfc="Bạn đang rảnh không?",
                    observed_monotonic=100.0,
                    source_complete=True,
                )
            )

        def cancel() -> None:
            coordinator.cancel()
            cancel_finished.set()

        ingest_thread = threading.Thread(target=ingest)
        cancel_thread = threading.Thread(target=cancel)
        ingest_thread.start()
        self.assertTrue(started.wait(1), "generation never started")
        cancel_thread.start()
        try:
            self.assertTrue(cancel_finished.wait(0.2), "cancel was blocked by generation")
        finally:
            release.set()
            ingest_thread.join(2)
            cancel_thread.join(2)
        self.assertFalse(ingest_thread.is_alive())
        self.assertFalse(cancel_thread.is_alive())
        self.assertEqual(outcome["result"].state, SuggestionState.CANCELLED)
        self.assertEqual(outcome["result"].reason_code, "cancelled_during_generation")


class FailureContainmentTests(unittest.TestCase):
    def test_decision_exception_becomes_a_content_free_block(self) -> None:
        class ExplodingGate:
            def evaluate(self, context):
                raise RuntimeError("message content must not escape into status")

        generator = StaticGenerator(
            DraftCandidate("Đã nhận.", "fixture-local", "fixture-registry-v1", "complete")
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
            decision_gate=ExplodingGate(),
            generator=generator,
        )

        result = coordinator.ingest(
            MessageEvent(
                event_id="event-decision-error",
                profile_id="fixture-profile",
                conversation_id="conversation-001",
                source_epoch="source-epoch-001",
                occurrence_id="occurrence-001",
                speaker_state=SpeakerState.OTHER,
                text_nfc="Bạn đọc tin nhắn này nhé.",
                observed_monotonic=100.0,
                source_complete=True,
            )
        )

        self.assertEqual(result.state, SuggestionState.BLOCKED)
        self.assertEqual(result.reason_code, "decision_error")
        self.assertEqual(generator.contexts, [])

    def test_generation_exception_becomes_a_content_free_block(self) -> None:
        class ExplodingGenerator:
            def generate(self, context, decision):
                raise RuntimeError("do not expose generated content or provider details")

        coordinator = ReplayCoordinator(
            profile_id="fixture-profile",
            policy=RuntimePolicy(
                profile_enabled=True,
                read_consent=True,
                source_access_allowed=True,
                requested_level=AutonomyLevel.L2,
                policy_revision="fixture-policy-v1",
            ),
            decision_gate=StaticDecisionGate(
                Decision(True, True, True, frozenset(), "fixture_reply_needed")
            ),
            generator=ExplodingGenerator(),
        )

        result = coordinator.ingest(
            MessageEvent(
                event_id="event-generation-error",
                profile_id="fixture-profile",
                conversation_id="conversation-001",
                source_epoch="source-epoch-001",
                occurrence_id="occurrence-001",
                speaker_state=SpeakerState.OTHER,
                text_nfc="Bạn đọc tin nhắn này nhé.",
                observed_monotonic=100.0,
                source_complete=True,
            )
        )

        self.assertEqual(result.state, SuggestionState.BLOCKED)
        self.assertEqual(result.reason_code, "generation_error")

    def test_untrusted_risk_labels_never_enter_the_result_reason(self) -> None:
        coordinator = ReplayCoordinator(
            profile_id="fixture-profile",
            policy=RuntimePolicy(
                profile_enabled=True,
                read_consent=True,
                source_access_allowed=True,
                requested_level=AutonomyLevel.L2,
                policy_revision="fixture-policy-v1",
            ),
            decision_gate=StaticDecisionGate(
                Decision(True, True, True, frozenset({"MÃ-BÍ-MẬT"}), "fixture_risk")
            ),
            generator=StaticGenerator(
                DraftCandidate("Đã nhận.", "fixture-local", "fixture-registry-v1", "complete")
            ),
        )

        result = coordinator.ingest(
            MessageEvent(
                event_id="event-risk-label",
                profile_id="fixture-profile",
                conversation_id="conversation-001",
                source_epoch="source-epoch-001",
                occurrence_id="occurrence-001",
                speaker_state=SpeakerState.OTHER,
                text_nfc="Dữ liệu không được đưa vào telemetry.",
                observed_monotonic=100.0,
                source_complete=True,
            )
        )

        self.assertEqual(result.state, SuggestionState.BLOCKED)
        self.assertEqual(result.reason_code, "hard_risk")
        self.assertNotIn("MÃ-BÍ-MẬT", result.reason_code)


if __name__ == "__main__":
    unittest.main()
