# P0 Replay Core

P0 is a local, deterministic foundation. It accepts replay fixtures, preserves event identity, suppresses duplicate event IDs without collapsing real repeated messages, enforces L0–L2 only, and produces a reviewable draft only through injected decision and generation adapters.

## Boundaries

- No capture backend, OCR engine, provider SDK, credential store, clipboard, input action, or auto-send implementation exists here.
- `ReplayCoordinator` never calls the OS or network. It has no send/fill API.
- An event is retained only after local profile consent allows reading.
- A pending decision/generation is invalidated if cancellation or any newer event changes the context.
- Exceptions from adapter implementations are converted into content-free blocked states.

## Fixture protocol

Replay input is UTF-8 JSONL. Each line must contain exactly one `MessageEvent` object:

```json
{
  "event_id": "event-001",
  "profile_id": "fixture-profile",
  "conversation_id": "conversation-001",
  "source_epoch": "source-epoch-001",
  "occurrence_id": "occurrence-001",
  "speaker_state": "other",
  "text_nfc": "Tin nhắn NFC đã chuẩn hóa.",
  "observed_monotonic": 100.0,
  "source_complete": true
}
```

The loader rejects duplicate JSON keys, unknown fields, malformed types, non-NFC text, and invalid speaker states. It does not echo fixture content in its errors.

## Metadata-only audit

The bundled command deliberately has no model route. It reads a fixture and emits only state/reason counts.

```bash
PYTHONPATH=src python -m autochat.cli --input path/to/replay.jsonl
```

The command never prints event text, replies, credentials, or provider diagnostics.

## Next boundary

P1 starts only after a concrete application is chosen and its read permission, source capability, identity binding, privacy implications, and support record are reviewed. P0 does not authorize an adapter or any action path.
