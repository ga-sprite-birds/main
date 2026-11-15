"""音色试听合成：缓存、失败与参数校验。"""

import pytest

from services.tts_service import (
    InvalidVoiceError,
    TTSVoiceService,
    VoicePreviewError,
)


def make_service(tmp_path, synthesizer=None):
    return TTSVoiceService(
        cache_path=tmp_path / "voices.json",
        preview_dir=tmp_path / "preview",
        fetcher=lambda: [],
        preview_synthesizer=synthesizer,
    )


@pytest.mark.unit
def test_preview_synthesizes_once_then_hits_cache(tmp_path):
    calls = []

    def synthesizer(voice, text):
        calls.append((voice, text))
        return b"ID3-preview-bytes"

    service = make_service(tmp_path, synthesizer)

    first = service.synthesize_preview("zh-CN-YunxiNeural")
    second = service.synthesize_preview("zh-CN-YunxiNeural")

    assert first == second == b"ID3-preview-bytes"
    # 第二次走磁盘缓存，不再触发网络合成
    assert len(calls) == 1
    assert calls[0][0] == "zh-CN-YunxiNeural"
    assert "你好" in calls[0][1]


@pytest.mark.unit
def test_preview_uses_english_text_for_non_chinese_voice(tmp_path):
    seen = []

    def synthesizer(voice, text):
        seen.append(text)
        return b"audio"

    service = make_service(tmp_path, synthesizer)
    service.synthesize_preview("en-US-JennyNeural")

    assert seen and seen[0].startswith("Hello")


@pytest.mark.unit
def test_preview_wraps_synthesis_failure(tmp_path):
    def synthesizer(voice, text):
        raise RuntimeError("edge unreachable")

    service = make_service(tmp_path, synthesizer)

    with pytest.raises(VoicePreviewError):
        service.synthesize_preview("zh-CN-YunxiNeural")


@pytest.mark.unit
def test_preview_rejects_blank_voice(tmp_path):
    service = make_service(tmp_path, lambda voice, text: b"audio")

    with pytest.raises(InvalidVoiceError):
        service.synthesize_preview("   ")
