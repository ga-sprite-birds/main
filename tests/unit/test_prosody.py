"""
Tests for punctuation-based pauses and lightweight prosody.
"""

import asyncio
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ga_birds.Audio import prosody  # noqa: E402


@pytest.mark.unit
def test_normalize_prosody_mode():
    assert prosody.normalize_prosody_mode("PAUSE") == "pause"
    assert prosody.normalize_prosody_mode(" prosody ") == "prosody"
    assert prosody.normalize_prosody_mode("unknown") == "off"
    assert prosody.normalize_prosody_mode(None) in prosody.PROSODY_MODES


@pytest.mark.unit
def test_split_units_adds_paragraph_pause():
    units = prosody.split_units("第一句。第二句！\n\n第三句？")

    assert [unit.text for unit in units] == ["第一句。", "第二句！", "第三句？"]
    assert units[0].pause_ms == prosody.PAUSE_MS["period"]
    assert units[1].pause_ms == (
        prosody.PAUSE_MS["exclaim"] + prosody.PARAGRAPH_PAUSE_MS
    )
    assert units[2].pause_ms == (
        prosody.PAUSE_MS["question"] + prosody.PARAGRAPH_PAUSE_MS
    )
    assert units[1].paragraph_end is True
    assert units[2].paragraph_end is True


@pytest.mark.unit
def test_split_units_respects_max_chars():
    units = prosody.split_units("这是一个没有标点的很长的句子", max_chars=5)

    assert len(units) > 1
    assert all(len(unit.text) <= 5 for unit in units)


@pytest.mark.unit
def test_ending_punctuation_ignores_closing_quotes():
    assert prosody.ending_punctuation("真的吗？”") == "question"
    assert prosody.ending_punctuation("走吧！」") == "exclaim"
    assert prosody.ending_punctuation("等等……") == "ellipsis"


@pytest.mark.unit
def test_style_for_applies_subtle_changes():
    question = prosody.SpeechUnit(text="真的吗？")
    rate, pitch, volume = prosody.style_for(question, "prosody", 1.0, 0, 1.0)

    assert rate < 1.0
    assert pitch > 0
    assert volume == 1.0

    plain = prosody.SpeechUnit(text="普通一句。")
    assert prosody.style_for(plain, "prosody", 1.0, 0, 1.0) == (1.0, 0, 1.0)
    assert prosody.style_for(question, "pause", 1.0, 0, 1.0) == (1.0, 0, 1.0)


class _FakeTTSManager:
    def __init__(self):
        self.calls = []

    async def generate_audio(self, **kwargs):
        self.calls.append(kwargs)
        Path(kwargs["output_path"]).write_bytes(b"fake")
        return kwargs["output_path"]


class _FakeMerger:
    def __init__(self):
        self.calls = []

    def merge_audio_files_with_pauses(self, audio_files, output_path, pauses_after):
        self.calls.append((audio_files, pauses_after))
        Path(output_path).write_bytes(b"merged")
        return True


@pytest.mark.unit
def test_generate_with_prosody_off_is_unchanged():
    manager = _FakeTTSManager()

    asyncio.run(prosody.generate_with_prosody(
        tts_manager=manager,
        text="普通一句。",
        output_path="/tmp/prosody_off.mp3",
        mode="off",
    ))

    assert len(manager.calls) == 1
    assert manager.calls[0]["text"] == "普通一句。"


@pytest.mark.unit
def test_generate_with_prosody_splits_and_merges(monkeypatch, tmp_path):
    manager = _FakeTTSManager()
    merger = _FakeMerger()
    monkeypatch.setattr(prosody, "AudioMerger", lambda: merger)

    asyncio.run(prosody.generate_with_prosody(
        tts_manager=manager,
        text="你好。世界！",
        output_path=str(tmp_path / "out.mp3"),
        mode="pause",
    ))

    assert [call["text"] for call in manager.calls] == ["你好。", "世界！"]
    assert len(merger.calls) == 1
    assert merger.calls[0][1] == [prosody.PAUSE_MS["period"], 0]
