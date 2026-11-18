"""Unit tests for system configuration and Edge voice validation."""

import json
from pathlib import Path

import pytest

from services.config_service import (
    ConfigService,
    ConfigValidationError,
    UnknownConfigKeyError,
)
from services.tts_service import InvalidVoiceError, TTSVoiceService
from system.config_schema import CONFIG_ITEMS, seed_config_defaults
from system.db import connect_system_db, utc_now_iso

pytestmark = pytest.mark.unit

VOICES = [
    {
        "ShortName": "zh-CN-YunjianNeural",
        "Locale": "zh-CN",
        "Gender": "Male",
        "FriendlyName": "Yunjian",
    },
    {
        "ShortName": "zh-CN-XiaoxiaoNeural",
        "Locale": "zh-CN",
        "Gender": "Female",
        "FriendlyName": "Xiaoxiao",
    },
    {
        "ShortName": "en-US-JennyNeural",
        "Locale": "en-US",
        "Gender": "Female",
        "FriendlyName": "Jenny",
    },
]


def make_service(tmp_path: Path, fetcher=None) -> ConfigService:
    voice_service = TTSVoiceService(
        cache_path=tmp_path / "cache" / "tts" / "voices.json",
        fetcher=fetcher or (lambda: VOICES),
    )
    return ConfigService(
        db_path=tmp_path / "data" / "system.db",
        override_path=tmp_path / "cache" / "config" / "system.json",
        tts_service=voice_service,
    )


def read_overrides(tmp_path: Path) -> dict:
    return json.loads(
        (tmp_path / "cache" / "config" / "system.json").read_text(
            encoding="utf-8"
        )
    )


def test_schema_defaults_are_seeded_without_env_values(tmp_path):
    service = make_service(tmp_path)

    assert service.get("LANGUAGE") == "zh_CN"
    assert service.get("ENABLE_LLM") is False
    assert service.get("LLM_TEMPERATURE") == 0.9
    assert service.get("LLM_MAX_TOKENS") == 2048
    assert service.get("TTS_VOICE") == "zh-CN-YunjianNeural"
    assert service.get("CHAPTER_MIN_LENGTH") == 10
    assert service.get("OUTPUT_BITRATE") == 192
    assert service.get("TTS_PROSODY_MODE") == "off"
    assert service.get("TTS_PROSODY_MAX_UNIT_CHARS") == 120
    assert service.get("OUTPUT_FRONT_MATTER_MARKERS") == ["导读", "前言"]
    assert service.get("SEGMENT_MAX_RATE_DELTA") == 0.25
    assert service.get("VOICE_PREFER_REGION_MATCH") is True
    assert len(service.get("CHAPTER_REGEX_PATTERNS")) == 2

    connection = connect_system_db(tmp_path / "data" / "system.db", readonly=True)
    try:
        rows = connection.execute(
            "SELECT key, value_json FROM config_defaults ORDER BY key LIMIT 1000"
        ).fetchall()
    finally:
        connection.close()
    assert {row["key"] for row in rows} == set(CONFIG_ITEMS)


def test_seed_only_adds_missing_keys_and_preserves_existing_values(tmp_path):
    db_path = tmp_path / "data" / "system.db"
    seed_config_defaults(db_path)
    connection = connect_system_db(db_path)
    try:
        with connection:
            connection.execute(
                """
                UPDATE config_defaults
                SET value_json = ?, updated_at = ?
                WHERE key = ?
                """,
                ("1.3", utc_now_iso(), "TTS_RATE"),
            )
            connection.execute(
                "DELETE FROM config_defaults WHERE key = ?",
                ("LANGUAGE",),
            )
    finally:
        connection.close()

    seed_config_defaults(db_path)
    connection = connect_system_db(db_path, readonly=True)
    try:
        rows = connection.execute(
            """
            SELECT key, value_json
            FROM config_defaults
            WHERE key IN (?, ?)
            ORDER BY key
            LIMIT 2
            """,
            ("LANGUAGE", "TTS_RATE"),
        ).fetchall()
    finally:
        connection.close()
    values = {row["key"]: json.loads(row["value_json"]) for row in rows}
    assert values == {"LANGUAGE": "zh_CN", "TTS_RATE": 1.3}


def test_partial_override_and_hot_update(tmp_path):
    service = make_service(tmp_path)

    result = service.set({"TTS_RATE": 1.25, "LANGUAGE": "en_US"})

    assert result["values"]["TTS_RATE"] == 1.25
    assert service.get("TTS_RATE") == 1.25
    assert service.get("TTS_VOLUME") == 1.0
    assert read_overrides(tmp_path) == {
        "LANGUAGE": "en_US",
        "TTS_RATE": 1.25,
    }

    reloaded = make_service(tmp_path)
    assert reloaded.get("TTS_RATE") == 1.25
    assert reloaded.get("LANGUAGE") == "en_US"


def test_setting_default_removes_override_and_reset_scopes(tmp_path):
    service = make_service(tmp_path)
    service.set({"TTS_RATE": 1.4, "LANGUAGE": "en_US", "TTS_PITCH": 3})

    service.reset("tts")
    assert service.get("TTS_RATE") == 1.0
    assert service.get("TTS_PITCH") == 0
    assert service.get("LANGUAGE") == "en_US"
    assert read_overrides(tmp_path) == {"LANGUAGE": "en_US"}

    service.set({"TTS_RATE": 1.5})
    service.set({"TTS_RATE": 1.0})
    assert read_overrides(tmp_path) == {"LANGUAGE": "en_US"}

    service.set({"TTS_PITCH": 2})
    service.reset_all()
    assert read_overrides(tmp_path) == {}
    assert service.get("LANGUAGE") == "zh_CN"
    assert service.get("TTS_PITCH") == 0


@pytest.mark.parametrize(
    ("key", "value", "expected_code"),
    [
        ("ENABLE_LLM", 1, 1002),
        ("TTS_PITCH", True, 1002),
        ("TTS_RATE", "1.2", 1002),
        ("TTS_RATE", 2.1, 1003),
        ("OUTPUT_STRATEGY", "unknown", 1004),
        ("CHAPTER_REGEX_PATTERNS", ["["], 1007),
        ("CHAPTER_INTRO_TEMPLATE", "{speaker}", 1008),
        ("OUTPUT_FILENAME_TEMPLATE", "{index", 1008),
        ("OUTPUT_FILENAME_TEMPLATE", "../../tasks.db", 1008),
        ("CHAPTER_REGEX_PATTERNS", ["a" * 501], 1007),
        ("OUTPUT_BASE_PATH", "", 1003),
    ],
)
def test_invalid_values_are_rejected_without_partial_writes(
    tmp_path, key, value, expected_code
):
    service = make_service(tmp_path)

    with pytest.raises(ConfigValidationError) as caught:
        service.set({key: value, "LANGUAGE": "en_US"})

    assert caught.value.code == expected_code
    assert service.get("LANGUAGE") == "zh_CN"
    assert not (tmp_path / "cache" / "config" / "system.json").exists()


def test_unknown_key_is_a_clear_business_error(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(UnknownConfigKeyError) as caught:
        service.set({"NOT_A_CONFIG_KEY": 1})
    assert caught.value.code == 1001
    assert caught.value.key == "NOT_A_CONFIG_KEY"


def test_cross_field_validation_uses_the_candidate_configuration(tmp_path):
    service = make_service(tmp_path)

    with pytest.raises(ConfigValidationError) as caught:
        service.set({"LLM_MAX_TOKENS": 8192})
    assert caught.value.code == 1006

    with pytest.raises(ConfigValidationError):
        service.set({"DIALOGUE_CHUNK_SIZE": 100, "DIALOGUE_CHUNK_OVERLAP": 100})

    result = service.set({"LLM_NUM_CTX": 4096, "LLM_MAX_TOKENS": 3000})
    assert result["values"]["LLM_MAX_TOKENS"] == 3000
    assert read_overrides(tmp_path) == {
        "LLM_MAX_TOKENS": 3000,
        "LLM_NUM_CTX": 4096,
    }


def test_voice_validation_uses_fresh_cache_without_network(tmp_path):
    cache_path = tmp_path / "cache" / "tts" / "voices.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(
        json.dumps({"fetched_at": utc_now_iso(), "voices": VOICES}),
        encoding="utf-8",
    )

    def fail_if_called():
        raise AssertionError("fresh cache must avoid network access")

    voices = TTSVoiceService(cache_path=cache_path, fetcher=fail_if_called)
    assert voices.validate_voice("zh-CN-XiaoxiaoNeural") is None
    with pytest.raises(InvalidVoiceError):
        voices.validate_voice("zh-CN-NotRealNeural")

    filtered = voices.get_voices(locale="zh-CN", gender="Female")
    assert [voice["ShortName"] for voice in filtered.voices] == [
        "zh-CN-XiaoxiaoNeural"
    ]


def test_voice_cache_is_written_and_reused(tmp_path):
    calls = []

    def fetch_voices():
        calls.append(True)
        return VOICES

    voices = TTSVoiceService(
        cache_path=tmp_path / "cache" / "tts" / "voices.json",
        fetcher=fetch_voices,
    )
    assert len(voices.get_voices().voices) == 3
    assert len(voices.get_voices().voices) == 3
    assert len(calls) == 1


def test_offline_voice_update_is_allowed_with_warning(tmp_path):
    def offline():
        raise OSError("offline")

    service = make_service(tmp_path, fetcher=offline)

    result = service.set({"TTS_VOICE": "zh-CN-OfflineNeural"})

    assert result["values"]["TTS_VOICE"] == "zh-CN-OfflineNeural"
    assert result["warning"] == "config.warning.tts_voices_unavailable"
    assert service.get("TTS_VOICE") == "zh-CN-OfflineNeural"


def test_second_instance_reloads_override_file(tmp_path):
    """API 进程写覆盖文件后，Core 进程的 ConfigService 实例应自动看到新值。"""
    api_side = make_service(tmp_path)
    core_side = make_service(tmp_path)

    api_side.set({"TTS_RATE": 1.15})
    # 另一个进程（另一个实例）读取时按文件签名判断是否重载。
    assert core_side.get("TTS_RATE") == 1.15
    assert core_side.get_all()["TTS_RATE"] == 1.15

    api_side.reset("tts")
    assert core_side.get("TTS_RATE") == 1.0


def test_corrupt_override_file_keeps_last_known_values(tmp_path):
    api_side = make_service(tmp_path)
    core_side = make_service(tmp_path)
    api_side.set({"TTS_RATE": 1.2})

    (tmp_path / "cache" / "config" / "system.json").write_text(
        "{ not json", encoding="utf-8"
    )

    # 损坏文件不该让读取方崩溃，仍返回上一次成功解析的值。
    assert core_side.get("TTS_RATE") == 1.0
