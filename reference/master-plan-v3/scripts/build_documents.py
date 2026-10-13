#!/usr/bin/env python3
"""Sinh các artifact chuẩn từ project.json. Không triển khai app Windows."""
from __future__ import annotations

import argparse
import copy
import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
LIMITS = META["hard_limits"]


def write_json(path: str, value: object) -> None:
    (ROOT / path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def obj(properties: dict, required: list[str] | None = None, **extra) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties) if required is None else required,
        **extra,
    }


def enum(*values) -> dict:
    return {"enum": list(values)}


def integer(lo: int, hi: int) -> dict:
    return {"type": "integer", "minimum": lo, "maximum": hi}


def number(lo: float, hi: float) -> dict:
    return {"type": "number", "minimum": lo, "maximum": hi}


def text(*, nullable: bool = False, pattern: str | None = None) -> dict:
    node = {"type": ["string", "null"] if nullable else "string", "minLength": 1}
    if pattern:
        node["pattern"] = pattern
    return node


def strings(*, values: list | None = None, minimum: int = 0) -> dict:
    return {
        "type": "array",
        "items": enum(*values) if values is not None else text(),
        "uniqueItems": True,
        "minItems": minimum,
    }


def ref(name: str) -> dict:
    return {"$ref": f"#/$defs/{name}"}


def route(provider: str, tokens: int) -> dict:
    return {
        "enabled": False,
        "provider_id": provider,
        "model_id": None,
        "max_output_tokens": tokens,
        "thinking_level": None,
        "timeout_ms": 10000,
    }


def configuration() -> dict:
    return {
        "$schema": "./profiles.schema.json",
        "version": META["version"],
        "global_settings": {
            "default_requested_level_after_wizard": "L2",
            "start_paused": True,
            "resume_action_after_restart": False,
            "kill_switch_hotkey": "Ctrl+Alt+Shift+F12",
            "cancel_hotkey": "Ctrl+Alt+F12",
            "send_now_hotkey": "Ctrl+Alt+F11",
            "presence": {
                "required_for_autosend": True,
                "idle_threshold_seconds": 60,
                "cancel_on_user_input": True,
            },
            "ai_disclosure": {
                "enabled": True,
                "text": " · (trợ lý AI)",
                "answer_honestly_if_asked": True,
            },
            "storage": {
                "mode": "memory_only",
                "database_path": "%LOCALAPPDATA%\\AutoChatAgent\\transcripts.db",
                "encryption": "sqlcipher_dpapi",
                "retention_days": 7,
                "store_screenshots": False,
            },
            "logging": {
                "level": "INFO",
                "log_message_content": False,
                "sdk_debug_logging": False,
            },
            "privacy": {
                "cloud_text_consent": False,
                "cloud_provider_allowlist": [],
                "pii_redaction_required": True,
                "style_learning_enabled": False,
                "sensitive_process_denylist": [
                    "KeePassXC.exe", "1Password.exe", "Bitwarden.exe"
                ],
            },
            "budget": {
                "currency": "USD",
                "daily_usd": None,
                "monthly_usd": None,
                "on_exceeded": "pause_cloud_calls",
            },
            "rate_limits": {
                "max_sends_per_conversation_per_10min":
                    LIMITS["max_sends_per_conversation_per_10min"],
                "max_consecutive_agent_turns": LIMITS["max_consecutive_agent_turns"],
                "min_seconds_between_sends": LIMITS["min_seconds_between_sends"],
                "duplicate_attempt_window_minutes": 10,
            },
            "quiet_hours": {
                "enabled": False,
                "start": "23:00",
                "end": "07:00",
                "timezone": META["timezone"],
            },
        },
        "providers": {
            "typesafe": {
                "kind": "typesafe_official",
                "enabled": False,
                "credential_ref": "wincred:AutoChatAgent/typesafe",
                "base_url": None,
                "data_policy_status": "not_reviewed",
            },
            "gemini": {
                "kind": "gemini_official",
                "enabled": False,
                "credential_ref": "wincred:AutoChatAgent/gemini",
                "base_url": None,
                "data_policy_status": "not_reviewed",
            },
            "custom": {
                "kind": "openai_compatible",
                "enabled": False,
                "credential_ref": "wincred:AutoChatAgent/custom",
                "base_url": None,
                "data_policy_status": "not_reviewed",
            },
            "local": {
                "kind": "ollama_local",
                "enabled": False,
                "credential_ref": None,
                "base_url": "http://127.0.0.1:11434",
                "data_policy_status": "local_only",
            },
        },
        "perception": {
            "capture_backend": "windows_graphics_capture",
            "fallback_capture_backend": "dxgi_dxcam",
            "max_capture_hz": 4,
            "exclude_own_overlays": True,
            "stable_frames_required": 2,
            "normalized_roi_required": True,
            "detect_scroll_and_wrap": True,
            "on_source_unavailable": "pause_profile",
        },
        "turn_taking": {
            "min_wait_ms": 700,
            "max_wait_ms": 4000,
            "use_typing_indicator_if_available": True,
            "cancel_draft_on_new_message": True,
            "on_incomplete_at_max_wait": "ask_confirmation",
        },
        "decision": {
            "enabled": False,
            "provider_id": "typesafe",
            "model_id": None,
            "timeout_ms": 1500,
            "question_set": "chat_gate_vi_v1",
            "on_low_confidence": "suggest_only",
            "on_error": "suggest_only",
            "on_timeout": "suggest_only",
            "stronger_route_id": "stronger",
            "max_stronger_retries": 1,
            "requires_calibration_for_autosend": True,
            "thresholds": {
                "min_decision_confidence": 0.85,
                "addressed_to_me": 0.60,
                "needs_reply": 0.60,
                "turn_complete": 0.60,
                "hazard_escalate": 0.30,
                "reflex_choice_confidence": 0.90,
            },
        },
        "generation": {
            "routes": {
                "fast": route("gemini", 1024),
                "complex": route("gemini", 2048),
                "stronger": route("custom", 2048),
                "local_private": route("local", 512),
            },
            "candidates": 1,
            "reply_max_chars": 160,
            "structured_output": True,
            "streaming_preview": True,
            "output_guard": True,
            "send_partial_stream": False,
        },
        "profiles": [],
    }


def profile_template() -> dict:
    return {
        "id": "new_profile_template",
        "enabled": False,
        "sensitive_app": False,
        "match": {
            "process_name": "CHANGE_ME.exe",
            "executable_path": None,
            "window_class": None,
            "window_title_pattern": None,
        },
        "languages": ["vi"],
        "source": {
            "adapters": ["uia", "ocr"],
            "read_consent": False,
            "access_policy_status": "unknown",
            "native_identity_required_for_action": True,
        },
        "ocr": {
            "engine_id": "vietocr",
            "model_artifact": None,
            "charset_verified": False,
            "roi": {
                "anchor": "client",
                "units": "normalized",
                "x": 0.05, "y": 0.65, "w": 0.40, "h": 0.25,
            },
            "preprocess": "bakeoff_pending",
        },
        "attribution": {
            "self_ids": [],
            "self_names": [],
            "unknown_speaker_policy": "no_action",
            "use_sent_ledger": True,
        },
        "policy": {
            "tos_status": "unknown",
            "tos_reviewed_at": None,
            "tos_evidence_ref": None,
            "protection_status": "unknown",
        },
        "autonomy": {
            "requested_level": "L0",
            "countdown_seconds": LIMITS["recommended_countdown_seconds"],
            "recipient_allowlist": [],
            "gate_report_ref": None,
        },
        "send": {
            "method": "none_user_types",
            "verify_after_send": True,
            "input_must_be_empty": True,
            "auto_focus": False,
            "verification_timeout_ms": 5000,
        },
        "persona_prompt":
            "Trả lời ngắn gọn, tự nhiên, không bịa; không tự cam kết hoặc tiết lộ thông tin riêng.",
    }


def schema() -> dict:
    false = {"const": False}
    true = {"const": True}
    model_id = text(nullable=True)
    provider_id = text(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    hotkey = {
        "type": "string",
        "pattern": r"^(?:(?:Ctrl|Alt|Shift|Win)\+)+(?:F(?:[1-9]|1[0-2])|[A-Z0-9])$",
    }
    credential = {
        "type": ["string", "null"],
        "pattern": r"^wincred:AutoChatAgent/[A-Za-z0-9_.-]+$",
    }
    nullable_date = {"type": ["string", "null"], "format": "date"}
    dollar_limit = {"type": ["number", "null"], "exclusiveMinimum": 0}
    defs = {}
    defs["global_settings"] = obj({
        "default_requested_level_after_wizard": enum("L0", "L1", "L2"),
        "start_paused": true,
        "resume_action_after_restart": false,
        "kill_switch_hotkey": hotkey,
        "cancel_hotkey": hotkey,
        "send_now_hotkey": hotkey,
        "presence": obj({
            "required_for_autosend": true,
            "idle_threshold_seconds": integer(10, 300),
            "cancel_on_user_input": true,
        }),
        "ai_disclosure": obj({
            "enabled": {"type": "boolean"},
            "text": text(),
            "answer_honestly_if_asked": true,
        }),
        "storage": obj({
            "mode": enum("memory_only", "encrypted_persistent"),
            "database_path": text(),
            "encryption": {"const": "sqlcipher_dpapi"},
            "retention_days": integer(1, 30),
            "store_screenshots": false,
        }),
        "logging": obj({
            "level": enum("INFO", "WARNING", "ERROR"),
            "log_message_content": false,
            "sdk_debug_logging": false,
        }),
        "privacy": obj({
            "cloud_text_consent": {"type": "boolean"},
            "cloud_provider_allowlist": strings(),
            "pii_redaction_required": true,
            "style_learning_enabled": {"type": "boolean"},
            "sensitive_process_denylist": strings(),
        }),
        "budget": obj({
            "currency": {"const": "USD"},
            "daily_usd": dollar_limit,
            "monthly_usd": dollar_limit,
            "on_exceeded": {"const": "pause_cloud_calls"},
        }),
        "rate_limits": obj({
            "max_sends_per_conversation_per_10min":
                integer(1, LIMITS["max_sends_per_conversation_per_10min"]),
            "max_consecutive_agent_turns":
                integer(1, LIMITS["max_consecutive_agent_turns"]),
            "min_seconds_between_sends":
                integer(LIMITS["min_seconds_between_sends"], 3600),
            "duplicate_attempt_window_minutes": integer(10, 1440),
        }),
        "quiet_hours": obj({
            "enabled": {"type": "boolean"},
            "start": {"type": "string", "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$"},
            "end": {"type": "string", "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$"},
            "timezone": text(),
        }),
    })
    defs["provider"] = obj({
        "kind": enum("typesafe_official", "gemini_official",
                     "openai_compatible", "ollama_local"),
        "enabled": {"type": "boolean"},
        "credential_ref": credential,
        "base_url": text(nullable=True),
        "data_policy_status": enum("not_reviewed", "no_training_reviewed", "local_only"),
    }, allOf=[
        {
            "if": {"properties": {"kind": enum("typesafe_official", "gemini_official")}},
            "then": {"properties": {"base_url": {"const": None}}},
        },
        {
            "if": {"properties": {"kind": {"const": "ollama_local"}}},
            "then": {"properties": {"data_policy_status": {"const": "local_only"}}},
        },
    ])
    defs["providers"] = {
        "type": "object", "additionalProperties": False,
        "patternProperties": {r"^[a-z][a-z0-9_]{0,31}$": ref("provider")},
        "minProperties": 1,
    }
    defs["route"] = obj({
        "enabled": {"type": "boolean"},
        "provider_id": provider_id,
        "model_id": model_id,
        "max_output_tokens": integer(256, 32768),
        "thinking_level": enum(None, "none", "minimal", "low", "medium", "high"),
        "timeout_ms": integer(500, 60000),
    })
    defs["routes"] = {
        "type": "object", "additionalProperties": False,
        "patternProperties": {r"^[a-z][a-z0-9_]{0,31}$": ref("route")},
        "minProperties": 1,
    }
    defs["roi"] = obj({
        "anchor": {"const": "client"},
        "units": {"const": "normalized"},
        "x": number(0, 1), "y": number(0, 1),
        "w": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
        "h": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
    })
    defs["ocr"] = obj({
        "engine_id": text(),
        "model_artifact": text(nullable=True),
        "charset_verified": {"type": "boolean"},
        "roi": ref("roi"),
        "preprocess": enum("bakeoff_pending", "none", "upscale",
                           "otsu", "hsv_mask", "custom_reviewed"),
    })
    defs["profile"] = obj({
        "id": provider_id,
        "enabled": {"type": "boolean"},
        "sensitive_app": {"type": "boolean"},
        "match": obj({
            "process_name": text(pattern=r"^[^\\/:\x00]+\.exe$"),
            "executable_path": text(nullable=True),
            "window_class": text(nullable=True),
            "window_title_pattern": text(nullable=True),
        }),
        "languages": strings(values=["vi", "en"], minimum=1),
        "source": obj({
            "adapters": strings(values=[
                "official_api", "uia", "notification", "browser_dom", "local_log", "ocr"
            ], minimum=1),
            "read_consent": {"type": "boolean"},
            "access_policy_status": enum("unknown", "allowed", "prohibited"),
            "native_identity_required_for_action": true,
        }),
        "ocr": ref("ocr"),
        "attribution": obj({
            "self_ids": strings(),
            "self_names": strings(),
            "unknown_speaker_policy": {"const": "no_action"},
            "use_sent_ledger": true,
        }),
        "policy": obj({
            "tos_status": enum("unknown", "allowed", "prohibited"),
            "tos_reviewed_at": nullable_date,
            "tos_evidence_ref": text(nullable=True),
            "protection_status": enum("unknown", "present", "absent"),
        }),
        "autonomy": obj({
            "requested_level": enum(*[x["id"] for x in META["autonomy_levels"]]),
            "countdown_seconds": number(
                LIMITS["min_countdown_seconds"], LIMITS["max_countdown_seconds"]),
            "recipient_allowlist": strings(),
            "gate_report_ref": text(nullable=True),
        }),
        "send": obj({
            "method": enum("none_user_types", "official_api",
                           "uia_value_pattern", "clipboard_paste_safe"),
            "verify_after_send": true,
            "input_must_be_empty": true,
            "auto_focus": false,
            "verification_timeout_ms": integer(1000, 30000),
        }),
        "persona_prompt": {"type": "string", "maxLength": 4000},
    }, required=[
        "id", "enabled", "sensitive_app", "match", "languages", "source",
        "attribution", "policy", "autonomy", "send", "persona_prompt",
    ], allOf=[
        {
            "if": {"properties": {
                "source": {"properties": {
                    "adapters": {"contains": {"const": "ocr"}}
                }}
            }},
            "then": {"required": ["ocr"]},
        },
        {
            "if": {"properties": {"languages": {"contains": {"const": "vi"}}}},
            "then": {"properties": {"ocr": {"properties": {
                "engine_id": {"not": {"enum": ["windows_media_ocr", "winocr"]}}
            }}}},
        },
        {
            "if": {"properties": {"send": {"properties": {
                "method": {"not": {"const": "none_user_types"}}
            }}}},
            "then": {"properties": {
                "sensitive_app": false,
                "source": {"properties": {"read_consent": true}},
                "policy": {"properties": {
                    "tos_status": {"const": "allowed"},
                    "protection_status": {"const": "absent"},
                    "tos_reviewed_at": {"type": "string", "format": "date"},
                    "tos_evidence_ref": text(),
                }},
                "autonomy": {"properties": {
                    "requested_level": enum("L3", "L4"),
                    "gate_report_ref": text(),
                }},
            }},
        },
        {
            "if": {"properties": {
                "autonomy": {"properties": {"requested_level": {"const": "L4"}}},
                "send": {"properties": {"method": {"not": {"const": "none_user_types"}}}},
            }},
            "then": {"properties": {"autonomy": {"properties": {
                "recipient_allowlist": {"minItems": 1},
            }}}},
        },
    ])
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Auto-Chat Agent V3 — configuration",
        "description":
            "Cấu trúc + hard guardrails. Validation hợp lệ không chứng minh runtime qualification.",
        **obj({
            "$schema": {"const": "./profiles.schema.json"},
            "version": {"const": META["version"]},
            "global_settings": ref("global_settings"),
            "providers": ref("providers"),
            "perception": obj({
                "capture_backend": enum("windows_graphics_capture", "dxgi_dxcam"),
                "fallback_capture_backend": enum("none", "dxgi_dxcam"),
                "max_capture_hz": integer(1, 10),
                "exclude_own_overlays": true,
                "stable_frames_required": integer(2, 10),
                "normalized_roi_required": true,
                "detect_scroll_and_wrap": true,
                "on_source_unavailable": {"const": "pause_profile"},
            }),
            "turn_taking": obj({
                "min_wait_ms": integer(100, 10000),
                "max_wait_ms": integer(100, 10000),
                "use_typing_indicator_if_available": {"type": "boolean"},
                "cancel_draft_on_new_message": true,
                "on_incomplete_at_max_wait": enum("ask_confirmation", "skip", "suggest_only"),
            }),
            "decision": obj({
                "enabled": {"type": "boolean"},
                "provider_id": provider_id,
                "model_id": model_id,
                "timeout_ms": integer(500, 10000),
                "question_set": text(),
                "on_low_confidence": enum(*LIMITS["on_low_confidence"]),
                "on_error": enum("suggest_only", "skip", "ask_confirmation"),
                "on_timeout": enum("suggest_only", "skip", "ask_confirmation"),
                "stronger_route_id": text(nullable=True),
                "max_stronger_retries": integer(0, 1),
                "requires_calibration_for_autosend": true,
                "thresholds": obj({
                    "min_decision_confidence": number(0.5, 1),
                    "addressed_to_me": number(0.5, 1),
                    "needs_reply": number(0.5, 1),
                    "turn_complete": number(0.5, 1),
                    "hazard_escalate": number(0.05, 0.3),
                    "reflex_choice_confidence": number(0.85, 1),
                }),
            }),
            "generation": obj({
                "routes": ref("routes"),
                "candidates": integer(1, 3),
                "reply_max_chars": integer(20, 1000),
                "structured_output": true,
                "streaming_preview": {"type": "boolean"},
                "output_guard": true,
                "send_partial_stream": false,
            }),
            "profiles": {"type": "array", "items": ref("profile"), "maxItems": 100},
        }),
        "$defs": defs,
    }


def table(headers: list[str], rows: list[list[str]]) -> str:
    clean = lambda x: str(x).replace("|", r"\|").replace("\n", " ")
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    out += ["| " + " | ".join(map(clean, row)) + " |" for row in rows]
    return "\n".join(out)


def replace_section(path: Path, key: str, content: str) -> None:
    original = path.read_text(encoding="utf-8")
    pattern = rf"(<!-- BEGIN:{key} -->).*?(<!-- END:{key} -->)"
    replacement, n = re.subn(pattern, lambda m:
                            m[1] + "\n" + content + "\n" + m[2],
                            original, flags=re.S)
    if n != 1:
        raise ValueError(f"{path.name}: cần đúng một section {key}, nhận {n}")
    path.write_text(replacement, encoding="utf-8")


def build_markdown() -> None:
    gates = table(
        ["Gate", "Tiêu chí đề xuất", "Bằng chứng cần có", "Trạng thái"],
        [[g["id"] + " — " + g["name"], g["threshold"], g["method"], g["status"]]
         for g in META["gates"]]
    )
    for name in ["AUTO_CHAT_AGENT_MASTER_PLAN.md", "AUDIT_CHECKLIST.md"]:
        replace_section(ROOT / name, "GATES", gates)
    levels = table(["Mức", "Agent", "Người dùng"],
                   [[x["id"] + " — " + x["name"], x["agent"], x["user"]]
                    for x in META["autonomy_levels"]])
    replace_section(ROOT / "AUTO_CHAT_AGENT_MASTER_PLAN.md", "AUTONOMY", levels)
    latency = table(["Chỉ số", "Định nghĩa", "Target chưa đo"],
                    [[x["metric"], x["definition"], x["target"]]
                     for x in META["latency_targets"]])
    replace_section(ROOT / "AUTO_CHAT_AGENT_MASTER_PLAN.md", "LATENCY", latency)
    readme = f"""# Auto-Chat Agent — bộ kế hoạch V{META['version']}

**Cá nhân trước · App/game chọn sau · Setting có kiểm soát**

Đây là bộ đặc tả đã sửa, **không phải app đã xây xong**.

## Đọc theo thứ tự

1. `AUTO_CHAT_AGENT_MASTER_PLAN.md` — kế hoạch triển khai chuẩn.
2. `Nghiên cứu Auto-Chat Agent.html` hoặc `Auto-Chat-Agent-Master-Plan-V3.pdf` — bản đọc trực quan của Master Plan.
3. `SETTINGS_SPEC.md` — các lựa chọn autonomy/low-confidence/provider/privacy/budget.
4. `AUDIT_CHECKLIST.md` — gate cá nhân và gate trước công khai.
5. `DECISIONS_AND_ASSUMPTIONS.md`, `CHANGELOG.md` — quyết định, unknown và thay đổi.

## Bắt đầu an toàn

- `config.example.json`: profile rỗng, provider/route tắt, model ID chưa chọn, cloud chưa consent, ngân sách chưa đặt.
- `profile.template.json`: mẫu profile tắt; thay placeholder sau khi chọn app thật.
- `model_registry.example.json`: registry rỗng; phải verify API/model/capability trước enable.
- `profiles.schema.json`: kiểm cấu trúc. `scripts/validate_config.py`: thêm ràng buộc chéo/endpoint/registry.
- `policy_core.py`: logic tham chiếu offline; không đọc màn hình, gọi API hoặc gửi chat.
- `tests/`: mock/fixture, không phải Windows integration test.

## Tự kiểm tra

Python 3.12+; tạo venv riêng và review dependency trước cài:

```bash
python -m venv .venv
# Windows: .venv\\\\Scripts\\\\activate
python -m pip install -r requirements-docs.txt
python scripts/validate_config.py config.example.json
python -m unittest discover -s tests -v
# Hoặc sinh lại báo cáo QA:
python scripts/run_checks.py
```

`python scripts/validate_config.py config.example.json --readiness` **phải báo chưa sẵn sàng** với config mẫu, vì chưa chọn app/model/consent. JSON hợp lệ không có nghĩa đã dùng được trên Windows.

Sinh lại bảng/schema/config/HTML:

```bash
python scripts/build_documents.py
# PDF tùy chọn, cần Chromium local:
python scripts/build_documents.py --pdf
```

Script build ghi lại file **mẫu**; không trỏ nó vào config cá nhân đang dùng. `project.json` là nguồn level/ngưỡng.

## Bằng chứng và giới hạn

Xem `qa/validation_summary.json` và `qa/test_results.txt` cho kết quả chạy trong sandbox. Những bài test này không chứng minh OCR, provider API, hotkey, clipboard hay actuator Windows.

`bench/` giữ công cụ OCR tham khảo, chưa chạy ảnh thật của app bạn. `reference/` là audit/phác thảo lịch sử, không baseline active; model/giá/link cần recheck.

Mốc cá nhân: ít nhất một profile thật, ≥ {LIMITS['min_personal_active_days_before_public_review']} ngày sử dụng có hoạt động, gate áp dụng đạt. Không yêu cầu mở L4 hoặc chốt ba game.

## Bản gói

Giữ nguyên tên sáu file lõi của gói cũ nhưng đã thay nội dung V3; thêm setting, quyết định, traceability và code kiểm thử. Không chứa API key, screenshot riêng tư hoặc dữ liệu hội thoại thật.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def traceability() -> None:
    sections = {
        "A": ["§5 OCR; schema profile", "§5 charset/bake-off", "§5 preprocessing",
              "§11 perf; §5 capture", "§4.2/5 ROI; validator", "§5 overlay"],
        "B": ["§6.2/6.3 registry", "§6.2 Jev role", "§11 measured latency/cost",
              "§6.2 VN eval", "§6.2 fan-out", "§6.1 rule; §6.2 calibration",
              "§9 official dependencies"],
        "C": ["§6.3 model verification", "§6.3 output budget",
              "§6.3 capability registry", "§6.3 no invented replacement ID",
              "§11 usage + dated pricing", "§9 data policy/consent",
              "§12 provider interface", "§12 local bake-off"],
        "D": ["§8 input risk; không dùng mouse flag cho keyboard",
              "§1/2 Zero-Evasion", "§1/2 no driver", "§1/2 no evasion jitter",
              "§8 clipboard", "§8 RegisterHotKey", "§8 modifier hotkeys",
              "§7 presence/allowlist", "§7 L2 manual-only",
              "§8 permit/verify", "§4.2 process binding",
              "§7 protected cap; schema/validator"],
        "E": ["§9 source review; không active repo rủi ro",
              "§5/12 capture upstream review", "§15 authoritative sources",
              "§9 SDK/pin/hash/SBOM"],
        "F": ["§11 metric definitions", "§1/2 bỏ jitter", "§8/11 cancellation",
              "§10 sampled precision, no 100% claim", "§11 targets unmeasured",
              "Master Plan TOC generated from headings", "§7 earned autonomy",
              "§10/11 evidence status"],
        "G": ["schema đủ field và additionalProperties",
              "schema + semantic cross-field validator",
              "credential_ref only", "modifier hotkey schema + collision validation",
              "verified model/capability registry; no unchecked string activation"],
    }
    records = [
        {"erratum": f"{letter}{i}", "applied_to_spec": True,
         "location": location,
         "product_validation": "pending_where_applicable"}
        for letter, locations in sections.items()
        for i, location in enumerate(locations, 1)
    ]
    if len(records) != 50:
        raise AssertionError("Traceability phải có 50 errata")
    write_json("reference/traceability.json", {
        "baseline": "2.4", "target": META["version"],
        "meaning": "Đã sửa đặc tả, không phải 50 product fixes đã được integration-test.",
        "records": records,
    })


CSS = """
:root {color-scheme:light dark;--bg:#fff;--surface:#f9f8f7;--text:#2c2c2b;
 --muted:#605d59;--border:#e6e5e3;--blue:#1d65b0;--soft:#e5f2fc;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
 font:16px/1.6 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
.page{max-width:1080px;margin:auto;padding:40px 32px 64px}
.intro{padding:24px;border:1px solid var(--border);background:var(--surface);
 border-top:4px solid var(--blue);border-radius:8px;margin-bottom:32px}
.eyebrow{font-size:14px;color:var(--blue);font-weight:700;letter-spacing:.06em}
.intro h1{font-size:32px;line-height:1.2;margin:8px 0 12px}
.intro p{margin:4px 0}
.status{font-size:14px;color:var(--muted)}
nav{border:1px solid var(--border);padding:20px 24px;border-radius:8px;margin-bottom:32px}
nav strong{display:block;margin-bottom:8px}
nav ol{columns:2;column-gap:32px;margin:0;padding-left:0;font-size:14px;list-style:none}
nav li{break-inside:avoid;margin:0 0 4px}
nav a{display:block;min-height:44px;padding:8px 0}
a{color:var(--blue);overflow-wrap:anywhere}
a:focus-visible{outline:3px solid var(--blue);outline-offset:3px}
article{max-width:760px;margin:auto}
article>h1{font-size:28px;line-height:1.25}
h2{font-size:24px;line-height:1.3;margin:40px 0 16px;padding-top:8px;
 border-bottom:1px solid var(--border);padding-bottom:12px}
h3{font-size:19px;line-height:1.4;margin:24px 0 12px}
p,ul,ol{margin:12px 0}
li{margin:6px 0}
pre{background:var(--surface);border:1px solid var(--border);border-radius:8px;
 padding:16px;overflow:auto;font:13px/1.5 Consolas,monospace}
code{font-size:.88em;overflow-wrap:anywhere}
pre code{font:inherit;white-space:pre}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;line-height:1.55;
 table-layout:fixed}
th,td{padding:12px;border:1px solid var(--border);vertical-align:top;overflow-wrap:anywhere}
th{text-align:left;background:var(--soft);color:var(--text)}
.table-wrap{overflow-x:auto}
blockquote{border-left:4px solid var(--blue);margin:16px 0;padding:8px 20px;background:var(--surface)}
footer{font-size:14px;color:var(--muted);border-top:1px solid var(--border);padding-top:16px;margin-top:40px}
@media(prefers-color-scheme:dark){:root{--bg:#191919;--surface:#202020;--text:#f5f5f5;
 --muted:#c0bdb8;--border:#47443f;--blue:#83bcff;--soft:#263647}}
@media(max-width:600px){.page{padding:24px 16px 40px}.intro{padding:20px}
 .intro h1{font-size:28px}nav{padding:16px}nav ol{columns:1}
 h2{font-size:23px}table{min-width:660px}pre{font-size:13px}
 .table-wrap::before{content:"Bảng rộng — vuốt ngang để xem đủ.";display:block;
  font-size:14px;color:var(--muted);margin:8px 0 0}}
@media print{
 :root{color-scheme:light;--bg:#fff;--surface:#f9f8f7;--text:#2c2c2b;
 --muted:#605d59;--border:#d4d1cd;--blue:#1d65b0;--soft:#e5f2fc}
 @page{size:A4;margin:16mm 15mm 17mm;
  @bottom-left{content:"AUTO-CHAT AGENT · V3.0";font:9pt Arial,sans-serif;color:#605d59}
  @bottom-right{content:counter(page) " / " counter(pages);font:9pt Arial,sans-serif;color:#605d59}}
 body{font:11pt/1.45 Arial,sans-serif}
 .page{max-width:none;padding:0}
 .intro{padding:6mm;margin-bottom:8mm}
 .intro h1{font-size:24pt}
 .eyebrow,.status,nav{font-size:9pt}
 nav{padding:5mm;margin-bottom:8mm}
 nav ol{columns:2;font-size:9pt}
 nav a{text-decoration:none;color:#2c2c2b;min-height:0;padding:0}
 article{max-width:none}
 article>h1{display:none}
 h2{font-size:16pt;margin:8mm 0 4mm;break-after:avoid}
 h3{font-size:13pt;margin:6mm 0 3mm;break-after:avoid}
 p,ul,ol{margin:3mm 0}
 p{orphans:3;widows:3}
 li{margin:1.5mm 0}
 pre{font:9pt/1.4 Consolas,monospace;white-space:pre-wrap;
  overflow:visible;padding:4mm;break-inside:avoid}
 pre code{white-space:pre-wrap;overflow-wrap:anywhere}
 table{font-size:9pt;line-height:1.4;min-width:0;table-layout:fixed}
 col{width:auto!important}
 th,td{padding:2.5mm}
 tr{break-inside:avoid}
 thead{display:table-header-group}
 .table-wrap{overflow:visible}
 .table-wrap::before{display:none}
 a{color:#1d65b0}
 footer{font-size:9pt}
}
"""


def build_html() -> Path:
    import markdown
    raw = (ROOT / "AUTO_CHAT_AGENT_MASTER_PLAN.md").read_text(encoding="utf-8")
    # Citation syntax vẫn giữ trong Markdown; HTML hiển thị liên kết nguồn đầy đủ.
    raw = re.sub(r"\[\^(https?://[^\]]+)\]",
                 lambda m: " [nguồn](" + m[1] + ")", raw)
    body = markdown.markdown(raw, extensions=["tables", "fenced_code"])
    headings = []
    index = 0
    def mark_heading(match):
        nonlocal index
        index += 1
        label = re.sub("<[^>]+>", "", match[1])
        key = f"section-{index}"
        headings.append((key, label))
        return f'<h2 id="{key}">{match[1]}</h2>'
    body = re.sub(r"<h2>(.*?)</h2>", mark_heading, body, flags=re.S)
    table_widths = [[20, 40, 40], [24, 42, 34], [20, 30, 50],
                    [16, 36, 34, 14], [25, 45, 30], [20, 15, 35, 30]]
    table_index = 0
    def wrap_table(match):
        nonlocal table_index
        widths = table_widths[table_index]
        table_index += 1
        columns = "<colgroup>" + "".join(
            f'<col style="width:{width}%">' for width in widths) + "</colgroup>"
        rendered = match[1].replace("<table>", "<table>" + columns, 1)
        return '<div class="table-wrap">' + rendered + "</div>"
    body = re.sub(r"(<table>.*?</table>)", wrap_table, body, flags=re.S)
    if table_index != len(table_widths):
        raise ValueError("Cập nhật layout weights khi thêm/bớt bảng Master Plan.")
    toc = "".join(f'<li><a href="#{key}">{html.escape(label)}</a></li>'
                  for key, label in headings)
    document = f"""<!doctype html>
<html lang="vi">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auto-Chat Agent — Master Plan V3</title><style>{CSS}</style></head>
<body><main class="page">
<header class="intro"><div class="eyebrow">SPEC • V3.0 • WINDOWS</div>
<h1>Trợ lý chat AI.<br>Cá nhân trước, công khai sau.</h1>
<p>Profile chọn sau · Setting có kiểm soát · Tự chủ theo bằng chứng</p>
<p class="status">13/10/2026 · Đặc tả triển khai — chưa phải sản phẩm đã kiểm chứng.</p></header>
<nav aria-label="Mục lục"><strong>Đọc theo mục</strong><ol>{toc}</ol></nav>
<article>{body}</article>
<footer>Nguồn chuẩn: Master Plan V3 + project.json. Bảng gate là mục tiêu, không phải kết quả đã đạt.</footer>
</main></body></html>"""
    target = ROOT / "Nghiên cứu Auto-Chat Agent.html"
    target.write_text(document, encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    write_json("config.example.json", configuration())
    write_json("profile.template.json", profile_template())
    write_json("profiles.schema.json", schema())
    write_json("model_registry.example.json", {"version": "1.0", "models": []})
    traceability()
    build_markdown()
    html_path = build_html()
    if args.pdf:
        subprocess.run([
            "chromium", "--headless", "--no-sandbox", "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={ROOT / 'Auto-Chat-Agent-Master-Plan-V3.pdf'}",
            html_path.as_uri(),
        ], check=True, capture_output=True, timeout=120)
    print("Đã đồng bộ config/schema, bảng Markdown, README, traceability và HTML"
          + ("/PDF." if args.pdf else "."))


if __name__ == "__main__":
    main()