from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from autochat.config import (
    ConfigError,
    ModelRegistry,
    RuntimeConfig,
    load_config,
    load_registry,
)


class ConfigModuleTests(unittest.TestCase):
    def test_safe_empty_config_is_valid_but_not_ready(self) -> None:
        cfg = load_config("fixture:no-file")
        self.assertIsInstance(cfg, RuntimeConfig)
        self.assertEqual(cfg.profiles, ())
        self.assertTrue(cfg.readiness_reasons)

    def test_unknown_root_field_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict({"version": "3.0", "unsafe_bypass": True})

    def test_schema_violation_is_rejected_by_loader(self) -> None:
        payload = {
            "version": "3.0",
            "profiles": [],
            "perception": {"pixel_click_target": [10, 20]},
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


def _record(**overrides):
    record = {
        "provider_id": "gemini",
        "model_id": "gemini-flash-2-5",
        "verification_status": "verified",
        "verified_at": "2026-10-14",
        "evidence_ref": "fixture:not-live",
        "retired": False,
        "tasks": ["generation"],
    }
    record.update(overrides)
    return record


def _registry(*records):
    return ModelRegistry.from_dict({"version": "1.0", "models": list(records)})


def _route_payload(model_id="gemini-flash-2-5"):
    return {
        "version": "3.0",
        "providers": {"gemini": {"kind": "gemini_official", "enabled": True}},
        "generation": {
            "routes": {
                "fast": {"enabled": True, "provider_id": "gemini", "model_id": model_id}
            }
        },
        "profiles": [],
    }


class RegistryGateTests(unittest.TestCase):
    def test_enabled_route_with_unverified_model_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict(_route_payload(), registry=load_registry())

    def test_verified_route_passes(self) -> None:
        cfg = RuntimeConfig.from_dict(_route_payload(), registry=_registry(_record()))
        self.assertEqual(cfg.profiles, ())

    def test_retired_model_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict(
                _route_payload(), registry=_registry(_record(retired=True))
            )

    def test_verified_model_without_evidence_is_rejected(self) -> None:
        record = _record()
        del record["evidence_ref"]
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict(_route_payload(), registry=_registry(record))

    def test_latest_alias_rejected_even_when_registry_verified(self) -> None:
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict(
                _route_payload("gemini-flash-latest"),
                registry=_registry(_record(model_id="gemini-flash-latest")),
            )

    def test_enabled_route_with_disabled_provider_is_rejected(self) -> None:
        payload = _route_payload()
        payload["providers"]["gemini"]["enabled"] = False
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict(payload, registry=_registry(_record()))

    def test_disabled_routes_need_no_registry(self) -> None:
        payload = _route_payload()
        payload["generation"]["routes"]["fast"]["enabled"] = False
        cfg = RuntimeConfig.from_dict(payload, registry=None)
        self.assertEqual(cfg.profiles, ())

    def test_enabled_decision_with_unverified_model_is_rejected(self) -> None:
        payload = _route_payload()
        payload["decision"] = {
            "enabled": True,
            "provider_id": "gemini",
            "model_id": "jev-reflex-2",
        }
        with self.assertRaises(ConfigError):
            RuntimeConfig.from_dict(payload, registry=_registry(_record()))

    def test_verified_decision_route_passes(self) -> None:
        payload = _route_payload()
        payload["decision"] = {
            "enabled": True,
            "provider_id": "gemini",
            "model_id": "jev-reflex-2",
        }
        cfg = RuntimeConfig.from_dict(
            payload,
            registry=_registry(_record(), _record(model_id="jev-reflex-2", tasks=["decision"])),
        )
        self.assertEqual(cfg.profiles, ())

    def test_load_registry_missing_file_is_empty(self) -> None:
        self.assertEqual(load_registry("fixture-no-registry.json").records, ())

    def test_real_example_config_loads_and_is_not_ready(self) -> None:
        cfg = load_config(Path(__file__).parent / "fixtures" / "config.example.json")
        self.assertEqual(cfg.profiles, ())
        self.assertEqual(len(cfg.readiness_reasons), 3)
