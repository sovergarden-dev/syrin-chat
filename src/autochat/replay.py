from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from threading import RLock
from typing import Protocol

from .domain import AutonomyLevel, Decision, DraftCandidate, MessageEvent, RuntimePolicy, SpeakerState
from .guard import ConversationRateLimiter, check_inbound_hard_rules, check_outbound_draft
from .shadow import ShadowCollector, ShadowEvent


class SuggestionState(str, Enum):
    OFF = "off"
    READING = "reading"
    WAITING = "waiting"
    SUGGESTED = "suggested"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TranscriptContext:
    profile_id: str
    conversation_id: str
    source_epoch: str
    revision: int
    events: tuple[MessageEvent, ...]

    @property
    def latest_event(self) -> MessageEvent:
        return self.events[-1]


@dataclass(frozen=True)
class Draft:
    draft_id: str
    reply_text: str
    route_id: str
    model_registry_revision: str
    context_revision: int
    policy_revision: str


@dataclass(frozen=True)
class Suggestion:
    state: SuggestionState
    reason_code: str
    effective_level: AutonomyLevel
    context_revision: int
    draft: Draft | None = None


class DecisionGate(Protocol):
    def evaluate(self, context: TranscriptContext) -> Decision: ...


class DraftGenerator(Protocol):
    def generate(self, context: TranscriptContext, decision: Decision) -> DraftCandidate: ...


class ReplayCoordinator:
    def __init__(
        self,
        *,
        profile_id: str,
        policy: RuntimePolicy,
        decision_gate: DecisionGate,
        generator: DraftGenerator,
        reply_max_chars: int = 160,
        context_limit: int = 10,
        rate_limiter: ConversationRateLimiter | None = None,
        shadow_collector: ShadowCollector | None = None,
    ) -> None:
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ValueError("profile_id: nonempty_string_required")
        if not isinstance(policy, RuntimePolicy):
            raise ValueError("policy: runtime_policy_required")
        if not callable(getattr(decision_gate, "evaluate", None)):
            raise ValueError("decision_gate: evaluate_required")
        if not callable(getattr(generator, "generate", None)):
            raise ValueError("generator: generate_required")
        if type(reply_max_chars) is not int or not 1 <= reply_max_chars <= 4_000:
            raise ValueError("reply_max_chars: positive_integer_required")
        if type(context_limit) is not int or not 1 <= context_limit <= 100:
            raise ValueError("context_limit: positive_integer_required")
        self._profile_id = profile_id
        self._policy = policy
        self._decision_gate = decision_gate
        self._generator = generator
        self._reply_max_chars = reply_max_chars
        self._context_limit = context_limit
        self._rate_limiter = rate_limiter
        self._shadow_collector = shadow_collector
        self._events: list[MessageEvent] = []
        self._event_ids: set[str] = set()
        self._revision = 0
        self._cancel_generation = 0
        self._lock = RLock()

    def ingest(self, event: MessageEvent) -> Suggestion:
        if not isinstance(event, MessageEvent):
            raise ValueError("event: message_event_required")
        if event.profile_id != self._profile_id:
            raise ValueError("event: profile_mismatch")
        with self._lock:
            level = self._policy.effective_level
            if level is AutonomyLevel.L0:
                return self._result(SuggestionState.OFF, "policy_or_consent_blocks_read")
            if event.event_id in self._event_ids:
                return self._result(SuggestionState.WAITING, "duplicate_event")
            self._event_ids.add(event.event_id)
            self._events.append(event)
            self._revision += 1
            if level is AutonomyLevel.L1:
                return self._result(SuggestionState.READING, "p0_l1_read_only")
            if not event.source_complete:
                return self._result(SuggestionState.WAITING, "source_incomplete")
            if event.speaker_state is not SpeakerState.OTHER:
                if self._rate_limiter is not None and event.speaker_state is SpeakerState.SELF:
                    pass
                return self._result(SuggestionState.WAITING, "speaker_not_other")
            if self._rate_limiter is not None:
                self._rate_limiter.mark_other_message(event.conversation_id, event.observed_monotonic)
            inbound_violations = check_inbound_hard_rules(event.text_nfc)
            if inbound_violations:
                return self._result(SuggestionState.BLOCKED, "inbound_guard:" + ",".join(inbound_violations))
            if self._rate_limiter is not None:
                allowed, rate_reason = self._rate_limiter.try_acquire(event.conversation_id, event.observed_monotonic)
                if not allowed:
                    return self._result(SuggestionState.BLOCKED, f"rate_limit:{rate_reason}")
            context = self._context_for(event)
            cancellation_generation = self._cancel_generation

        try:
            decision = self._decision_gate.evaluate(context)
        except Exception:
            with self._lock:
                invalidation = self._invalidation_reason(
                    cancellation_generation, context.revision, "decision"
                )
                if invalidation is not None:
                    return self._result(SuggestionState.CANCELLED, invalidation)
                return self._result(SuggestionState.BLOCKED, "decision_error")
        with self._lock:
            invalidation = self._invalidation_reason(
                cancellation_generation, context.revision, "decision"
            )
            if invalidation is not None:
                return self._result(SuggestionState.CANCELLED, invalidation)
            if not isinstance(decision, Decision):
                return self._result(SuggestionState.BLOCKED, "decision_contract_invalid")
            if decision.risk_flags:
                return self._result(SuggestionState.BLOCKED, "hard_risk")
            if not decision.addressed_to_user or not decision.needs_reply:
                return self._result(SuggestionState.WAITING, "reply_not_required")
            if not decision.turn_complete:
                return self._result(SuggestionState.WAITING, "turn_incomplete")

        try:
            candidate = self._generator.generate(context, decision)
        except Exception:
            with self._lock:
                invalidation = self._invalidation_reason(
                    cancellation_generation, context.revision, "generation"
                )
                if invalidation is not None:
                    return self._result(SuggestionState.CANCELLED, invalidation)
                return self._result(SuggestionState.BLOCKED, "generation_error")
        with self._lock:
            invalidation = self._invalidation_reason(
                cancellation_generation, context.revision, "generation"
            )
            if invalidation is not None:
                return self._result(SuggestionState.CANCELLED, invalidation)
            if not isinstance(candidate, DraftCandidate):
                return self._result(SuggestionState.BLOCKED, "generation_contract_invalid")
            guard_error = self._guard(candidate)
            if guard_error is not None:
                return self._result(SuggestionState.BLOCKED, guard_error)
            draft = Draft(
                draft_id=self._draft_id(context, candidate),
                reply_text=candidate.reply_text,
                route_id=candidate.route_id,
                model_registry_revision=candidate.model_registry_revision,
                context_revision=context.revision,
                policy_revision=self._policy.policy_revision,
            )
            return Suggestion(
                state=SuggestionState.SUGGESTED,
                reason_code="review_required_l2",
                effective_level=self._policy.effective_level,
                context_revision=self._revision,
                draft=draft,
            )

    def cancel(self) -> Suggestion:
        with self._lock:
            self._cancel_generation += 1
            return self._result(SuggestionState.CANCELLED, "explicit_cancel")

    def _invalidation_reason(
        self, cancellation_generation: int, context_revision: int, phase: str
    ) -> str | None:
        if cancellation_generation != self._cancel_generation:
            return f"cancelled_during_{phase}"
        if context_revision != self._revision:
            return f"context_changed_during_{phase}"
        return None

    def _context_for(self, current: MessageEvent) -> TranscriptContext:
        relevant = tuple(
            event
            for event in self._events
            if event.conversation_id == current.conversation_id and event.source_epoch == current.source_epoch
        )[-self._context_limit :]
        return TranscriptContext(
            profile_id=self._profile_id,
            conversation_id=current.conversation_id,
            source_epoch=current.source_epoch,
            revision=self._revision,
            events=relevant,
        )

    def _result(self, state: SuggestionState, reason_code: str) -> Suggestion:
        return Suggestion(
            state=state,
            reason_code=reason_code,
            effective_level=self._policy.effective_level,
            context_revision=self._revision,
        )

    def _guard(self, candidate: DraftCandidate) -> str | None:
        text = candidate.reply_text
        if candidate.finish_status != "complete":
            return "generation_incomplete"
        violations = check_outbound_draft(text, max_chars=self._reply_max_chars)
        if violations:
            return "outbound_guard:" + ",".join(violations)
        return None

    def _draft_id(self, context: TranscriptContext, candidate: DraftCandidate) -> str:
        material = "\0".join(
            (
                self._profile_id,
                context.conversation_id,
                context.source_epoch,
                str(context.revision),
                self._policy.policy_revision,
                candidate.route_id,
                candidate.model_registry_revision,
                candidate.reply_text,
            )
        )
        return sha256(material.encode("utf-8")).hexdigest()
