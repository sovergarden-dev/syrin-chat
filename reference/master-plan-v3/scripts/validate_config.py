#!/usr/bin/env python3
"""Kiểm cấu trúc và semantic guardrails; không chứng minh app Windows đã an toàn."""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda s: (_ for _ in ()).throw(
                          ValueError(f"Invalid JSON constant: {s}")))


def endpoint_error(provider: dict) -> str | None:
    url = provider["base_url"]
    kind = provider["kind"]
    if url is None:
        return ("endpoint_required" if provider["enabled"]
                and kind in {"openai_compatible", "ollama_local"} else None)
    try:
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return "endpoint_host_or_embedded_credential"
        if parsed.query or parsed.fragment:
            return "endpoint_query_or_fragment_forbidden"
        _ = parsed.port
        host = parsed.hostname.lower().rstrip(".")
        address = None
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass
        if kind == "ollama_local":
            loopback = host == "localhost" or (address is not None and address.is_loopback)
            if parsed.scheme not in {"http", "https"} or not loopback:
                return "local_endpoint_must_be_loopback"
        else:
            if parsed.scheme != "https":
                return "cloud_endpoint_requires_https"
            if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
                return "cloud_endpoint_private_host"
            if address is not None and not address.is_global:
                return "cloud_endpoint_private_address"
            if host.endswith((".local", ".internal")):
                return "cloud_endpoint_private_host"
    except (ValueError, TypeError):
        return "endpoint_invalid"
    return None


def model_errors(config: dict, registry: dict, errors: list[str]) -> None:
    if not isinstance(registry, dict):
        errors.append("registry: must_be_object")
        return
    records = registry.get("models", [])
    if not isinstance(records, list):
        errors.append("registry/models: must_be_array")
        return
    known = {}
    for item in records:
        if not isinstance(item, dict):
            errors.append("registry/models: invalid_record")
            continue
        key = (item.get("provider_id"), item.get("model_id"))
        if not all(isinstance(x, str) and x for x in key):
            errors.append("registry/models: provider_and_model_required")
            continue
        if key in known:
            errors.append(f"registry/{key}: duplicate_model")
        tasks = item.get("tasks", [])
        caps = item.get("capabilities", {})
        if (not isinstance(tasks, list)
                or any(not isinstance(x, str) or x not in {"decision", "generation"}
                       for x in tasks)
                or not isinstance(caps, dict)):
            errors.append(f"registry/{key}: invalid_tasks_or_capabilities")
            continue
        known[key] = item
    active = []
    decision = config["decision"]
    if decision["enabled"]:
        active.append(("decision", decision, "decision"))
    for key, value in config["generation"]["routes"].items():
        if value["enabled"]:
            active.append((f"generation/routes/{key}", value, "generation"))
    for path, route, task in active:
        model_id = route["model_id"]
        provider = config["providers"].get(route["provider_id"])
        if provider is None or not provider["enabled"]:
            errors.append(f"{path}: enabled_provider_required")
        if (not model_id or model_id.lower() in {"tbd", "change_me"}
                or re.search(r"(?:^|[-_])(?:latest|preview)$", model_id.lower())):
            errors.append(f"{path}: verified_pinned_model_required")
            continue
        record = known.get((route["provider_id"], model_id))
        if not record or record.get("verification_status") != "verified":
            errors.append(f"{path}: model_not_verified_in_registry")
            continue
        if record.get("retired", False):
            errors.append(f"{path}: retired_model")
        if task not in record.get("tasks", []):
            errors.append(f"{path}: task_not_supported")
        if (not isinstance(record.get("evidence_ref"), str)
                or not record.get("evidence_ref")
                or not isinstance(record.get("verified_at"), str)
                or not FormatChecker().conforms(record.get("verified_at"), "date")):
            errors.append(f"{path}: verification_evidence_required")
        if task == "generation":
            caps = record.get("capabilities", {})
            if caps.get("structured_output") is not True:
                errors.append(f"{path}: structured_output_not_verified")
            thinking = caps.get("thinking_levels", [None])
            if (not isinstance(thinking, list)
                    or route["thinking_level"] not in thinking):
                errors.append(f"{path}: unsupported_thinking_level")
            limit = caps.get("max_output_tokens")
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < route["max_output_tokens"]:
                errors.append(f"{path}: output_limit_not_verified_or_exceeded")
            if config["generation"]["streaming_preview"] and caps.get("streaming") is not True:
                errors.append(f"{path}: streaming_not_verified")


def validate(config: dict, registry: dict | None = None) -> list[str]:
    schema = load_json(ROOT / "profiles.schema.json")
    Draft202012Validator.check_schema(schema)
    structural = list(Draft202012Validator(
        schema, format_checker=FormatChecker()).iter_errors(config))
    structural.sort(key=lambda e: "/".join(map(str, e.absolute_path)))
    if structural:
        # Không in instance/value: malformed credential có thể chứa secret.
        return [f"{'/'.join(map(str, e.absolute_path)) or '/'}: schema_{e.validator}"
                for e in structural]
    errors = []
    global_settings = config["global_settings"]
    keys = [global_settings[x] for x in
            ("kill_switch_hotkey", "cancel_hotkey", "send_now_hotkey")]
    normalized = []
    for key in keys:
        tokens = key.split("+")
        if len(set(tokens[:-1])) != len(tokens[:-1]):
            errors.append("global_settings/hotkeys: duplicate_modifier")
        normalized.append((frozenset(tokens[:-1]), tokens[-1]))
    if len(set(normalized)) != len(normalized):
        errors.append("global_settings/hotkeys: collision")
    quiet = global_settings["quiet_hours"]
    try:
        ZoneInfo(quiet["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        errors.append("global_settings/quiet_hours: timezone_invalid")
    if quiet["enabled"] and quiet["start"] == quiet["end"]:
        errors.append("global_settings/quiet_hours: ambiguous_24h_interval")
    budget = global_settings["budget"]
    if budget["daily_usd"] is not None and budget["monthly_usd"] is not None:
        if budget["daily_usd"] > budget["monthly_usd"]:
            errors.append("global_settings/budget: daily_exceeds_monthly")
    privacy = global_settings["privacy"]
    for provider_id in privacy["cloud_provider_allowlist"]:
        if provider_id not in config["providers"]:
            errors.append(f"privacy/cloud_provider_allowlist/{provider_id}: unknown_provider")
    for provider_id, provider in config["providers"].items():
        bad_endpoint = endpoint_error(provider)
        if bad_endpoint:
            errors.append(f"providers/{provider_id}: {bad_endpoint}")
        if not provider["enabled"]:
            continue
        if provider["kind"] != "ollama_local":
            if not provider["credential_ref"]:
                errors.append(f"providers/{provider_id}: credential_ref_required")
            if not privacy["cloud_text_consent"]:
                errors.append(f"providers/{provider_id}: cloud_consent_required")
            if provider_id not in privacy["cloud_provider_allowlist"]:
                errors.append(f"providers/{provider_id}: cloud_allowlist_required")
            if provider["data_policy_status"] != "no_training_reviewed":
                errors.append(f"providers/{provider_id}: data_policy_review_required")
            if budget["daily_usd"] is None or budget["monthly_usd"] is None:
                errors.append(f"providers/{provider_id}: daily_and_monthly_budget_required")
    timing = config["turn_taking"]
    if timing["min_wait_ms"] > timing["max_wait_ms"]:
        errors.append("turn_taking: min_wait_exceeds_max")
    decision = config["decision"]
    if decision["provider_id"] not in config["providers"]:
        errors.append("decision/provider_id: unknown_provider")
    if decision["on_low_confidence"] == "retry_stronger":
        route = config["generation"]["routes"].get(decision["stronger_route_id"])
        if not route or not route["enabled"] or decision["max_stronger_retries"] < 1:
            errors.append("decision: retry_stronger_requires_enabled_route_and_retry_budget")
    for route_id, route in config["generation"]["routes"].items():
        if route["provider_id"] not in config["providers"]:
            errors.append(f"generation/routes/{route_id}: unknown_provider")
    seen = set()
    for profile in config["profiles"]:
        prefix = f"profiles/{profile['id']}"
        if profile["id"] in seen:
            errors.append(f"{prefix}: duplicate_profile_id")
        seen.add(profile["id"])
        pattern = profile["match"]["window_title_pattern"]
        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error:
                errors.append(f"{prefix}: invalid_title_pattern")
        if "ocr" in profile["source"]["adapters"]:
            roi = profile["ocr"]["roi"]
            if roi["x"] + roi["w"] > 1 + 1e-9 or roi["y"] + roi["h"] > 1 + 1e-9:
                errors.append(f"{prefix}/ocr/roi: outside_client_area")
        if profile["enabled"]:
            if not profile["source"]["read_consent"]:
                errors.append(f"{prefix}: read_consent_required")
            if profile["source"]["access_policy_status"] != "allowed":
                errors.append(f"{prefix}: source_access_review_required")
            if "CHANGE_ME" in profile["match"]["process_name"].upper():
                errors.append(f"{prefix}: placeholder_target")
            if profile["sensitive_app"]:
                errors.append(f"{prefix}: sensitive_app_not_eligible")
            if "ocr" in profile["source"]["adapters"]:
                ocr = profile["ocr"]
                if not ocr["model_artifact"] or not ocr["charset_verified"]:
                    errors.append(f"{prefix}: ocr_artifact_and_charset_verification_required")
        if profile["send"]["method"] != "none_user_types":
            if not profile["source"]["native_identity_required_for_action"]:
                errors.append(f"{prefix}: native_identity_required")
            if not profile["attribution"]["self_ids"] and not profile["attribution"]["self_names"]:
                errors.append(f"{prefix}: self_identity_required")
            if (profile["autonomy"]["requested_level"] == "L4"
                    and not global_settings["ai_disclosure"]["enabled"]):
                errors.append(f"{prefix}: disclosure_required_for_L4")
    model_errors(config, {"models": []} if registry is None else registry, errors)
    return errors


def readiness(config: dict) -> list[str]:
    """Chỉ configuration preflight; không tự chạy mạng/capture hay mở action."""
    reasons = []
    active_profiles = [p for p in config["profiles"] if p["enabled"]]
    if not active_profiles:
        reasons.append("Chưa có profile thực tế được bật và cấp quyền.")
    routes = [v for v in config["generation"]["routes"].values() if v["enabled"]]
    if not routes:
        reasons.append("Chưa có generation route/model được verify và bật.")
    if not config["decision"]["enabled"]:
        reasons.append("Decision provider/model chưa được verify và bật.")
    return reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--registry", type=Path,
                        default=ROOT / "model_registry.example.json")
    parser.add_argument("--readiness", action="store_true")
    args = parser.parse_args()
    try:
        config = load_json(args.config)
        registry = load_json(args.registry)
        errors = validate(config, registry)
    except (ValueError, OSError, TypeError) as exc:
        print(f"KHÔNG HỢP LỆ: {type(exc).__name__}: {exc}")
        return 1
    if errors:
        print(f"KHÔNG HỢP LỆ — {len(errors)} lỗi")
        for error in errors:
            print(" -", error)
        return 1
    print("HỢP LỆ theo schema + semantic checks; không phải runtime certification.")
    if args.readiness:
        reasons = readiness(config)
        for reason in reasons:
            print(" -", reason)
        print("Windows/OCR/API integration và gate report cần kiểm riêng; "
              "validator không chứng nhận runtime.")
        return 2 if reasons else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())