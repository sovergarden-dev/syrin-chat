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

## Implemented P1, P2 & P3 Universal Overlay, Perception, Engine & Live Execution components

- `autochat.ui.geometry`: High-performance coordinate space mapping, `Rect` math with clamping, normalized sub-window offsets, and multi-monitor DPI scaling.
- `autochat.ui.win32`: Native bridge implementing `WS_EX_NOACTIVATE` (zero-focus stealing), `WDA_EXCLUDEFROMCAPTURE` (screen-capture invisible overlay to eliminate self-capture loops), and window rectangle queries.
- `autochat.ui.actuator`: `StagedInputActuator` supporting staged message buffers, in-flight manual editing, countdown autopilot (3s countdown with cancel), and automated focus-then-dispatch triggers.
- `autochat.ui.overlay`: Headless-friendly `OverlayState` with slot presets (`save_preset`, `apply_preset`), coordinate lock/unlock, and lazy PySide6 `FloatingAssistantOverlay` interface.
- `autochat.ui.win32_input`: `Win32InputDispatcher` supporting dual input modes:
  - `InputMode.CLIPBOARD`: High-speed paste (`Ctrl+V`) with non-destructive clipboard state preservation and automatic restoration.
  - `InputMode.HUMAN_KEYPRESS`: Direct unicode keystroke dispatch (`KEYEVENTF_UNICODE`) with simulated human jitter (configurable inter-key delay) for anti-cheat and direct-input resilience.
- `autochat.ui.hotkey`: `GlobalHotkeyBridge` registering system-wide Win32 hotkeys (`RegisterHotKey` / `UnregisterHotKey`) for immediate single-key send (F8), instant cancellation (Esc), and emergency panic stop.
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
  - `OllamaProvider`: Local Ollama HTTP adapter (localhost:11434).
  - `SyrinPoolProvider`: Local Syrin Pool / Antigravity HTTP adapter (localhost:9100).
- `autochat.loop.live`: `LiveAgentLoop` end-to-end execution pipeline coordinating Capture -> Settler -> OCR -> Parser -> Two-Tier Engine -> Outbound Guard -> Staged Actuator.

## Deliberately excluded out-of-scope boundaries

- Closed-loop autonomous spamming without human-in-the-loop countdown or cancel override.
- Undisclosed automated game tampering or anti-cheat circumvention; all actions use humanized delays or explicit user staging.
- Plaintext credential storage or external telemetry storing raw conversation transcripts.

## Why this boundary is deliberate

The V3 plan requires a selected application, source-specific evidence, permissions, calibration, and platform-policy review before a real integration. P0 therefore proves protocol and failure behavior without collecting real chat data or modifying an external application.
