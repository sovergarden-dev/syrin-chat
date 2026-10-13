"""Fixture tests. Các 'verified' model ở đây giả lập, KHÔNG gọi API thật."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_config import validate, load_json, no_duplicate_keys, readiness


def base():
    return load_json(ROOT / "config.example.json")


def template():
    return load_json(ROOT / "profile.template.json")


def manual_profile():
    p = template()
    p.update(enabled=True)
    p["match"]["process_name"] = "FIXTURE_CHAT.exe"
    p["source"].update(adapters=["uia"], read_consent=True,
                       access_policy_status="allowed")
    p.pop("ocr")
    p["autonomy"]["requested_level"] = "L2"
    return p


def action_config(level="L4"):
    c = base()
    p = manual_profile()
    p["policy"].update(
        tos_status="allowed", protection_status="absent",
        tos_reviewed_at="2026-10-13", tos_evidence_ref="fixture-only:not-live")
    p["autonomy"].update(
        requested_level=level, gate_report_ref="fixture-only:not-live",
        recipient_allowlist=["fixture:conversation:42"])
    p["send"]["method"] = "uia_value_pattern"
    p["attribution"]["self_ids"] = ["fixture:self"]
    c["profiles"] = [p]
    return c


def cloud_config():
    c = base()
    c["providers"]["gemini"].update(enabled=True, data_policy_status="no_training_reviewed")
    c["global_settings"]["privacy"].update(
        cloud_text_consent=True, cloud_provider_allowlist=["gemini"])
    # Test-only numbers; không phải budget của người dùng.
    c["global_settings"]["budget"].update(daily_usd=1, monthly_usd=5)
    c["generation"]["routes"]["fast"].update(
        enabled=True, model_id="fixture-model-not-a-real-API", thinking_level="low")
    registry = {
        "models": [{
            "provider_id": "gemini", "model_id": "fixture-model-not-a-real-API",
            "verification_status": "verified",
            "verified_at": "2026-10-13", "evidence_ref": "fixture-only:not-live",
            "retired": False, "tasks": ["generation"],
            "capabilities": {
                "structured_output": True, "streaming": True,
                "thinking_levels": [None, "low"], "max_output_tokens": 2048,
            },
        }]
    }
    return c, registry


class ConfigTests(unittest.TestCase):
    def test_safe_empty_config_valid(self):
        self.assertEqual(validate(base()), [])

    def test_disabled_template_valid(self):
        c = base()
        c["profiles"] = [template()]
        self.assertEqual(validate(c), [])

    def test_manual_profile_valid(self):
        c = base()
        c["profiles"] = [manual_profile()]
        self.assertEqual(validate(c), [])

    def test_action_config_fixture_valid(self):
        self.assertEqual(validate(action_config()), [])

    def test_cloud_registry_fixture_valid(self):
        c, registry = cloud_config()
        self.assertEqual(validate(c, registry), [])

    def test_requested_L4_with_no_action_saved_but_not_qualified(self):
        c = base()
        p = manual_profile()
        p["autonomy"]["requested_level"] = "L4"
        c["profiles"] = [p]
        self.assertEqual(validate(c), [])
        # Effective cap được thử riêng ở test_policy.py.

    def test_unknown_timezone_rejected(self):
        c = base()
        c["global_settings"]["quiet_hours"]["timezone"] = "Mars/Olympus"
        self.assertTrue(validate(c))

    def test_duplicate_JSON_key_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"version":"3.0","version":"2.4"}',
                       object_pairs_hook=no_duplicate_keys)

    def test_safe_example_not_ready(self):
        self.assertTrue(readiness(base()))

    def test_roi_overflow_rejected(self):
        c = base()
        p = template()
        p["ocr"]["roi"].update(x=0.8, w=0.4)
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_min_wait_exceeds_max_rejected(self):
        c = base()
        c["turn_taking"].update(min_wait_ms=4000, max_wait_ms=700)
        self.assertTrue(validate(c))

    def test_duplicate_profile_id_rejected(self):
        c = base()
        c["profiles"] = [template(), template()]
        self.assertTrue(validate(c))

    def test_duplicate_hotkey_alias_order_rejected(self):
        c = base()
        c["global_settings"]["cancel_hotkey"] = "Alt+Ctrl+Shift+F12"
        self.assertTrue(validate(c))

    def test_duplicate_hotkey_modifier_rejected(self):
        c = base()
        c["global_settings"]["cancel_hotkey"] = "Ctrl+Ctrl+F12"
        self.assertTrue(validate(c))

    def test_windows_ocr_vi_rejected(self):
        c = base()
        p = template()
        p["ocr"]["engine_id"] = "windows_media_ocr"
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_active_placeholder_rejected(self):
        c = base()
        p = template()
        p["enabled"] = True
        p["source"]["read_consent"] = True
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_missing_ocr_block_rejected(self):
        c = base()
        p = template()
        p.pop("ocr")
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_title_only_target_rejected(self):
        c = base()
        p = template()
        p["match"].pop("process_name")
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_bad_title_regex_rejected(self):
        c = base()
        p = template()
        p["match"]["window_title_pattern"] = "["
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_enabled_without_read_consent_rejected(self):
        c = base()
        p = manual_profile()
        p["source"]["read_consent"] = False
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_enabled_source_permission_unknown_rejected(self):
        c = base()
        p = manual_profile()
        p["source"]["access_policy_status"] = "unknown"
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_validator_never_echoes_bad_secret_value(self):
        c = base()
        c["providers"]["gemini"]["credential_ref"] = "fixture_secret_do_not_echo"
        errors = validate(c)
        self.assertTrue(errors)
        self.assertNotIn("fixture_secret_do_not_echo", "\n".join(errors))

    def test_enabled_sensitive_profile_rejected(self):
        c = base()
        p = manual_profile()
        p["sensitive_app"] = True
        c["profiles"] = [p]
        self.assertTrue(validate(c))

    def test_quiet_hours_same_start_end_rejected(self):
        c = base()
        c["global_settings"]["quiet_hours"].update(enabled=True, start="07:00", end="07:00")
        self.assertTrue(validate(c))

    def test_daily_above_monthly_rejected(self):
        c = base()
        c["global_settings"]["budget"].update(daily_usd=6, monthly_usd=5)
        self.assertTrue(validate(c))

    def test_local_non_loopback_rejected(self):
        c = base()
        c["providers"]["local"]["base_url"] = "http://192.168.1.2:11434"
        self.assertTrue(validate(c))

    def test_local_loopback_ipv6_valid(self):
        c = base()
        c["providers"]["local"]["base_url"] = "http://[::1]:11434"
        self.assertEqual(validate(c), [])

    def test_custom_endpoint_http_rejected(self):
        c = base()
        c["providers"]["custom"]["base_url"] = "http://api.example.test/v1"
        self.assertTrue(validate(c))

    def test_custom_endpoint_embedded_credentials_rejected(self):
        c = base()
        c["providers"]["custom"]["base_url"] = "https://key:secret@example.test/v1"
        self.assertTrue(validate(c))

    def test_custom_endpoint_query_rejected(self):
        c = base()
        c["providers"]["custom"]["base_url"] = "https://api.example.test/v1?key=fixture"
        self.assertTrue(validate(c))

    def test_custom_endpoint_private_ip_rejected(self):
        c = base()
        c["providers"]["custom"]["base_url"] = "https://127.0.0.1/v1"
        self.assertTrue(validate(c))

    def test_custom_endpoint_invalid_port_rejected(self):
        c = base()
        c["providers"]["custom"]["base_url"] = "https://api.example.test:99999"
        self.assertTrue(validate(c))

    def test_custom_enabled_endpoint_required(self):
        c = base()
        c["providers"]["custom"]["enabled"] = True
        self.assertTrue(validate(c))

    def test_unknown_cloud_allowlist_provider_rejected(self):
        c = base()
        c["global_settings"]["privacy"]["cloud_provider_allowlist"] = ["unknown"]
        self.assertTrue(validate(c))

    def test_stronger_not_enabled_rejected(self):
        c = base()
        c["decision"]["on_low_confidence"] = "retry_stronger"
        self.assertTrue(validate(c))

    def test_unknown_route_provider_rejected(self):
        c = base()
        c["generation"]["routes"]["fast"]["provider_id"] = "unknown"
        self.assertTrue(validate(c))

    def test_active_unverified_model_rejected(self):
        c, _ = cloud_config()
        self.assertTrue(validate(c))

    def test_model_supported_thinking_required(self):
        c, registry = cloud_config()
        c["generation"]["routes"]["fast"]["thinking_level"] = "minimal"
        self.assertTrue(validate(c, registry))

    def test_registry_output_limit_enforced(self):
        c, registry = cloud_config()
        c["generation"]["routes"]["fast"]["max_output_tokens"] = 3000
        self.assertTrue(validate(c, registry))

    def test_retired_registry_model_rejected(self):
        c, registry = cloud_config()
        registry["models"][0]["retired"] = True
        self.assertTrue(validate(c, registry))

    def test_registry_wrong_task_rejected(self):
        c, registry = cloud_config()
        registry["models"][0]["tasks"] = ["decision"]
        self.assertTrue(validate(c, registry))

    def test_registry_missing_evidence_rejected(self):
        c, registry = cloud_config()
        registry["models"][0].pop("evidence_ref")
        self.assertTrue(validate(c, registry))

    def test_registry_duplicate_model_rejected(self):
        c, registry = cloud_config()
        registry["models"].append(copy.deepcopy(registry["models"][0]))
        self.assertTrue(validate(c, registry))

    def test_active_alias_model_rejected(self):
        c, registry = cloud_config()
        c["generation"]["routes"]["fast"]["model_id"] = "latest"
        self.assertTrue(validate(c, registry))

    def test_registry_structured_output_required(self):
        c, registry = cloud_config()
        registry["models"][0]["capabilities"]["structured_output"] = False
        self.assertTrue(validate(c, registry))

    def test_registry_streaming_required(self):
        c, registry = cloud_config()
        registry["models"][0]["capabilities"]["streaming"] = False
        self.assertTrue(validate(c, registry))

    def test_registry_truthy_string_not_capability_proof(self):
        c, registry = cloud_config()
        registry["models"][0]["capabilities"]["structured_output"] = "true"
        self.assertTrue(validate(c, registry))

    def test_registry_malformed_task_list_rejected(self):
        c, registry = cloud_config()
        registry["models"][0]["tasks"] = [{}]
        self.assertTrue(validate(c, registry))

    def test_cloud_provider_disabled_route_rejected(self):
        c, registry = cloud_config()
        c["providers"]["gemini"]["enabled"] = False
        self.assertTrue(validate(c, registry))


def make_negative_test(path, value, factory=base):
    def test(self):
        generated = factory()
        if isinstance(generated, tuple):
            c, registry = generated
        else:
            c, registry = generated, None
        node = c
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        self.assertTrue(validate(c, registry), "Cấu hình nguy hiểm đã lọt")
    return test


NEGATIVES = [
    ("unknown_root_field", ("unsafe_bypass",), True, base),
    ("plaintext_key", ("providers", "gemini", "api_key"), "fixture_secret", base),
    ("unknown_nested", ("perception", "pixel_click_target"), [10, 20], base),
    ("old_version", ("version",), "2.4", base),
    ("kill_key_esc", ("global_settings", "kill_switch_hotkey"), "Esc", base),
    ("cancel_key_enter", ("global_settings", "cancel_hotkey"), "Enter", base),
    ("resume_action", ("global_settings", "resume_action_after_restart"), True, base),
    ("presence_bypass", ("global_settings", "presence", "required_for_autosend"), False, base),
    ("cancel_input_bypass", ("global_settings", "presence", "cancel_on_user_input"), False, base),
    ("screenshot_storage", ("global_settings", "storage", "store_screenshots"), True, base),
    ("plaintext_storage", ("global_settings", "storage", "encryption"), "none", base),
    ("content_logging", ("global_settings", "logging", "log_message_content"), True, base),
    ("sdk_debug_logging", ("global_settings", "logging", "sdk_debug_logging"), True, base),
    ("pii_bypass", ("global_settings", "privacy", "pii_redaction_required"), False, base),
    ("too_many_sends", ("global_settings", "rate_limits",
                        "max_sends_per_conversation_per_10min"), 100, base),
    ("too_fast_sends", ("global_settings", "rate_limits", "min_seconds_between_sends"), 1, base),
    ("output_guard_bypass", ("generation", "output_guard"), False, base),
    ("partial_stream_send", ("generation", "send_partial_stream"), True, base),
    ("tiny_output_limit", ("generation", "routes", "fast", "max_output_tokens"), 120, base),
    ("calibration_bypass", ("decision", "requires_calibration_for_autosend"), False, base),
    ("autosend_lowconfidence", ("decision", "on_low_confidence"), "autosend", base),
    ("disable_cancel_new_msg", ("turn_taking", "cancel_draft_on_new_message"), False, base),
    ("too_few_stable_frames", ("perception", "stable_frames_required"), 1, base),
    ("cloud_no_consent", ("global_settings", "privacy", "cloud_text_consent"), False, cloud_config),
    ("cloud_no_budget", ("global_settings", "budget", "daily_usd"), None, cloud_config),
    ("cloud_not_allowlisted", ("global_settings", "privacy", "cloud_provider_allowlist"), [], cloud_config),
    ("cloud_policy_unreviewed", ("providers", "gemini", "data_policy_status"), "not_reviewed", cloud_config),
    ("cloud_no_credential_ref", ("providers", "gemini", "credential_ref"), None, cloud_config),
    ("action_tos_unknown", ("profiles", 0, "policy", "tos_status"), "unknown", action_config),
    ("action_tos_prohibited", ("profiles", 0, "policy", "tos_status"), "prohibited", action_config),
    ("action_protected", ("profiles", 0, "policy", "protection_status"), "present", action_config),
    ("action_protection_unknown", ("profiles", 0, "policy", "protection_status"), "unknown", action_config),
    ("action_no_gate_report", ("profiles", 0, "autonomy", "gate_report_ref"), None, action_config),
    ("action_no_allowlist", ("profiles", 0, "autonomy", "recipient_allowlist"), [], action_config),
    ("action_no_disclosure", ("global_settings", "ai_disclosure", "enabled"), False, action_config),
    ("action_scan_code_jitter", ("profiles", 0, "send", "method"), "directinput_scancode_jitter", action_config),
    ("action_no_verify", ("profiles", 0, "send", "verify_after_send"), False, action_config),
    ("action_auto_focus", ("profiles", 0, "send", "auto_focus"), True, action_config),
    ("action_overwrite_input", ("profiles", 0, "send", "input_must_be_empty"), False, action_config),
    ("action_no_native_id", ("profiles", 0, "source", "native_identity_required_for_action"), False, action_config),
    ("action_short_countdown", ("profiles", 0, "autonomy", "countdown_seconds"), 1, action_config),
]
for name, path, value, factory in NEGATIVES:
    setattr(ConfigTests, f"test_reject_{name}", make_negative_test(path, value, factory))


if __name__ == "__main__":
    unittest.main()