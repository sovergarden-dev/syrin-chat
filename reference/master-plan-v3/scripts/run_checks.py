#!/usr/bin/env python3
"""Sinh báo cáo kiểm thử OFFLINE. Chạy từ đâu cũng được, không gọi dịch vụ ngoài."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_config import load_json, validate, readiness


def main() -> int:
    os.chdir(ROOT)
    out = ROOT / "qa"
    out.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with (out / "test_results.txt").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    summary = {
        "scope": "Offline configuration/policy reference only; no live OCR/API/Windows actions tested",
        "tests_run": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "example_config_errors": validate(load_json(ROOT / "config.example.json")),
        "example_readiness_pending": readiness(load_json(ROOT / "config.example.json")),
        "real_world_gates_status": "G1–G9 pending",
        "errata_mapped": len(load_json(ROOT / "reference/traceability.json")["records"]),
    }
    (out / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() and not summary["example_config_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())