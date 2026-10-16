# Auto-Chat Agent

Consent-first desktop AI chat copilot for Windows. It turns approved, structured or replayed conversation data into reviewed reply suggestions. It does not claim universal application support.

## Status

**P0 foundation in progress.** The repository begins from the independently verified V3 master plan. No live capture, OCR, cloud provider, clipboard, input injection, or auto-send path is enabled in this baseline.

## Non-negotiable boundaries

- New profiles start at L0. P0 supports only replayed data and L2-style suggestions.
- No anti-cheat evasion, hardware emulation, timing jitter, self-bot workaround, or “zero-ban” claim.
- No conversation content in operational logs. No API keys in JSON, source control, or test fixtures.
- Unknown speaker, source, target, policy, confidence, or delivery state blocks action.
- L3/L4 require profile-specific evidence gates. They are not part of the initial implementation.

## V3 specification baseline

The reviewed V3 package is preserved verbatim under [`reference/master-plan-v3/`](reference/master-plan-v3/). Its archive provenance and independent verification record are in [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

Start with these documents:

1. [`AUTO_CHAT_AGENT_MASTER_PLAN.md`](reference/master-plan-v3/AUTO_CHAT_AGENT_MASTER_PLAN.md)
2. [`SETTINGS_SPEC.md`](reference/master-plan-v3/SETTINGS_SPEC.md)
3. [`AUDIT_CHECKLIST.md`](reference/master-plan-v3/AUDIT_CHECKLIST.md)
4. [`DECISIONS_AND_ASSUMPTIONS.md`](reference/master-plan-v3/DECISIONS_AND_ASSUMPTIONS.md)

Implementation records:

- [`P0_REPLAY_CORE.md`](docs/P0_REPLAY_CORE.md)
- [`IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md)
- [`P1_PROFILE_SELECTION.md`](docs/P1_PROFILE_SELECTION.md)

## Delivery path

| Phase | Scope | State |
| --- | --- | --- |
| P0 | Replay fixtures, domain protocol, transcript safeguards, deterministic L2 suggestions, cancellation and policy tests, guard, config/registry gates, shadow metrics | Complete |
| P1 | Universal Floating Overlay & Staged Input Copilot (ROI selection, Win32 zero-focus-steal, WDA_EXCLUDEFROMCAPTURE, 1-trigger dispatch, countdown autopilot) | In progress |
| P2 | OCR/transcript quality on live screen regions, dirty detection & glyph caching | Not started |
| P3 | L3/L4 only after all applicable evidence gates | Not started |
| P4 | 14-day personal-use acceptance | Not started |
| P5 | Public-release decision, legal/security/support readiness | Explicitly deferred |

## Repository policy

This codebase follows the V3 `Human-in-control`, `Fail-closed`, `Zero-Evasion`, `Local-first`, and `Measure-first` decisions. Runtime implementation must remain app-agnostic until a real profile is selected and reviewed.
