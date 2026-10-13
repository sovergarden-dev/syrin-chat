# V3 Baseline Provenance

## Source artifact

- File: `C:\Users\rurus\Downloads\Auto-Chat-Agent-Master-Plan-V3.zip`
- Archive SHA-256: `025e36e421d527559d77542bf0e1df1e3498ea2f39e42d09299100f7debb2aba`
- Package identity: `SPEC-AUTO-CHAT-V3`, version `3.0`, dated `2026-10-13`.
- Imported tree: [`reference/master-plan-v3/`](../reference/master-plan-v3/)

## Integrity check

The package manifest lists 33 payload files plus `MANIFEST.json`. Every listed file was verified against its declared byte size and SHA-256.

```text
manifest_entries=33
mismatches=[]
unlisted_files=[]
```

The imported tree contains exactly those 34 files. The baseline remains reference material until corresponding runtime functionality is implemented and independently exercised.

## Independent offline verification

The package's offline configuration/policy suite was rerun in an isolated virtual environment.

```text
Interpreter: CPython 3.14.7
Dependencies: jsonschema==4.25.1, tzdata==2025.2
Command: python -m unittest discover -s tests -v
Result: Ran 186 tests in 6.969s — OK
```

`validate_config.py config.example.json` passed structural and semantic checks. `--readiness` intentionally exited with code `2`: no real profile, verified generation route, or verified decision route is configured.

These checks validate only the frozen offline reference code. They do not establish OCR quality, provider access, Windows integration, platform permission, actuator safety, or any G1–G9 acceptance gate.
