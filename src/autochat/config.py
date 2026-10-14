from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_SCHEMA_PATH = Path(__file__).with_name("data") / "profiles.schema.json"
_KNOWN_ROOT = frozenset(
    {
        "$schema",
        "version",
        "global_settings",
        "providers",
        "perception",
        "turn_taking",
        "decision",
        "generation",
        "profiles",
    }
)
_ALIAS_SUFFIX = re.compile(r"(?:^|[-_])(?:latest|preview)$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ProfileConfig:
    id: str
    requested_level: str
    send_method: str

    @classmethod
    def from_dict(cls, value: Any) -> "ProfileConfig":
        if not isinstance(value, dict):
            raise ConfigError("profile: must_be_object")
        profile_id = value.get("id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ConfigError("profiles: nonempty_id_required")
        autonomy = value.get("autonomy") or {}
        send = value.get("send") or {}
        if not isinstance(autonomy, dict) or not isinstance(send, dict):
            raise ConfigError("profile: autonomy_and_send_must_be_objects")
        return cls(
            id=profile_id,
            requested_level=str(autonomy.get("requested_level", "L0")),
            send_method=str(send.get("method", "none_user_types")),
        )


@dataclass(frozen=True)
class ModelRecord:
    provider_id: str
    model_id: str
    verification_status: str
    verified_at: str
    evidence_ref: str
    retired: bool
    tasks: frozenset[str]

    @classmethod
    def from_dict(cls, value: Any) -> "ModelRecord":
        if not isinstance(value, dict):
            raise ConfigError("registry/models: invalid_record")
        provider_id = value.get("provider_id")
        model_id = value.get("model_id")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ConfigError("registry/models: provider_id_required")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ConfigError("registry/models: model_id_required")
        tasks = value.get("tasks", [])
        if not isinstance(tasks, list) or any(
            not isinstance(task, str) or not task.strip() for task in tasks
        ):
            raise ConfigError("registry/models: invalid_tasks")
        retired = value.get("retired", False)
        if type(retired) is not bool:
            raise ConfigError("registry/models: retired_must_be_boolean")
        status = value.get("verification_status", "")
        verified_at = value.get("verified_at", "")
        evidence_ref = value.get("evidence_ref", "")
        return cls(
            provider_id=provider_id,
            model_id=model_id,
            verification_status=status if isinstance(status, str) else "",
            verified_at=verified_at if isinstance(verified_at, str) else "",
            evidence_ref=evidence_ref if isinstance(evidence_ref, str) else "",
            retired=retired,
            tasks=frozenset(tasks),
        )

    def usable_for(self, task: str) -> bool:
        return (
            self.verification_status == "verified"
            and not self.retired
            and bool(self.evidence_ref.strip())
            and bool(self.verified_at.strip())
            and task in self.tasks
        )


@dataclass(frozen=True)
class ModelRegistry:
    records: tuple[ModelRecord, ...]

    @classmethod
    def empty(cls) -> "ModelRegistry":
        return cls(())

    @classmethod
    def from_dict(cls, value: Any) -> "ModelRegistry":
        if not isinstance(value, dict):
            raise ConfigError("registry: must_be_object")
        models = value.get("models", [])
        if not isinstance(models, list):
            raise ConfigError("registry/models: must_be_array")
        records: list[ModelRecord] = []
        seen: set[tuple[str, str]] = set()
        for item in models:
            record = ModelRecord.from_dict(item)
            key = (record.provider_id, record.model_id)
            if key in seen:
                raise ConfigError("registry: duplicate_model")
            seen.add(key)
            records.append(record)
        return cls(tuple(records))

    def find(self, provider_id: str, model_id: str) -> Optional[ModelRecord]:
        for record in self.records:
            if record.provider_id == provider_id and record.model_id == model_id:
                return record
        return None

    def is_verified(self, provider_id: str, model_id: str, task: str) -> bool:
        record = self.find(provider_id, model_id)
        return record is not None and record.usable_for(task)


def is_alias_model_id(model_id: str) -> bool:
    return bool(_ALIAS_SUFFIX.search(model_id.lower()))


@dataclass(frozen=True)
class RuntimeConfig:
    profiles: tuple[ProfileConfig, ...]
    readiness_reasons: tuple[str, ...]

    @classmethod
    def safe_empty(cls) -> "RuntimeConfig":
        return cls(
            profiles=(),
            readiness_reasons=(
                "Chưa có profile thực tế được bật và cấp quyền.",
                "Chưa có generation route/model được verify và bật.",
                "Decision provider/model chưa được verify và bật.",
            ),
        )

    @classmethod
    def from_dict(cls, payload: Any, *, registry: Any = None) -> "RuntimeConfig":
        if not isinstance(payload, dict):
            raise ConfigError("config: must_be_object")
        unknown = set(payload) - _KNOWN_ROOT
        if unknown:
            raise ConfigError(f"config: unknown_root_field:{sorted(unknown)[0]}")
        if payload.get("version") not in ("3.0",):
            raise ConfigError("config: unsupported_version")
        active_generation = payload.get("generation", {}).get("routes", {})
        profiles = payload.get("profiles", [])
        if not isinstance(profiles, list):
            raise ConfigError("profiles: must_be_array")
        _enforce_model_gates(payload, registry)
        return cls(
            profiles=tuple(ProfileConfig.from_dict(item) for item in profiles),
            readiness_reasons=_readiness(payload, active_generation),
        )


def _enforce_model_gates(payload: dict[str, Any], registry: Any) -> None:
    providers = payload.get("providers")
    providers = providers if isinstance(providers, dict) else {}
    generation = payload.get("generation")
    routes = generation.get("routes") if isinstance(generation, dict) else None
    if isinstance(routes, dict):
        for route_id, route in routes.items():
            if isinstance(route, dict) and route.get("enabled"):
                _require_verified_model(
                    providers,
                    registry,
                    route.get("provider_id"),
                    route.get("model_id"),
                    "generation",
                    f"generation/routes/{route_id}",
                )
    decision = payload.get("decision")
    if isinstance(decision, dict) and decision.get("enabled"):
        _require_verified_model(
            providers,
            registry,
            decision.get("provider_id"),
            decision.get("model_id"),
            "decision",
            "decision",
        )


def _require_verified_model(
    providers: dict[str, Any],
    registry: Any,
    provider_id: Any,
    model_id: Any,
    task: str,
    where: str,
) -> None:
    provider = providers.get(provider_id) if isinstance(provider_id, str) else None
    if not isinstance(provider, dict) or provider.get("enabled") is not True:
        raise ConfigError(f"{where}: enabled_provider_required")
    if not isinstance(model_id, str) or not model_id.strip() or is_alias_model_id(model_id):
        raise ConfigError(f"{where}: verified_pinned_model_required")
    if not isinstance(registry, ModelRegistry) or not registry.is_verified(
        provider_id, model_id, task
    ):
        raise ConfigError(f"{where}: model_not_verified_in_registry")


def _readiness(payload: dict[str, Any], routes: Any) -> tuple[str, ...]:
    reasons: list[str] = []
    if not payload.get("profiles"):
        reasons.append("Chưa có profile thực tế được bật và cấp quyền.")
    if isinstance(routes, dict) and not any(
        isinstance(r, dict) and r.get("enabled") for r in routes.values()
    ):
        reasons.append("Chưa có generation route/model được verify và bật.")
    decision = payload.get("decision")
    if not isinstance(decision, dict) or not decision.get("enabled"):
        reasons.append("Decision provider/model chưa được verify và bật.")
    return tuple(reasons)


def load_config(
    path: str | Path | None, *, registry_path: str | Path | None = None
) -> RuntimeConfig:
    if path is None:
        return RuntimeConfig.safe_empty()
    config_path = Path(path)
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError:
        return RuntimeConfig.safe_empty()
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ConfigError("config: invalid_json") from exc
    _validate_against_schema(payload)
    if registry_path is None:
        sibling = config_path.with_name("model_registry.json")
        registry_path = sibling if sibling.is_file() else None
    return RuntimeConfig.from_dict(payload, registry=load_registry(registry_path))


def load_registry(path: str | Path | None = None) -> ModelRegistry:
    if path is None:
        return ModelRegistry.empty()
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return ModelRegistry.empty()
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ConfigError("registry: invalid_json") from exc
    return ModelRegistry.from_dict(payload)


def _validate_against_schema(payload: dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ConfigError("config: schema_validator_unavailable") from exc
    schema_text = _SCHEMA_PATH.read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    validator_class = jsonschema.validators.validator_for(schema)
    validator = validator_class(schema)
    for error in validator.iter_errors(payload):
        location = "/".join(str(part) for part in error.absolute_path)
        raise ConfigError(f"config: schema_{error.validator}@/{location or 'root'}")
