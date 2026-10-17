# Implementation Status

## Implemented P0 components

- Immutable `MessageEvent`, decision, draft-candidate, and runtime-policy protocol.
- Local replay coordinator capped at L2 even when a caller requests L3/L4.
- Consent-first L0 behavior that retains no event and invokes no adapter.
- Event-ID deduplication without collapsing two real same-text occurrences.
- Speaker/source completeness guards before decision or generation.
- Cancellation and newer-context invalidation outside the adapter execution lock.
- Inbound and outbound guards: Vietnamese CCCD/phone/card/OTP/email redaction and hard rules.
- Thread-safe conversation rate limiter matching V3 hard limits.
- Action-phase policy enforcement: `effective_level`, single-use `SendPermit`, and `AttemptLedger`.
- Runtime configuration loader with model registry verification and schema enforcement.
- Metadata-only shadow telemetry collector (`ShadowCollector`) for measuring G4/G5/G6 criteria.
- Content-free failure and risk reasons.
- Strict JSONL replay parser and metadata-only CLI audit.
- Isolated package build, lockfile, Windows CI workflow, and preserved V3 reference suite.

## Implemented P1 & P2 Universal Overlay, Perception & Engine components

- `autochat.ui.geometry`: High-performance coordinate space mapping, `Rect` math with clamping, normalized sub-window offsets, and multi-monitor DPI scaling.
- `autochat.ui.win32`: Native bridge implementing `WS_EX_NOACTIVATE` (zero-focus stealing), `WDA_EXCLUDEFROMCAPTURE` (screen-capture invisible overlay to eliminate self-capture loops), and window rectangle queries.
- `autochat.ui.actuator`: `StagedInputActuator` supporting staged message buffers, in-flight manual editing, countdown autopilot (3s countdown with cancel), and automated focus-then-dispatch triggers.
- `autochat.ui.overlay`: Headless-friendly `OverlayState` with slot presets (`save_preset`, `apply_preset`), coordinate lock/unlock, and lazy PySide6 `FloatingAssistantOverlay` interface.
- `autochat.ui.win32_input`: `Win32InputDispatcher` supporting dual input modes:
  - `InputMode.CLIPBOARD`: High-speed paste (`Ctrl+V`) with non-destructive clipboard state preservation and automatic restoration.
  - `InputMode.HUMAN_KEYPRESS`: Direct unicode keystroke dispatch (`KEYEVENTF_UNICODE`) with simulated human jitter (configurable inter-key delay) for anti-cheat and direct-input resilience.
- `autochat.perception.frame`: High-speed zero-dependency `Frame` representation with fast sub-region cropping (`crop(rect: Rect)`).
- `autochat.perception.detector`: `DirtyFrameDetector` comparing consecutive frames on byte level with adaptive delta and change thresholds, avoiding unnecessary OCR calls on static frames or moving backgrounds.
- `autochat.perception.settling`: `FrameSettler` providing a quiet-window filter (150-250ms) to ensure text rendering and animations settle completely before invoking OCR, with hard max-wait safeguards.
- `autochat.perception.capture`: `ScreenRegionCapture` protocol with `MockCaptureBackend` and zero-dependency `GdiCaptureBackend` utilizing Windows `BitBlt` and `GetDIBits` with guaranteed GDI handle cleanup.
- `autochat.perception.ocr`: `OcrBackend` protocol with `MockOcrBackend` and `WinRtOcrBackend` for offline zero-latency Windows native OCR.
- `autochat.perception.parser`: `TranscriptParser` providing regex-driven speaker attribution, self-message detection (`my_username`), and deduplication against sliding historical buffers.
- `autochat.engine`: Two-Tier Reflex & Reasoning architecture:
  - `ReflexTier`: High-speed regex / canned response evaluator (< 5ms response time) for instant game reactions.
  - `DeepReasoningTier`: Prompt-based deliberate reasoning layer interfacing with local (Ollama/Syrin Pool) or cloud LLMs.
  - `TwoTierEngine`: Unified coordinator prioritizing reflex shortcuts before delegating complex requests to LLMs.

## Explicitly not implemented

- Windows capture, UI Automation, notifications, OCR, overlay UI, region selector, hotkey, clipboard, input mutation, fill, send, ledger persistence, or delivery verification.
- Any TypeSafe/Jev, Gemini, custom, or local provider adapter.
- Credential storage, cloud consent UI, budget enforcement, transcript persistence, or persona learning.
- Any actual app/game profile, support claim, autonomy qualification, or G1–G9 pass claim.

## Why this boundary is deliberate

The V3 plan requires a selected application, source-specific evidence, permissions, calibration, and platform-policy review before a real integration. P0 therefore proves protocol and failure behavior without collecting real chat data or modifying an external application.
