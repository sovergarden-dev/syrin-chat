# Implementation Status

## Implemented P0 components

- Immutable `MessageEvent`, decision, draft-candidate, and runtime-policy protocol.
- Local replay coordinator capped at L2 even when a caller requests L3/L4.
- Consent-first L0 behavior that retains no event and invokes no adapter.
- Event-ID deduplication without collapsing two real same-text occurrences.
- Speaker/source completeness guards before decision or generation.
- Cancellation and newer-context invalidation outside the adapter execution lock.
- Content-free failure and risk reasons.
- Strict JSONL replay parser and metadata-only CLI audit.
- Isolated package build, lockfile, Windows CI workflow, and preserved V3 reference suite.

## Explicitly not implemented

- Windows capture, UI Automation, notifications, OCR, overlay UI, region selector, hotkey, clipboard, input mutation, fill, send, ledger persistence, or delivery verification.
- Any TypeSafe/Jev, Gemini, custom, or local provider adapter.
- Credential storage, cloud consent UI, budget enforcement, transcript persistence, or persona learning.
- Any actual app/game profile, support claim, autonomy qualification, or G1–G9 pass claim.

## Why this boundary is deliberate

The V3 plan requires a selected application, source-specific evidence, permissions, calibration, and platform-policy review before a real integration. P0 therefore proves protocol and failure behavior without collecting real chat data or modifying an external application.
