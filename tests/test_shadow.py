from __future__ import annotations

import unittest
from autochat.shadow import ShadowEvent, ShadowCollector, ShadowMetricsSummary


class ShadowCollectorTests(unittest.TestCase):
    def test_record_shadow_trial_and_summarize(self) -> None:
        collector = ShadowCollector()
        event = ShadowEvent(
            trial_id="trial-001",
            conversation_id="conv-1",
            decision_latency_ms=120.0,
            generation_latency_ms=450.0,
            decision_needs_reply=True,
            decision_confidence=0.92,
            misfire=False,
            rejected_by_guard=False,
            user_accepted_without_edit=True,
        )
        collector.record(event)
        summary = collector.summarize()
        self.assertEqual(summary.total_trials, 1)
        self.assertEqual(summary.misfires, 0)
        self.assertEqual(summary.accepted_without_edit, 1)
        self.assertAlmostEqual(summary.acceptance_rate, 1.0)
        self.assertAlmostEqual(summary.misfire_rate, 0.0)

    def test_misfire_tracking_for_g6(self) -> None:
        collector = ShadowCollector()
        for i in range(10):
            collector.record(
                ShadowEvent(
                    trial_id=f"trial-{i}",
                    conversation_id="conv-1",
                    decision_latency_ms=100.0,
                    generation_latency_ms=300.0,
                    decision_needs_reply=True,
                    decision_confidence=0.85,
                    misfire=(i == 5),
                    rejected_by_guard=False,
                    user_accepted_without_edit=(i != 5),
                )
            )
        summary = collector.summarize()
        self.assertEqual(summary.total_trials, 10)
        self.assertEqual(summary.misfires, 1)
        self.assertAlmostEqual(summary.misfire_rate, 0.1)
        self.assertEqual(summary.accepted_without_edit, 9)
        self.assertAlmostEqual(summary.acceptance_rate, 0.9)

    def test_p95_latency_calculation(self) -> None:
        collector = ShadowCollector()
        for i in range(100):
            collector.record(
                ShadowEvent(
                    trial_id=f"trial-{i}",
                    conversation_id="conv-1",
                    decision_latency_ms=float(i + 1),
                    generation_latency_ms=float((i + 1) * 2),
                    decision_needs_reply=True,
                    decision_confidence=0.9,
                    misfire=False,
                    rejected_by_guard=False,
                    user_accepted_without_edit=True,
                )
            )
        summary = collector.summarize()
        self.assertGreaterEqual(summary.p95_decision_latency_ms, 95.0)
        self.assertGreaterEqual(summary.p95_generation_latency_ms, 190.0)

    def test_summary_does_not_contain_text(self) -> None:
        collector = ShadowCollector()
        collector.record(
            ShadowEvent(
                trial_id="trial-sec",
                conversation_id="conv-sec",
                decision_latency_ms=50.0,
                generation_latency_ms=200.0,
                decision_needs_reply=True,
                decision_confidence=0.95,
                misfire=False,
                rejected_by_guard=False,
                user_accepted_without_edit=True,
            )
        )
        summary_repr = repr(collector.summarize())
        self.assertNotIn("text", summary_repr.lower())
        self.assertNotIn("secret", summary_repr.lower())


if __name__ == "__main__":
    unittest.main()
