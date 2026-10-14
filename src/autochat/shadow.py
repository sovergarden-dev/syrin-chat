from __future__ import annotations

import math
from dataclasses import dataclass
from threading import RLock
from typing import List, Optional


@dataclass(frozen=True)
class ShadowEvent:
    trial_id: str
    conversation_id: str
    decision_latency_ms: float
    generation_latency_ms: float
    decision_needs_reply: bool
    decision_confidence: float
    misfire: bool
    rejected_by_guard: bool
    user_accepted_without_edit: bool

    def __post_init__(self) -> None:
        if not isinstance(self.trial_id, str) or not self.trial_id.strip():
            raise ValueError("trial_id: nonempty_string_required")
        if not isinstance(self.conversation_id, str) or not self.conversation_id.strip():
            raise ValueError("conversation_id: nonempty_string_required")
        for num_field in ("decision_latency_ms", "generation_latency_ms", "decision_confidence"):
            val = getattr(self, num_field)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val < 0:
                raise ValueError(f"{num_field}: non_negative_finite_number_required")
        for bool_field in ("decision_needs_reply", "misfire", "rejected_by_guard", "user_accepted_without_edit"):
            val = getattr(self, bool_field)
            if type(val) is not bool:
                raise ValueError(f"{bool_field}: boolean_required")


@dataclass(frozen=True)
class ShadowMetricsSummary:
    total_trials: int
    misfires: int
    misfire_rate: float
    accepted_without_edit: int
    acceptance_rate: float
    rejected_by_guard: int
    p95_decision_latency_ms: float
    p95_generation_latency_ms: float


class ShadowCollector:
    def __init__(self) -> None:
        self._events: List[ShadowEvent] = []
        self._lock = RLock()

    def record(self, event: ShadowEvent) -> None:
        if not isinstance(event, ShadowEvent):
            raise ValueError("event: ShadowEvent_required")
        with self._lock:
            self._events.append(event)

    def summarize(self) -> ShadowMetricsSummary:
        with self._lock:
            total = len(self._events)
            if total == 0:
                return ShadowMetricsSummary(
                    total_trials=0,
                    misfires=0,
                    misfire_rate=0.0,
                    accepted_without_edit=0,
                    acceptance_rate=0.0,
                    rejected_by_guard=0,
                    p95_decision_latency_ms=0.0,
                    p95_generation_latency_ms=0.0,
                )
            misfires = sum(1 for e in self._events if e.misfire)
            accepted = sum(1 for e in self._events if e.user_accepted_without_edit)
            guard_rejected = sum(1 for e in self._events if e.rejected_by_guard)

            dec_lats = sorted(e.decision_latency_ms for e in self._events)
            gen_lats = sorted(e.generation_latency_ms for e in self._events)

            p95_idx = max(0, math.ceil(0.95 * total) - 1)
            p95_dec = dec_lats[p95_idx]
            p95_gen = gen_lats[p95_idx]

            return ShadowMetricsSummary(
                total_trials=total,
                misfires=misfires,
                misfire_rate=misfires / total,
                accepted_without_edit=accepted,
                acceptance_rate=accepted / total,
                rejected_by_guard=guard_rejected,
                p95_decision_latency_ms=p95_dec,
                p95_generation_latency_ms=p95_gen,
            )
