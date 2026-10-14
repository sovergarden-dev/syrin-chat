from __future__ import annotations

import json
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from autochat.domain import AutonomyLevel
from autochat.guard import ConversationRateLimiter
from autochat.policy import (
    IDENTITY_FIELDS,
    MAX_PERMIT_TTL_SECONDS,
    DUPLICATE_ATTEMPT_WINDOW_SECONDS_MIN,
    MIN_ACCEPTANCE_RATE_FOR_L3,
    MIN_L2_REVIEWS_FOR_L3,
    MIN_SHADOW_TRIALS_FOR_L4,
    ON_LOW_CONFIDENCE,
    AttemptLedger,
    DeliveryState,
    ProfilePolicy,
    Qualification,
    SendPermit,
    Snapshot,
    draft_digest,
    effective_level,
    low_confidence_action,
)

ROOT = Path(__file__).resolve().parents[1]


def good_policy() -> ProfilePolicy:
    return ProfilePolicy(
        enabled=True,
        read_consent=True,
        source_access_allowed=True,
        sensitive=False,
        requested=AutonomyLevel.L4,
        tos_status="allowed",
        protection_status="absent",
        send_method="uia_value_pattern",
        recipient_allowlist=frozenset({"fixture:conversation:42"}),
        disclosure=True,
        revision="fixture-policy-v1",
    )


def good_qualification() -> Qualification:
    # Fixture giả định ĐÃ review — không phải evidence Windows thật.
    return Qualification(
        source_qualified=True,
        speaker_qualified=True,
        generation_qualified=True,
        action_qualified=True,
        decision_calibrated=True,
        gate_report_bound=True,
        l2_reviews=200,
        acceptance_rate=0.70,
        shadow_trials=500,
        shadow_misfires=0,
    )


def good_snapshot() -> Snapshot:
    return Snapshot(
        hwnd=101,
        pid=202,
        process_start_token="fixture-start-token",
        conversation_id="fixture:conversation:42",
        conversation_revision=3,
        source_epoch="fixture-source-epoch-1",
        last_message_revision=5,
        human_input_revision=7,
        target_input_revision=2,
        policy_revision="fixture-policy-v1",
        cancel_generation=0,
        draft_hash=draft_digest("ok, mình đã đọc · (trợ lý AI)"),
        input_empty=True,
        target_foreground=True,
        source_valid=True,
        speaker_known=True,
        presence_known=True,
        user_idle_seconds=4,
        draft_complete=True,
        guard_passed=True,
        hard_block=False,
        soft_uncertain=False,
        turn_complete=True,
        budget_ok=True,
        rate_ok=True,
        user_approved=True,
        countdown_completed=True,
    )


class EffectiveLevelTests(unittest.TestCase):
    def test_qualified_L4(self):
        self.assertEqual(effective_level(good_policy(), good_qualification()).level, AutonomyLevel.L4)

    def test_never_elevates_requested_level(self):
        for level in AutonomyLevel:
            self.assertEqual(
                effective_level(replace(good_policy(), requested=level), good_qualification()).level,
                level,
            )

    def test_ocr_required_but_not_qualified_caps_L1(self):
        q = replace(good_qualification(), ocr_required=True, ocr_qualified=False)
        self.assertEqual(effective_level(good_policy(), q).level, AutonomyLevel.L1)

    def test_ocr_not_required_does_not_block(self):
        self.assertEqual(effective_level(good_policy(), good_qualification()).level, AutonomyLevel.L4)

    def test_unknown_tos_saved_setting_is_capped(self):
        p = replace(good_policy(), tos_status="unknown", send_method="none_user_types")
        self.assertEqual(effective_level(p, good_qualification()).level, AutonomyLevel.L2)

    def test_invalid_policy_boolean_rejected(self):
        with self.assertRaises(ValueError):
            replace(good_policy(), disclosure="true")

    def test_invalid_qualification_nan_rejected(self):
        with self.assertRaises(ValueError):
            replace(good_qualification(), acceptance_rate=float("nan"))

    def test_invalid_qualification_counts_rejected(self):
        with self.assertRaises(ValueError):
            replace(good_qualification(), shadow_trials=-1)

    def test_empty_draft_rejected(self):
        with self.assertRaises(ValueError):
            draft_digest("  ")

    def test_changed_suffix_changes_hash(self):
        self.assertNotEqual(draft_digest("ok"), draft_digest("ok · (trợ lý AI)")) 

    def test_reasons_explain_caps(self):
        eligibility = effective_level(
            replace(good_policy(), tos_status="prohibited"), good_qualification()
        )
        self.assertTrue(eligibility.reasons)


def make_cap_test(field, value, expected):
    def test(self):
        p = replace(good_policy(), **{field: value})
        self.assertLessEqual(effective_level(p, good_qualification()).level, expected)
    return test


for field, value, cap in [
    ("enabled", False, AutonomyLevel.L0),
    ("read_consent", False, AutonomyLevel.L0),
    ("source_access_allowed", False, AutonomyLevel.L0),
    ("sensitive", True, AutonomyLevel.L0),
    ("tos_status", "unknown", AutonomyLevel.L2),
    ("tos_status", "prohibited", AutonomyLevel.L2),
    ("protection_status", "present", AutonomyLevel.L2),
    ("protection_status", "unknown", AutonomyLevel.L2),
    ("send_method", "none_user_types", AutonomyLevel.L2),
    ("disclosure", False, AutonomyLevel.L3),
    ("recipient_allowlist", frozenset(), AutonomyLevel.L3),
]:
    setattr(EffectiveLevelTests, f"test_cap_{field}_{str(value).replace(' ', '_')}",
            make_cap_test(field, value, cap))


def make_evidence_test(field, value, expected):
    def test(self):
        q = replace(good_qualification(), **{field: value})
        self.assertLessEqual(effective_level(good_policy(), q).level, expected)
    return test


for field, value, cap in [
    ("source_qualified", False, AutonomyLevel.L1),
    ("speaker_qualified", False, AutonomyLevel.L1),
    ("generation_qualified", False, AutonomyLevel.L2),
    ("action_qualified", False, AutonomyLevel.L2),
    ("gate_report_bound", False, AutonomyLevel.L2),
    ("l2_reviews", 199, AutonomyLevel.L2),
    ("acceptance_rate", 0.699, AutonomyLevel.L2),
    ("critical_errors", 1, AutonomyLevel.L2),
    ("decision_calibrated", False, AutonomyLevel.L3),
    ("shadow_trials", 499, AutonomyLevel.L3),
    ("shadow_misfires", 1, AutonomyLevel.L3),
]:
    setattr(EffectiveLevelTests, f"test_evidence_{field}", make_evidence_test(field, value, cap))


class PermitTests(unittest.TestCase):
    def consume(self, current=None, policy=None, qualification=None, action="send", now=101):
        permit = SendPermit(good_snapshot(), created_at=100)
        return permit.consume(
            action=action,
            current=current or good_snapshot(),
            policy=policy or good_policy(),
            qualification=qualification or good_qualification(),
            now=now,
        )

    def test_good_send(self):
        self.assertTrue(self.consume()[0])

    def test_good_fill_L3(self):
        self.assertTrue(self.consume(
            policy=replace(good_policy(), requested=AutonomyLevel.L3), action="fill")[0])

    def test_L3_cannot_send(self):
        self.assertFalse(self.consume(
            policy=replace(good_policy(), requested=AutonomyLevel.L3))[0])

    def test_fill_requires_explicit_approval(self):
        self.assertFalse(self.consume(
            current=replace(good_snapshot(), user_approved=False), action="fill")[0])

    def test_send_requires_countdown(self):
        self.assertFalse(self.consume(current=replace(good_snapshot(), countdown_completed=False))[0])

    def test_non_allowlisted_recipient(self):
        p = replace(good_policy(), recipient_allowlist=frozenset({"fixture:other"}))
        self.assertFalse(self.consume(policy=p)[0])

    def test_policy_binding(self):
        self.assertFalse(self.consume(policy=replace(good_policy(), revision="new-policy"))[0])

    def test_idle_absent(self):
        self.assertFalse(self.consume(current=replace(good_snapshot(), user_idle_seconds=61))[0])

    def test_expired_at_boundary(self):
        self.assertFalse(self.consume(now=110)[0])

    def test_clock_reversal(self):
        self.assertFalse(self.consume(now=99)[0])

    def test_clock_nan(self):
        self.assertFalse(self.consume(now=float("nan"))[0])

    def test_invalid_action(self):
        self.assertFalse(self.consume(action="inject_anyway")[0])

    def test_invalid_ttl(self):
        with self.assertRaises(ValueError):
            SendPermit(good_snapshot(), ttl_seconds=11)

    def test_permit_cannot_be_created_from_partial_draft(self):
        with self.assertRaises(ValueError):
            SendPermit(replace(good_snapshot(), draft_complete=False))

    def test_permit_cannot_be_created_without_guard(self):
        with self.assertRaises(ValueError):
            SendPermit(replace(good_snapshot(), guard_passed=False))

    def test_invalid_snapshot_truthy_boolean(self):
        with self.assertRaises(ValueError):
            replace(good_snapshot(), guard_passed="true")

    def test_invalid_snapshot_nan_idle(self):
        with self.assertRaises(ValueError):
            replace(good_snapshot(), user_idle_seconds=float("nan"))

    def test_consumed_once(self):
        permit = SendPermit(good_snapshot(), created_at=100)
        kwargs = dict(action="send", current=good_snapshot(),
                      policy=good_policy(), qualification=good_qualification(), now=101)
        self.assertTrue(permit.consume(**kwargs)[0])
        self.assertFalse(permit.consume(**kwargs)[0])

    def test_failed_recheck_burns_permit(self):
        permit = SendPermit(good_snapshot(), created_at=100)
        kwargs = dict(action="send", policy=good_policy(),
                      qualification=good_qualification(), now=101)
        self.assertFalse(permit.consume(
            current=replace(good_snapshot(), input_empty=False), **kwargs)[0])
        self.assertFalse(permit.consume(current=good_snapshot(), **kwargs)[0])

    def test_concurrent_consumers_only_one(self):
        permit = SendPermit(good_snapshot(), created_at=100)
        barrier = threading.Barrier(8)
        results = []

        def consume():
            barrier.wait()
            result = permit.consume(
                action="send",
                current=good_snapshot(),
                policy=good_policy(),
                qualification=good_qualification(),
                now=101,
            )
            results.append(result[0])

        threads = [threading.Thread(target=consume) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(results), 1)


def make_identity_test(field):
    def test(self):
        value = getattr(good_snapshot(), field)
        change = value + 1 if isinstance(value, int) else (
            draft_digest("đã sửa draft") if field == "draft_hash" else value + "-changed")
        self.assertFalse(self.consume(current=replace(good_snapshot(), **{field: change}))[0])
    return test


for field in IDENTITY_FIELDS:
    setattr(PermitTests, f"test_changed_{field}_invalidates", make_identity_test(field))


def make_required_test(field, value):
    def test(self):
        self.assertFalse(self.consume(current=replace(good_snapshot(), **{field: value}))[0])
    return test


for field, value in [
    ("input_empty", False),
    ("target_foreground", False),
    ("source_valid", False),
    ("speaker_known", False),
    ("presence_known", False),
    ("draft_complete", False),
    ("guard_passed", False),
    ("hard_block", True),
    ("soft_uncertain", True),
    ("turn_complete", False),
    ("budget_ok", False),
    ("rate_ok", False),
]:
    setattr(PermitTests, f"test_block_{field}", make_required_test(field, value))


class LowConfidenceTests(unittest.TestCase):
    def test_safe_setting_options(self):
        for setting in ("suggest_only", "skip", "ask_confirmation"):
            self.assertEqual(low_confidence_action(setting, hard_block=False), setting)

    def test_no_setting_bypasses_hard_block(self):
        for setting in ("suggest_only", "skip", "ask_confirmation", "retry_stronger"):
            self.assertEqual(low_confidence_action(
                setting, hard_block=True, stronger_ready=True, budget_ok=True), "blocked")

    def test_stronger_once(self):
        self.assertEqual(low_confidence_action(
            "retry_stronger", hard_block=False, stronger_ready=True, budget_ok=True),
            "retry_stronger")

    def test_stronger_no_budget(self):
        self.assertEqual(low_confidence_action(
            "retry_stronger", hard_block=False, stronger_ready=True), "ask_confirmation")

    def test_stronger_no_route(self):
        self.assertEqual(low_confidence_action(
            "retry_stronger", hard_block=False, budget_ok=True), "ask_confirmation")

    def test_stronger_retry_already_used(self):
        self.assertEqual(low_confidence_action(
            "retry_stronger", hard_block=False, stronger_ready=True,
            budget_ok=True, retries_used=1), "ask_confirmation")

    def test_unknown_setting_rejected(self):
        with self.assertRaises(ValueError):
            low_confidence_action("send_anyway", hard_block=False)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = AttemptLedger()
        self.digest = draft_digest("fixture reply")

    def begin(self, key="a", conv="fixture:42", now=100):
        return self.ledger.begin(key, conv, self.digest, now=now)

    def test_pending_before_delivery(self):
        self.assertTrue(self.begin()[0])
        self.assertEqual(self.ledger.state("a"), DeliveryState.PENDING)

    def test_pending_duplicate_blocked(self):
        self.begin()
        self.assertFalse(self.begin(key="b", now=101)[0])

    def test_unknown_delivery_blocks_retry(self):
        self.begin()
        self.ledger.mark_unknown("a")
        self.assertFalse(self.begin(key="b", now=101)[0])
        self.assertEqual(self.ledger.state("a"), DeliveryState.UNKNOWN)

    def test_same_attempt_never_retried_after_window(self):
        self.begin()
        self.ledger.mark_unknown("a")
        self.assertFalse(self.begin(now=10000)[0])

    def test_confirmed_duplicate_blocked(self):
        self.begin()
        self.ledger.confirm("a", "fixture-native-id")
        self.assertFalse(self.begin(key="b", now=101)[0])

    def test_other_conversation_not_duplicate(self):
        self.begin()
        self.assertTrue(self.begin(key="b", conv="fixture:other", now=101)[0])

    def test_new_attempt_after_duplicate_window(self):
        self.begin()
        self.ledger.confirm("a", "fixture-native-id")
        self.assertTrue(self.begin(key="b", now=701)[0])

    def test_late_verification_unknown_can_confirm(self):
        self.begin()
        self.ledger.mark_unknown("a")
        self.ledger.confirm("a", "fixture-native-id")
        self.assertEqual(self.ledger.state("a"), DeliveryState.CONFIRMED)

    def test_confirmation_requires_evidence_id(self):
        self.begin()
        with self.assertRaises(ValueError):
            self.ledger.confirm("a", "")

    def test_confirmed_cannot_become_unknown(self):
        self.begin()
        self.ledger.confirm("a", "fixture-native-id")
        with self.assertRaises(ValueError):
            self.ledger.mark_unknown("a")

    def test_rejected_before_action_allows_new_key(self):
        self.begin()
        self.ledger.reject_before_action("a")
        self.assertTrue(self.begin(key="b", now=101)[0])

    def test_rejected_before_action_cannot_confirm(self):
        self.begin()
        self.ledger.reject_before_action("a")
        with self.assertRaises(ValueError):
            self.ledger.confirm("a", "fixture-native-id")

    def test_concurrent_begin_only_one_reserves(self):
        barrier = threading.Barrier(8)
        results = []

        def begin(i):
            barrier.wait()
            results.append(self.begin(key=f"a-{i}")[0])

        threads = [threading.Thread(target=begin, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(results), 1)

    def test_duplicate_window_floor_enforced(self):
        with self.assertRaises(ValueError):
            AttemptLedger(duplicate_window_seconds=599)


class SpecConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(
            (ROOT / "reference" / "master-plan-v3" / "project.json").read_text(encoding="utf-8")
        )
        cls.example = json.loads(
            (ROOT / "reference" / "master-plan-v3" / "config.example.json").read_text(encoding="utf-8")
        )

    def test_hard_limits_match_spec(self):
        limits = self.spec["hard_limits"]
        self.assertEqual(MAX_PERMIT_TTL_SECONDS, limits["max_permit_ttl_seconds"])
        self.assertEqual(MIN_L2_REVIEWS_FOR_L3, limits["min_l2_reviews_for_l3"])
        self.assertEqual(MIN_ACCEPTANCE_RATE_FOR_L3, limits["min_acceptance_rate_for_l3"])
        self.assertEqual(MIN_SHADOW_TRIALS_FOR_L4, limits["min_shadow_trials_for_l4"])
        self.assertEqual(list(ON_LOW_CONFIDENCE), limits["on_low_confidence"])

    def test_ledger_window_matches_spec_duplicate_window(self):
        minutes = self.example["global_settings"]["rate_limits"]["duplicate_attempt_window_minutes"]
        self.assertEqual(DUPLICATE_ATTEMPT_WINDOW_SECONDS_MIN, minutes * 60)

    def test_rate_limiter_defaults_match_spec(self):
        rate = self.example["global_settings"]["rate_limits"]
        limiter = ConversationRateLimiter()
        self.assertEqual(limiter.max_per_10min, rate["max_sends_per_conversation_per_10min"])
        self.assertEqual(limiter.max_consecutive, rate["max_consecutive_agent_turns"])
        self.assertEqual(limiter.min_interval, float(rate["min_seconds_between_sends"]))


if __name__ == "__main__":
    unittest.main()
