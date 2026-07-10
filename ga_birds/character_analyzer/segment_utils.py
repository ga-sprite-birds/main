"""
Segment analysis helpers
Shared language detection and TTS parameter normalization utilities.
"""

import re
from typing import Dict, Optional

import config

try:
    from langdetect import detect as detect_language
except ImportError:  # pragma: no cover - optional dependency
    detect_language = None


LANGUAGE_KEYWORDS = {
    "en": [" the ", " and ", " you ", " was ", " that ", " he ", " she ", " it ", " with ", " but "],
    "de": [" der ", " die ", " und ", " ist ", " nicht ", " ein ", " mit "],
    "fr": [" le ", " la ", " et ", " est ", " une ", " les ", " des ", " que "],
    "es": [" el ", " la ", " y ", " es ", " que ", " los ", " las ", " una "],
    "pt": [" o ", " a ", " e ", " de ", " que ", " os ", " as ", " um ", " uma "],
    "it": [" il ", " la ", " e ", " che ", " non ", " un ", " una ", " per "],
}

LANGUAGE_ALIASES = {
    "english": "en",
    "en-us": "en",
    "en_gb": "en",
    "chinese": "zh",
    "mandarin": "zh",
    "zh-cn": "zh",
    "zh_tw": "zh",
    "japanese": "ja",
    "ja-jp": "ja",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "portuguese": "pt",
    "italian": "it",
}

EMOTION_ALIASES = {
    "neutral": "neutral",
    "平静": "calm",
    "calm": "calm",
    "gentle": "calm",
    "happy": "happy",
    "开心": "happy",
    "joyful": "happy",
    "excited": "excited",
    "激动": "excited",
    "energetic": "excited",
    "sad": "sad",
    "伤心": "sad",
    "melancholic": "sad",
    "angry": "angry",
    "生气": "angry",
    "furious": "angry",
    "nervous": "nervous",
    "紧张": "nervous",
    "anxious": "nervous",
    "serious": "serious",
    "严肃": "serious",
    "stern": "serious",
}

TONE_ALIASES = {
    "narration": "narration",
    "旁白": "narration",
    "dialogue": "dialogue",
    "对话": "dialogue",
    "gentle": "gentle",
    "温和": "gentle",
    "firm": "firm",
    "坚定": "firm",
    "whisper": "whisper",
    "低语": "whisper",
    "shout": "shout",
    "喊叫": "shout",
    "sarcastic": "sarcastic",
    "讽刺": "sarcastic",
}

SEGMENT_TYPE_ALIASES = {
    "dialogue": "dialogue",
    "对话": "dialogue",
    "narration": "narration",
    "旁白": "narration",
    "intro": "intro",
    "片头": "intro",
    "outro": "outro",
    "片尾": "outro",
}

EMOTION_TTS_DELTAS = {
    "neutral": {"rate": 0.0, "pitch": 0, "volume": 0.0},
    "calm": {"rate": -0.05, "pitch": -1, "volume": 0.0},
    "happy": {"rate": 0.06, "pitch": 2, "volume": 0.04},
    "excited": {"rate": 0.12, "pitch": 4, "volume": 0.08},
    "sad": {"rate": -0.10, "pitch": -2, "volume": -0.04},
    "angry": {"rate": 0.10, "pitch": 3, "volume": 0.08},
    "nervous": {"rate": 0.06, "pitch": 2, "volume": -0.02},
    "serious": {"rate": -0.03, "pitch": -1, "volume": 0.0},
}

TONE_TTS_DELTAS = {
    "narration": {"rate": 0.0, "pitch": 0, "volume": 0.0},
    "dialogue": {"rate": 0.0, "pitch": 0, "volume": 0.0},
    "gentle": {"rate": -0.02, "pitch": 1, "volume": -0.02},
    "firm": {"rate": 0.02, "pitch": -1, "volume": 0.02},
    "whisper": {"rate": -0.08, "pitch": -1, "volume": -0.12},
    "shout": {"rate": 0.08, "pitch": 3, "volume": 0.10},
    "sarcastic": {"rate": -0.01, "pitch": 1, "volume": 0.01},
}


class SegmentUtils:
    """Utility helpers for segment-level metadata."""

    @staticmethod
    def extract_locale_from_voice(voice_name: str) -> str:
        parts = str(voice_name).split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        return ""

    @staticmethod
    def extract_language_from_locale(locale: str) -> str:
        if not locale:
            return ""
        normalized = str(locale).replace("_", "-")
        return normalized.split("-")[0].lower()

    @classmethod
    def normalize_language_code(cls, language: Optional[str], fallback: str = "en") -> str:
        if not language:
            return fallback

        normalized = cls.extract_language_from_locale(str(language))
        if normalized:
            return normalized

        lowered = str(language).strip().lower().replace("_", "-")
        return LANGUAGE_ALIASES.get(lowered, lowered or fallback)

    @classmethod
    def heuristic_detect_language(cls, text: str, fallback_language: str = "en") -> str:
        sample = text[:5000]
        if not sample.strip():
            return fallback_language or "en"

        if re.search(r"[\u3040-\u30ff]", sample):
            return "ja"

        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", sample))
        latin_count = len(re.findall(r"[A-Za-z]", sample))
        if cjk_count > max(20, latin_count // 2):
            return "zh"

        lowered = f" {sample.lower()} "
        scores = {
            language: sum(lowered.count(keyword) for keyword in keywords)
            for language, keywords in LANGUAGE_KEYWORDS.items()
        }

        en_score = scores.get("en", 0)
        best_language = "en"
        best_score = en_score

        for language in ("de", "fr", "es", "pt", "it"):
            score = scores.get(language, 0)
            if score > best_score and score > en_score:
                best_language = language
                best_score = score

        if best_score >= 2:
            return best_language

        return "en" if latin_count > 0 else fallback_language or "en"

    @classmethod
    def detect_language(cls, text: str, fallback_language: str = "en") -> str:
        if detect_language and text.strip():
            try:
                return cls.normalize_language_code(detect_language(text[:5000]), fallback=fallback_language)
            except Exception:  # pragma: no cover - optional dependency failures
                pass
        return cls.heuristic_detect_language(text, fallback_language=fallback_language)

    @staticmethod
    def normalize_emotion(emotion: Optional[str]) -> str:
        if not emotion:
            return "neutral"
        key = str(emotion).strip().lower()
        return EMOTION_ALIASES.get(key, "neutral")

    @staticmethod
    def normalize_tone(tone: Optional[str], segment_type: str = "dialogue") -> str:
        if not tone:
            return "narration" if segment_type == "narration" else "dialogue"
        key = str(tone).strip().lower()
        return TONE_ALIASES.get(key, "narration" if segment_type == "narration" else "dialogue")

    @staticmethod
    def normalize_segment_type(segment_type: Optional[str], speaker: str = "narrator") -> str:
        if segment_type:
            key = str(segment_type).strip().lower()
            if key in SEGMENT_TYPE_ALIASES:
                return SEGMENT_TYPE_ALIASES[key]
        return "narration" if speaker == "narrator" else "dialogue"

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    @classmethod
    def normalize_tts_params(
        cls,
        tts_params: Optional[Dict],
        emotion: str = "neutral",
        tone: str = "dialogue",
    ) -> Dict:
        base_rate = float(config.TTS_RATE)
        base_pitch = int(config.TTS_PITCH)
        base_volume = float(config.TTS_VOLUME)

        emotion_delta = EMOTION_TTS_DELTAS.get(emotion, EMOTION_TTS_DELTAS["neutral"])
        tone_delta = TONE_TTS_DELTAS.get(tone, TONE_TTS_DELTAS["dialogue"])

        default_rate = base_rate + emotion_delta["rate"] + tone_delta["rate"]
        default_pitch = base_pitch + emotion_delta["pitch"] + tone_delta["pitch"]
        default_volume = base_volume + emotion_delta["volume"] + tone_delta["volume"]

        raw = tts_params or {}
        rate = raw.get("rate")
        pitch = raw.get("pitch")
        volume = raw.get("volume")

        if rate is None:
            rate = default_rate
        if pitch is None:
            pitch = default_pitch
        if volume is None:
            volume = default_volume

        max_rate_delta = float(config.SEGMENT_MAX_RATE_DELTA)
        max_pitch_delta = int(config.SEGMENT_MAX_PITCH_DELTA)
        max_volume_delta = float(config.SEGMENT_MAX_VOLUME_DELTA)

        rate = cls._clamp(float(rate), max(0.5, base_rate - max_rate_delta), min(2.0, base_rate + max_rate_delta))
        pitch = int(cls._clamp(float(pitch), max(-20, base_pitch - max_pitch_delta), min(20, base_pitch + max_pitch_delta)))
        volume = cls._clamp(float(volume), max(0.0, base_volume - max_volume_delta), min(2.0, base_volume + max_volume_delta))

        return {
            "rate": round(rate, 2),
            "pitch": pitch,
            "volume": round(volume, 2),
        }
