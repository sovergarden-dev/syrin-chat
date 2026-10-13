from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .domain import MessageEvent, SpeakerState
from .replay import ReplayCoordinator, Suggestion, SuggestionState


class ReplayInputError(ValueError):
    pass


_EVENT_FIELDS = frozenset(
    {
        "event_id",
        "profile_id",
        "conversation_id",
        "source_epoch",
        "occurrence_id",
        "speaker_state",
        "text_nfc",
        "observed_monotonic",
        "source_complete",
    }
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReplayInputError("duplicate_key")
        value[key] = item
    return value


def load_events(lines: Iterable[str]) -> tuple[MessageEvent, ...]:
    events: list[MessageEvent] = []
    for line_number, raw_line in enumerate(lines, start=1):
        if not isinstance(raw_line, str):
            raise ReplayInputError(f"line {line_number}: invalid_json_object")
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, ReplayInputError, TypeError, ValueError):
            raise ReplayInputError(f"line {line_number}: invalid_json_object") from None
        if not isinstance(record, dict) or frozenset(record) != _EVENT_FIELDS:
            raise ReplayInputError(f"line {line_number}: schema_violation")
        try:
            events.append(
                MessageEvent(
                    event_id=record["event_id"],
                    profile_id=record["profile_id"],
                    conversation_id=record["conversation_id"],
                    source_epoch=record["source_epoch"],
                    occurrence_id=record["occurrence_id"],
                    speaker_state=SpeakerState(record["speaker_state"]),
                    text_nfc=record["text_nfc"],
                    observed_monotonic=record["observed_monotonic"],
                    source_complete=record["source_complete"],
                )
            )
        except (KeyError, TypeError, ValueError):
            raise ReplayInputError(f"line {line_number}: schema_violation") from None
    return tuple(events)


@dataclass(frozen=True)
class ReplayReport:
    events_seen: int
    off: int
    reading: int
    waiting: int
    suggested: int
    blocked: int
    cancelled: int
    reason_counts: tuple[tuple[str, int], ...]


def run_replay(events: Iterable[MessageEvent], coordinator: ReplayCoordinator) -> ReplayReport:
    if not isinstance(coordinator, ReplayCoordinator):
        raise ValueError("coordinator: replay_coordinator_required")
    state_counts: Counter[SuggestionState] = Counter()
    reason_counts: Counter[str] = Counter()
    events_seen = 0
    for event in events:
        result = coordinator.ingest(event)
        if not isinstance(result, Suggestion):
            raise ValueError("coordinator: suggestion_result_required")
        events_seen += 1
        state_counts[result.state] += 1
        reason_counts[result.reason_code] += 1
    return ReplayReport(
        events_seen=events_seen,
        off=state_counts[SuggestionState.OFF],
        reading=state_counts[SuggestionState.READING],
        waiting=state_counts[SuggestionState.WAITING],
        suggested=state_counts[SuggestionState.SUGGESTED],
        blocked=state_counts[SuggestionState.BLOCKED],
        cancelled=state_counts[SuggestionState.CANCELLED],
        reason_counts=tuple(sorted(reason_counts.items())),
    )
