"""
Test voice catalog loading and caching for voice assignment.
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from ga_birds.character_analyzer.voice_assigner import VoiceAssigner


def test_voice_assigner_loads_cached_catalog(monkeypatch, tmp_path):
    cache_file = tmp_path / "edge_voices.json"
    cache_file.write_text(
        json.dumps(
            {
                "voices": [
                    {"ShortName": "zh-CN-TestMale", "Locale": "zh-CN", "Gender": "Male"},
                    {"ShortName": "zh-CN-TestFemale", "Locale": "zh-CN", "Gender": "Female"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "TTS_VOICE_CATALOG_CACHE", str(cache_file))
    monkeypatch.setattr(config, "TTS_VOICE", "zh-CN-YunxiNeural")
    monkeypatch.setattr(
        "ga_birds.character_analyzer.segment_utils.detect_language",
        None,
    )

    assigner = VoiceAssigner(source_text="这是一个中文测试。")

    assert assigner.MALE_VOICES == ["zh-CN-TestMale"]
    assert assigner.FEMALE_VOICES == ["zh-CN-TestFemale"]


def test_voice_assigner_fetches_and_caches_catalog(monkeypatch, tmp_path):
    cache_file = tmp_path / "edge_voices.json"
    fetched = [
        {"ShortName": "zh-CN-FetchedMale", "Locale": "zh-CN", "Gender": "Male"},
        {"ShortName": "zh-CN-FetchedFemale", "Locale": "zh-CN", "Gender": "Female"},
    ]

    async def fake_list_voices():
        return fetched

    monkeypatch.setattr(config, "TTS_VOICE_CATALOG_CACHE", str(cache_file))
    monkeypatch.setattr(config, "TTS_VOICE", "zh-CN-YunxiNeural")
    monkeypatch.setattr("ga_birds.character_analyzer.voice_assigner.edge_tts.list_voices", fake_list_voices)
    monkeypatch.setattr(
        "ga_birds.character_analyzer.segment_utils.detect_language",
        None,
    )

    assigner = VoiceAssigner(source_text="这是另一个中文测试。")

    assert assigner.voice_catalog == fetched
    assert assigner.MALE_VOICES == ["zh-CN-FetchedMale"]
    assert assigner.FEMALE_VOICES == ["zh-CN-FetchedFemale"]
    assert cache_file.exists()
    assert json.loads(cache_file.read_text(encoding="utf-8"))["voices"] == fetched


def test_voice_assigner_prefers_content_language_over_tts_voice(monkeypatch, tmp_path):
    cache_file = tmp_path / "edge_voices.json"
    cache_file.write_text(
        json.dumps(
            {
                "voices": [
                    {"ShortName": "en-US-GuyNeural", "Locale": "en-US", "Gender": "Male"},
                    {"ShortName": "en-US-JennyNeural", "Locale": "en-US", "Gender": "Female"},
                    {"ShortName": "zh-CN-YunxiNeural", "Locale": "zh-CN", "Gender": "Male"},
                    {"ShortName": "zh-CN-XiaoxiaoNeural", "Locale": "zh-CN", "Gender": "Female"}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "TTS_VOICE_CATALOG_CACHE", str(cache_file))
    monkeypatch.setattr(config, "TTS_VOICE", "zh-CN-YunxiNeural")
    monkeypatch.setattr(
        "ga_birds.character_analyzer.segment_utils.detect_language",
        lambda text: "en",
    )

    assigner = VoiceAssigner(source_text="The boss looked up and saw A and B by the window.")

    assert assigner.MALE_VOICES == ["en-US-GuyNeural"]
    assert assigner.FEMALE_VOICES == ["en-US-JennyNeural"]
    assert assigner.narrator_voice == "en-US-JennyNeural"


def test_voice_assigner_falls_back_to_tts_voice_when_language_pool_missing(monkeypatch, tmp_path):
    cache_file = tmp_path / "edge_voices.json"
    cache_file.write_text(
        json.dumps(
            {
                "voices": [
                    {"ShortName": "zh-CN-YunxiNeural", "Locale": "zh-CN", "Gender": "Male"},
                    {"ShortName": "zh-CN-XiaoxiaoNeural", "Locale": "zh-CN", "Gender": "Female"}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "TTS_VOICE_CATALOG_CACHE", str(cache_file))
    monkeypatch.setattr(config, "TTS_VOICE", "zh-CN-YunxiNeural")
    monkeypatch.setattr(
        "ga_birds.character_analyzer.segment_utils.detect_language",
        lambda text: "en",
    )

    assigner = VoiceAssigner(source_text="The boss looked up and saw A and B by the window.")
    characters = assigner.assign_voices([
        {"name": "boss", "gender": "male"},
        {"name": "A", "gender": "female"},
    ])

    assert characters[0]["voice"] == "zh-CN-YunxiNeural"
    assert characters[1]["voice"] == "zh-CN-YunxiNeural"
    assert assigner.narrator_voice == "zh-CN-YunxiNeural"


def test_voice_assigner_prefers_segment_language_and_manual_preferences(monkeypatch, tmp_path):
    cache_file = tmp_path / "edge_voices.json"
    cache_file.write_text(
        json.dumps(
            {
                "voices": [
                    {"ShortName": "en-US-BrianNeural", "Locale": "en-US", "Gender": "Male"},
                    {"ShortName": "en-US-AvaNeural", "Locale": "en-US", "Gender": "Female"},
                    {"ShortName": "zh-CN-YunxiNeural", "Locale": "zh-CN", "Gender": "Male"},
                    {"ShortName": "zh-CN-XiaoxiaoNeural", "Locale": "zh-CN", "Gender": "Female"}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "TTS_VOICE_CATALOG_CACHE", str(cache_file))
    monkeypatch.setattr(config, "TTS_VOICE", "zh-CN-YunxiNeural")
    monkeypatch.setattr(
        "ga_birds.character_analyzer.segment_utils.detect_language",
        lambda text: "en",
    )

    assigner = VoiceAssigner(source_text="Mixed language content")
    template = {
        "characters": [
            {
                "name": "boss",
                "gender": "male",
                "voice": "en-US-BrianNeural",
                "profile": {
                    "age_group": "adult",
                    "occupation": "manager",
                    "region_hint": "unknown",
                    "accent_preference": "standard",
                    "speech_style": [],
                },
                "voice_preferences": {
                    "default": "en-US-BrianNeural",
                    "by_language": {
                        "zh": "zh-CN-YunxiNeural"
                    },
                },
            }
        ],
        "narrator": {
            "voice": "en-US-AvaNeural",
            "profile": {},
            "voice_preferences": {"default": "en-US-AvaNeural", "by_language": {}},
        },
    }

    zh_segment = {
        "text": "你好，老板。",
        "speaker": "boss",
        "segment_type": "dialogue",
        "language": "zh",
        "voice_override": "",
    }
    en_segment = {
        "text": "I can see you.",
        "speaker": "boss",
        "segment_type": "dialogue",
        "language": "en",
        "voice_override": "",
    }

    assert assigner.get_voice_for_segment(zh_segment, template) == "zh-CN-YunxiNeural"
    assert assigner.get_voice_for_segment(en_segment, template) == "en-US-BrianNeural"
