"""Code-owned system configuration schema and idempotent SQLite seeding."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from system.db import connect_system_db, utc_now_iso

CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ConfigItemDefinition:
    key: str
    value_type: str
    default: Any
    label_i18n: str
    # 字段说明文案 key（`config.desc.<KEY>`），为空表示该字段不需要说明。
    description_i18n: str | None = None
    # 枚举项文案 key 前缀（`config.option.<KEY>`），前端按 `前缀.<值>` 取译文，
    # 缺失时回退显示原始值，因此未翻译的枚举不会变成空字符串。
    options_i18n: str | None = None
    options: tuple[str, ...] | None = None
    options_source: str | None = None
    recommended_options: tuple[Any, ...] | None = None
    gt: float | None = None
    ge: float | None = None
    lt: float | None = None
    le: float | None = None
    min_length: int | None = None
    template_fields: tuple[str, ...] | None = None
    validate_regex: bool = False
    is_path: bool = False


@dataclass(frozen=True)
class ConfigSectionDefinition:
    section_key: str
    title_i18n: str
    items: tuple[ConfigItemDefinition, ...]


def _item(
    key: str,
    value_type: str,
    default: Any,
    *,
    description: bool = False,
    **metadata: Any,
) -> ConfigItemDefinition:
    """Build one item definition.

    `description=True` 声明该字段在 GUI 中需要一段说明文案，key 固定为
    `config.desc.<KEY>`；枚举项的选项文案 key 前缀固定为 `config.option.<KEY>`。
    """
    if description:
        metadata["description_i18n"] = f"config.desc.{key}"
    if value_type == "enum" and metadata.get("options"):
        metadata["options_i18n"] = f"config.option.{key}"
    return ConfigItemDefinition(
        key=key,
        value_type=value_type,
        default=default,
        label_i18n=f"config.item.{key}",
        **metadata,
    )


CONFIG_SECTIONS: tuple[ConfigSectionDefinition, ...] = (
    ConfigSectionDefinition(
        "language",
        "config.section.language",
        (_item("LANGUAGE", "enum", "zh_CN", options=("en_US", "zh_CN", "ja_JP")),),
    ),
    ConfigSectionDefinition(
        "llm",
        "config.section.llm",
        (
            _item("ENABLE_LLM", "bool", False),
            _item("LLM_TEMPERATURE", "float", 0.9, ge=0.0, le=2.0),
            _item("LLM_MAX_TOKENS", "int", 2048, gt=0),
            _item("LLM_NUM_CTX", "int", 8192, gt=0),
            _item("LLM_TIMEOUT", "int", 600, gt=0),
        ),
    ),
    ConfigSectionDefinition(
        "tts",
        "config.section.tts",
        (
            _item("TTS_ENGINE", "enum", "edge", options=("edge",)),
            _item(
                "TTS_VOICE",
                "dynamic-select",
                "zh-CN-YunjianNeural",
                options_source="edge_voices",
                min_length=1,
            ),
            _item("TTS_RATE", "float", 1.0, ge=0.5, le=2.0),
            _item("TTS_VOLUME", "float", 1.0, ge=0.0, le=2.0),
            _item("TTS_PITCH", "int", 0, ge=-20, le=20),
            _item("TTS_CHUNK_MAX_CHARS", "int", 2000, gt=0),
            _item("TTS_CHUNK_TIMEOUT", "int", 180, gt=0),
            _item(
                "TTS_PROSODY_MODE",
                "enum",
                "off",
                options=("off", "pause", "prosody"),
                description=True,
            ),
            _item("TTS_PROSODY_MAX_UNIT_CHARS", "int", 120, gt=0, description=True),
        ),
    ),
    ConfigSectionDefinition(
        "chapter",
        "config.section.chapter",
        (
            _item("CHAPTER_INTRO_OUTRO", "bool", True),
            _item(
                "CHAPTER_LEAD_IN_ENABLED",
                "bool",
                False,
                description=True,
            ),
            _item(
                "CHAPTER_INTRO_TEMPLATE",
                "string",
                "第{index}章开始",
                template_fields=("index", "title"),
            ),
            _item("CHAPTER_OUTRO_TEMPLATE", "string", "本章播讲完毕"),
            _item("CHAPTER_INTRO_OUTRO_PAUSE", "float", 1.0, ge=0.0),
            _item(
                "CHAPTER_REGEX_PATTERNS",
                "list[str]",
                [
                    r"^第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节](?![\u4e00-\u9fff])",
                    r"^#+\s*第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节](?![\u4e00-\u9fff])",
                ],
                validate_regex=True,
            ),
            _item("CHAPTER_MIN_LENGTH", "int", 10, ge=0),
            _item("CHAPTER_KEEP_TITLE", "bool", True),
            _item("CHAPTER_NORMALIZE_ENABLED", "bool", True),
        ),
    ),
    ConfigSectionDefinition(
        "output",
        "config.section.output",
        (
            _item("OUTPUT_BASE_PATH", "string", "./output", min_length=1, is_path=True),
            _item(
                "OUTPUT_STRATEGY",
                "enum",
                "by_role",
                options=("by_role", "by_model", "by_date"),
                description=True,
            ),
            _item("OUTPUT_FORMAT", "enum", "mp3", options=("mp3", "m4a", "wav")),
            _item(
                "OUTPUT_BITRATE",
                "int",
                192,
                gt=0,
                recommended_options=(128, 192, 320),
            ),
            _item(
                "OUTPUT_FILENAME_TEMPLATE",
                "string",
                "{index:03d}-{title}.{format}",
                template_fields=("index", "title", "role", "date", "format"),
            ),
            _item(
                "OUTPUT_FRONT_MATTER_MARKERS",
                "list[str]",
                ["导读", "前言"],
            ),
            _item("OUTPUT_KEEP_TEMP_FILES", "bool", False),
            _item(
                "OUTPUT_DUPLICATE_HANDLING",
                "enum",
                "rename",
                options=("overwrite", "rename", "skip"),
                description=True,
            ),
            _item("OUTPUT_SAVE_CHAPTER_TEXT", "bool", True),
            _item(
                "OUTPUT_CHAPTER_TEXT_ENCODING",
                "string",
                "utf-8",
                min_length=1,
                recommended_options=("utf-8", "gbk"),
            ),
        ),
    ),
    ConfigSectionDefinition(
        "text_preprocessing",
        "config.section.text_preprocessing",
        (_item("TEXT_PREPROCESSING_ENABLED", "bool", True),),
    ),
    ConfigSectionDefinition(
        "character_analysis",
        "config.section.character_analysis",
        (
            _item("ENABLE_MULTI_VOICE", "bool", True),
            _item(
                "CHARACTER_ANALYSIS_MODE",
                "enum",
                "auto",
                options=("auto", "hybrid"),
                description=True,
            ),
            _item("CHARACTER_MAX_CONTENT_LENGTH", "int", 3000, gt=0),
            _item("DIALOGUE_CHUNK_SIZE", "int", 3000, gt=0),
            _item("DIALOGUE_CHUNK_OVERLAP", "int", 200, ge=0),
            _item("SEGMENT_ENABLE_LANGUAGE_ANALYSIS", "bool", True),
            _item("SEGMENT_ENABLE_EMOTION_ANALYSIS", "bool", True),
            _item("SEGMENT_MAX_RATE_DELTA", "float", 0.25, ge=0.0),
            _item("SEGMENT_MAX_PITCH_DELTA", "int", 8, ge=0),
            _item("SEGMENT_MAX_VOLUME_DELTA", "float", 0.15, ge=0.0),
            _item("VOICE_PREFER_REGION_MATCH", "bool", True),
        ),
    ),
)

CONFIG_ITEMS: dict[str, ConfigItemDefinition] = {
    item.key: item
    for section in CONFIG_SECTIONS
    for item in section.items
}
CONFIG_SECTION_MAP: dict[str, ConfigSectionDefinition] = {
    section.section_key: section for section in CONFIG_SECTIONS
}


def iter_config_items() -> Iterator[tuple[ConfigSectionDefinition, ConfigItemDefinition]]:
    for section in CONFIG_SECTIONS:
        for item in section.items:
            yield section, item


def seed_config_defaults(db_path: str | Path | None = None) -> int:
    """Create the schema and insert only missing default keys."""
    connection = connect_system_db(db_path)
    inserted = 0
    try:
        connection.executescript(
            """
            -- System configuration defaults; values are JSON encoded.
            CREATE TABLE IF NOT EXISTS config_defaults (
              key         TEXT PRIMARY KEY,
              value_json  TEXT NOT NULL,
              updated_at  TEXT NOT NULL
            );

            -- Singleton metadata for the system configuration schema.
            CREATE TABLE IF NOT EXISTS schema_meta (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              config_schema_version INTEGER NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        now = utc_now_iso()
        with connection:
            for _, item in iter_config_items():
                cursor = connection.execute(
                    """
                    INSERT INTO config_defaults (key, value_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO NOTHING
                    """,
                    (
                        item.key,
                        json.dumps(item.default, ensure_ascii=False),
                        now,
                    ),
                )
                inserted += max(cursor.rowcount, 0)
            connection.execute(
                """
                INSERT INTO schema_meta (id, config_schema_version, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  config_schema_version = excluded.config_schema_version,
                  updated_at = excluded.updated_at
                """,
                (CONFIG_SCHEMA_VERSION, now),
            )
        return inserted
    except sqlite3.Error:
        connection.rollback()
        raise
    finally:
        connection.close()
