"""Three-layer system configuration with strict validation and hot updates."""

import copy
import json
import logging
import math
import os
import re
import string
import tempfile
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from services.tts_service import InvalidVoiceError, TTSVoiceService
from system.config import PROJECT_ROOT
from system.config_schema import (
    CONFIG_ITEMS,
    CONFIG_SECTION_MAP,
    CONFIG_SECTIONS,
    ConfigItemDefinition,
    seed_config_defaults,
)
from system.db import connect_system_db

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """An error safe for routers to translate into a response envelope."""

    def __init__(
        self,
        code: int,
        msg: str,
        *,
        key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg
        self.key = key
        self.details = details or {}


class ConfigValidationError(ConfigError):
    def __init__(
        self,
        key: str,
        msg: str = "config.error.invalid_value",
        code: int = 1000,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, msg, key=key, details=details)


class UnknownConfigKeyError(ConfigValidationError):
    def __init__(self, key: str) -> None:
        super().__init__(key, "config.error.unknown_key", 1001)


class InvalidSectionError(ConfigValidationError):
    def __init__(self, section: str) -> None:
        super().__init__(section, "config.error.invalid_section", 1009)


class ConfigService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        override_path: str | Path | None = None,
        tts_service: TTSVoiceService | None = None,
    ) -> None:
        self._db_path = Path(db_path) if db_path else None
        self._override_path = Path(override_path) if override_path else (
            PROJECT_ROOT / "cache" / "config" / "system.json"
        )
        self._tts_service = tts_service or TTSVoiceService()
        self._lock = threading.RLock()
        self._override_signature: tuple[int, int] | None = None

        seed_config_defaults(self._db_path)
        self._defaults = self._load_defaults()
        self._overrides = self._load_overrides()
        self._override_signature = self._current_signature()
        self._effective = self._merge(self._overrides)

    def get(self, key: str) -> Any:
        with self._lock:
            if key not in CONFIG_ITEMS:
                raise UnknownConfigKeyError(key)
            self._refresh_if_stale()
            return copy.deepcopy(self._effective[key])

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_if_stale()
            return copy.deepcopy(self._effective)

    def get_schema(self) -> list[dict[str, Any]]:
        """Return sections with current values and GUI validation metadata."""
        with self._lock:
            self._refresh_if_stale()
            sections: list[dict[str, Any]] = []
            for section in CONFIG_SECTIONS:
                items: list[dict[str, Any]] = []
                for definition in section.items:
                    item: dict[str, Any] = {
                        "key": definition.key,
                        "label_i18n": definition.label_i18n,
                        "type": definition.value_type,
                        "value": copy.deepcopy(
                            self._effective[definition.key]
                        ),
                        "default": copy.deepcopy(definition.default),
                        "overridden": definition.key in self._overrides,
                    }
                    item.update(self._public_metadata(definition))
                    items.append(item)
                sections.append(
                    {
                        "section_key": section.section_key,
                        "title_i18n": section.title_i18n,
                        "items": items,
                    }
                )
            return sections

    def set(self, values: Mapping[str, Any]) -> dict[str, Any]:
        """Validate and atomically persist a partial override update."""
        with self._lock:
            self._refresh_if_stale()
            validated = {
                key: self._validate_value(key, value)
                for key, value in values.items()
            }
            new_overrides = copy.deepcopy(self._overrides)
            for key, value in validated.items():
                if value == self._defaults[key]:
                    new_overrides.pop(key, None)
                elif value != self._effective[key] or key not in new_overrides:
                    new_overrides[key] = value

            if new_overrides == self._overrides:
                return {"values": self.get_all(), "warning": None}

            candidate = self._merge(new_overrides)
            self._validate_cross_fields(candidate)
            warning = None
            if (
                "TTS_VOICE" in validated
                and candidate["TTS_VOICE"] != self._effective["TTS_VOICE"]
            ):
                try:
                    warning = self._tts_service.validate_voice(
                        candidate["TTS_VOICE"]
                    )
                except InvalidVoiceError as exc:
                    raise ConfigValidationError(
                        "TTS_VOICE",
                        "config.error.invalid_voice",
                        1005,
                        {"value": candidate["TTS_VOICE"]},
                    ) from exc

            self._write_overrides(new_overrides)
            self._overrides = new_overrides
            self._effective = candidate
            return {"values": self.get_all(), "warning": warning}

    def reset(self, section: str) -> dict[str, Any]:
        with self._lock:
            if section not in CONFIG_SECTION_MAP:
                raise InvalidSectionError(section)
            self._refresh_if_stale()
            section_keys = {
                item.key for item in CONFIG_SECTION_MAP[section].items
            }
            new_overrides = {
                key: value
                for key, value in self._overrides.items()
                if key not in section_keys
            }
            if new_overrides != self._overrides:
                self._write_overrides(new_overrides)
                self._overrides = new_overrides
                self._effective = self._merge(new_overrides)
            return {"values": self.get_all(), "warning": None}

    def reset_all(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_if_stale()
            if self._overrides:
                self._write_overrides({})
                self._overrides = {}
                self._effective = self._merge({})
            return {"values": self.get_all(), "warning": None}

    def _load_defaults(self) -> dict[str, Any]:
        connection = connect_system_db(self._db_path, readonly=True)
        try:
            rows = connection.execute(
                """
                SELECT key, value_json
                FROM config_defaults
                ORDER BY key
                LIMIT 1000
                """
            ).fetchall()
        finally:
            connection.close()

        defaults: dict[str, Any] = {}
        for row in rows:
            key = row["key"]
            if key not in CONFIG_ITEMS:
                continue
            try:
                defaults[key] = json.loads(row["value_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ConfigError(
                    4000,
                    "config.error.invalid_default",
                    key=key,
                ) from exc
        missing = set(CONFIG_ITEMS) - set(defaults)
        if missing:
            raise ConfigError(
                4000,
                "config.error.missing_default",
                details={"keys": sorted(missing)},
            )
        return defaults

    def _load_overrides(self) -> dict[str, Any]:
        if not self._override_path.exists():
            return {}
        try:
            payload = json.loads(self._override_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(4000, "config.error.invalid_override_file") from exc
        if not isinstance(payload, dict):
            raise ConfigError(4000, "config.error.invalid_override_file")

        overrides = {
            key: self._validate_value(key, value)
            for key, value in payload.items()
        }
        self._validate_cross_fields(self._merge(overrides))
        return overrides

    def _current_signature(self) -> tuple[int, int] | None:
        """Identify the override file version so other processes' writes are seen."""
        try:
            stat = self._override_path.stat()
        except OSError:
            return None
        return (stat.st_mtime_ns, stat.st_size)

    def _refresh_if_stale(self) -> None:
        """Reload the override file when another process (API or Core) rewrote it."""
        signature = self._current_signature()
        if signature == self._override_signature:
            return
        try:
            overrides = self._load_overrides()
        except ConfigError as exc:
            # 外部写入的文件损坏时保留内存中的旧值，避免整个配置接口不可用。
            logger.warning("system.json 重载失败，继续使用旧配置：%s", exc.msg)
            self._override_signature = signature
            return
        self._overrides = overrides
        self._override_signature = signature
        self._effective = self._merge(overrides)

    def _merge(self, overrides: Mapping[str, Any]) -> dict[str, Any]:
        effective = copy.deepcopy(self._defaults)
        effective.update(copy.deepcopy(dict(overrides)))
        return {key: effective[key] for key in CONFIG_ITEMS}

    def _validate_value(self, key: str, value: Any) -> Any:
        if key not in CONFIG_ITEMS:
            raise UnknownConfigKeyError(key)
        definition = CONFIG_ITEMS[key]
        value_type = definition.value_type

        if value_type == "bool":
            if type(value) is not bool:
                self._raise_type(key, "bool")
            return value
        if value_type == "int":
            if type(value) is not int:
                self._raise_type(key, "int")
        elif value_type == "float":
            if type(value) not in (int, float):
                self._raise_type(key, "float")
            value = float(value)
            if not math.isfinite(value):
                self._raise_type(key, "finite float")
        elif value_type in ("string", "enum", "dynamic-select"):
            if type(value) is not str:
                self._raise_type(key, "string")
        elif value_type == "list[str]":
            if type(value) is not list or not all(
                type(item) is str for item in value
            ):
                self._raise_type(key, "list[str]")
        else:
            raise ConfigError(4000, "config.error.unknown_schema_type", key=key)

        if definition.options is not None and value not in definition.options:
            raise ConfigValidationError(
                key,
                "config.error.invalid_enum",
                1004,
                {"allowed": list(definition.options)},
            )
        if definition.gt is not None and not value > definition.gt:
            self._raise_range(key, definition)
        if definition.ge is not None and not value >= definition.ge:
            self._raise_range(key, definition)
        if definition.lt is not None and not value < definition.lt:
            self._raise_range(key, definition)
        if definition.le is not None and not value <= definition.le:
            self._raise_range(key, definition)
        if definition.min_length is not None and len(value) < definition.min_length:
            raise ConfigValidationError(
                key,
                "config.error.invalid_length",
                1003,
                {"min_length": definition.min_length},
            )
        if definition.is_path and (not value.strip() or "\0" in value):
            raise ConfigValidationError(key, "config.error.invalid_path", 1003)
        if definition.validate_regex:
            for pattern in value:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise ConfigValidationError(
                        key,
                        "config.error.invalid_regex",
                        1007,
                        {"pattern": pattern, "error": str(exc)},
                    ) from exc
        if definition.template_fields is not None:
            self._validate_template(key, value, definition.template_fields)
        return copy.deepcopy(value)

    @staticmethod
    def _validate_template(
        key: str,
        value: str,
        allowed_fields: tuple[str, ...],
    ) -> None:
        try:
            fields = [
                field_name
                for _, field_name, _, _ in string.Formatter().parse(value)
                if field_name is not None
            ]
        except ValueError as exc:
            raise ConfigValidationError(
                key, "config.error.invalid_template", 1008
            ) from exc
        if any(field not in allowed_fields for field in fields):
            raise ConfigValidationError(
                key,
                "config.error.invalid_template",
                1008,
                {"allowed_fields": list(allowed_fields)},
            )

    @staticmethod
    def _validate_cross_fields(values: Mapping[str, Any]) -> None:
        if values["LLM_MAX_TOKENS"] >= values["LLM_NUM_CTX"]:
            raise ConfigValidationError(
                "LLM_MAX_TOKENS",
                "config.error.llm_tokens_context",
                1006,
            )
        if values["DIALOGUE_CHUNK_OVERLAP"] >= values["DIALOGUE_CHUNK_SIZE"]:
            raise ConfigValidationError(
                "DIALOGUE_CHUNK_OVERLAP",
                "config.error.dialogue_overlap_size",
                1006,
            )

    @staticmethod
    def _raise_type(key: str, expected: str) -> None:
        raise ConfigValidationError(
            key,
            "config.error.invalid_type",
            1002,
            {"expected": expected},
        )

    @staticmethod
    def _raise_range(key: str, definition: ConfigItemDefinition) -> None:
        raise ConfigValidationError(
            key,
            "config.error.out_of_range",
            1003,
            {
                "gt": definition.gt,
                "ge": definition.ge,
                "lt": definition.lt,
                "le": definition.le,
            },
        )

    @staticmethod
    def _public_metadata(definition: ConfigItemDefinition) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for field in (
            "description_i18n",
            "options_i18n",
            "options",
            "options_source",
            "recommended_options",
            "gt",
            "ge",
            "lt",
            "le",
            "min_length",
            "template_fields",
        ):
            value = getattr(definition, field)
            if value is not None:
                metadata[field] = list(value) if isinstance(value, tuple) else value
        if definition.validate_regex:
            metadata["validate_regex"] = True
        if definition.is_path:
            metadata["is_path"] = True
        return metadata

    def _write_overrides(self, overrides: Mapping[str, Any]) -> None:
        ordered = {
            key: copy.deepcopy(overrides[key])
            for key in CONFIG_ITEMS
            if key in overrides
        }
        temporary_path: Path | None = None
        try:
            self._override_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._override_path.parent,
                prefix=f"{self._override_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(ordered, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self._override_path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise ConfigError(4000, "config.error.override_write_failed") from exc
        # 记录自己的写入版本，避免下一次读取把刚写完的文件再解析一遍。
        self._override_signature = self._current_signature()
