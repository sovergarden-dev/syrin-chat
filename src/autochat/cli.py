from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .domain import AutonomyLevel, Decision, DraftCandidate, RuntimePolicy
from .protocol import ReplayInputError, load_events, run_replay
from .replay import ReplayCoordinator


class _NoModelDecisionGate:
    def evaluate(self, context) -> Decision:
        return Decision(
            addressed_to_user=False,
            needs_reply=False,
            turn_complete=True,
            risk_flags=frozenset(),
            rationale_code="p0_model_unconfigured",
        )


class _UnreachableGenerator:
    def generate(self, context, decision) -> DraftCandidate:
        raise RuntimeError("generator_must_not_run_without_a_verified_route")


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a local, metadata-only Auto-Chat Agent P0 replay audit."
    )
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSONL MessageEvent fixture")
    args = parser.parse_args(argv)
    try:
        with args.input.open("r", encoding="utf-8") as stream:
            events = load_events(stream)
    except (OSError, ReplayInputError):
        _emit({"error": "invalid_replay_input"})
        return 2
    if not events:
        _emit({"error": "empty_replay"})
        return 2
    profile_ids = {event.profile_id for event in events}
    if len(profile_ids) != 1:
        _emit({"error": "mixed_profile_ids"})
        return 2
    coordinator = ReplayCoordinator(
        profile_id=events[0].profile_id,
        policy=RuntimePolicy(
            profile_enabled=True,
            read_consent=True,
            source_access_allowed=True,
            requested_level=AutonomyLevel.L2,
            policy_revision="p0-cli-policy-v1",
        ),
        decision_gate=_NoModelDecisionGate(),
        generator=_UnreachableGenerator(),
    )
    report = run_replay(events, coordinator)
    _emit(asdict(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
