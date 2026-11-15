"""Contract tests for the v2 system configuration and TTS routers."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import system_config, tts
from services.config_service import ConfigService
from services.tts_service import TTSVoiceService
from system.deps import get_config_service, get_tts_voice_service

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


@pytest.fixture
def client(tmp_path: Path):
    voice_service = TTSVoiceService(
        cache_path=tmp_path / "cache" / "tts" / "voices.json",
        fetcher=lambda: VOICES,
    )
    config_service = ConfigService(
        db_path=tmp_path / "data" / "system.db",
        override_path=tmp_path / "cache" / "config" / "system.json",
        tts_service=voice_service,
    )
    app = FastAPI()
    app.include_router(system_config.router, prefix="/fcgi-bin/api")
    app.include_router(tts.router, prefix="/fcgi-bin/api")
    app.dependency_overrides[get_config_service] = lambda: config_service
    app.dependency_overrides[get_tts_voice_service] = lambda: voice_service
    with TestClient(app) as test_client:
        yield test_client


def test_get_system_config_returns_grouped_schema(client):
    response = client.get("/fcgi-bin/api/system-config")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "ok"
    sections = body["data"]["sections"]
    tts_section = next(
        section for section in sections if section["section_key"] == "tts"
    )
    voice = next(item for item in tts_section["items"] if item["key"] == "TTS_VOICE")
    assert voice == {
        "key": "TTS_VOICE",
        "label_i18n": "config.item.TTS_VOICE",
        "type": "dynamic-select",
        "value": "zh-CN-YunjianNeural",
        "default": "zh-CN-YunjianNeural",
        "overridden": False,
        "options_source": "edge_voices",
        "min_length": 1,
    }


def test_put_and_reset_use_unified_responses(client):
    put_response = client.put(
        "/fcgi-bin/api/system-config",
        json={"values": {"TTS_RATE": 1.2}},
    )
    assert put_response.status_code == 200
    assert put_response.json()["code"] == 0
    assert put_response.json()["data"]["values"]["TTS_RATE"] == 1.2

    invalid_response = client.put(
        "/fcgi-bin/api/system-config",
        json={"values": {"TTS_RATE": 9}},
    )
    assert invalid_response.status_code == 200
    assert invalid_response.json() == {
        "code": 1003,
        "msg": "config.error.out_of_range",
        "data": {
            "gt": None,
            "ge": 0.5,
            "lt": None,
            "le": 2.0,
            "key": "TTS_RATE",
        },
    }

    reset_response = client.post(
        "/fcgi-bin/api/system-config/reset",
        json={"section": "tts"},
    )
    assert reset_response.json()["code"] == 0
    assert reset_response.json()["data"]["values"]["TTS_RATE"] == 1.0

    reset_all_response = client.post(
        "/fcgi-bin/api/system-config/reset",
        json={"all": True},
    )
    assert reset_all_response.json()["code"] == 0


def test_tts_voices_support_locale_and_gender_filters(client):
    response = client.get(
        "/fcgi-bin/api/tts/voices",
        params={"locale": "zh-CN", "gender": "Female"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["warning"] is None
    assert [voice["ShortName"] for voice in body["data"]["voices"]] == [
        "zh-CN-XiaoxiaoNeural"
    ]


def test_enum_items_expose_translated_options_and_descriptions(client):
    """枚举项要能下发选项译文与说明文案的 i18n key。

    GUI 靠这两个 key 把 off / pause / prosody 这类近似选项翻成中文并解释差别；
    缺少 options_i18n 时前端只能回退显示原始英文值。
    """
    body = client.get("/fcgi-bin/api/system-config").json()
    items = {
        item["key"]: item
        for section in body["data"]["sections"]
        for item in section["items"]
    }

    prosody = items["TTS_PROSODY_MODE"]
    assert prosody["options"] == ["off", "pause", "prosody"]
    assert prosody["options_i18n"] == "config.option.TTS_PROSODY_MODE"
    assert prosody["description_i18n"] == "config.desc.TTS_PROSODY_MODE"
    assert items["TTS_PROSODY_MAX_UNIT_CHARS"]["description_i18n"] == (
        "config.desc.TTS_PROSODY_MAX_UNIT_CHARS"
    )


def test_every_enum_option_has_translation_in_all_languages():
    """所有枚举值都必须有译文，避免中文界面漏出英文原始值。"""
    import json
    from pathlib import Path

    from system.config_schema import CONFIG_SECTIONS

    languages = {
        locale: json.loads(
            (Path("ga_birds") / "Langues" / f"{locale}.json").read_text("utf-8")
        )["config"]
        for locale in ("zh_CN", "en_US")
    }

    missing = []
    for section in CONFIG_SECTIONS:
        for item in section.items:
            if item.value_type != "enum" or not item.options:
                continue
            for locale, config in languages.items():
                labels = config.get("option", {}).get(item.key, {})
                for option in item.options:
                    if not labels.get(option):
                        missing.append(f"{locale}:{item.key}.{option}")

    assert missing == []


def test_preview_failure_is_not_cacheable(client):
    """试听失败响应必须禁缓存，否则同一个 voice URL 会一直回放失败的旧结果。"""
    response = client.get(
        "/fcgi-bin/api/tts/preview",
        params={"voice": "xx-XX-NotAVoice"},
    )

    assert response.headers["cache-control"] == "no-store"
    assert response.json()["code"] == 1000
