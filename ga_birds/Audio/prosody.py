"""
Punctuation-based pauses and lightweight prosody for Edge TTS.

Edge TTS only accepts plain text, so precise pauses are produced by
synthesizing sentence-sized units and inserting silence between them.
The mode is intentionally conservative by default:

  off      - original behaviour (one request per chapter)
  pause    - split at sentence boundaries and insert silence
  prosody  - pause mode plus small rate/pitch/volume changes
"""

import asyncio
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

from loguru import logger

import config
from ga_birds.Common.i18n import t
from .audio_merger import AudioMerger

PROSODY_MODES = ("off", "pause", "prosody")
DEFAULT_MODE = "off"

PAUSE_MS = {
    "ellipsis": 700,
    "question_exclaim": 480,
    "question": 450,
    "exclaim": 450,
    "semicolon": 260,
    "period": 400,
    "dash": 300,
    "comma": 140,
    "none": 180,
}
PARAGRAPH_PAUSE_MS = 300

SENTENCE_RE = re.compile(
    r"[^。！？!?；;…—]+(?:[。！？!?；;]+|…+|—+)?[”’\"』」】）)]*"
)


@dataclass
class SpeechUnit:
    """One independently synthesized speech unit."""

    text: str
    paragraph_end: bool = False
    pause_ms: int = 0


def normalize_prosody_mode(mode: Optional[str] = None) -> str:
    """Return a valid prosody mode, falling back to off."""
    value = str(
        mode if mode is not None else config.TTS_PROSODY_MODE or DEFAULT_MODE
    ).strip().lower()
    return value if value in PROSODY_MODES else DEFAULT_MODE


def _split_long_sentence(sentence: str, max_chars: int) -> List[str]:
    if len(sentence) <= max_chars:
        return [sentence]

    # Prefer commas/colons when a single sentence is too long.
    pieces = re.split(r"(?<=[，,、：:])", sentence)
    units = []
    buffer = ""

    for piece in pieces:
        if not piece:
            continue
        if len(piece) > max_chars:
            if buffer:
                units.append(buffer)
                buffer = ""
            for start in range(0, len(piece), max_chars):
                units.append(piece[start:start + max_chars])
        elif buffer and len(buffer) + len(piece) > max_chars:
            units.append(buffer)
            buffer = piece
        else:
            buffer += piece

    if buffer.strip():
        units.append(buffer)
    return units


def split_units(text: str, max_chars: Optional[int] = None) -> List[SpeechUnit]:
    """Split text into sentence-sized units with a pause after each unit."""
    max_chars = max(1, int(max_chars or config.TTS_PROSODY_MAX_UNIT_CHARS))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: List[SpeechUnit] = []

    for paragraph in paragraphs:
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        sentences = [s.strip() for s in SENTENCE_RE.findall(paragraph) if s.strip()]
        if not sentences:
            sentences = [paragraph]

        paragraph_units: List[str] = []
        for sentence in sentences:
            paragraph_units.extend(_split_long_sentence(sentence, max_chars))

        for index, sentence in enumerate(paragraph_units):
            unit = SpeechUnit(
                text=sentence,
                paragraph_end=index == len(paragraph_units) - 1,
            )
            unit.pause_ms = pause_after(unit)
            units.append(unit)

    return units


def ending_punctuation(text: str) -> str:
    """Classify the final punctuation, ignoring closing quotes/brackets."""
    clean = re.sub(r"[”’\"』」】）)\s]+$", "", text)
    if clean.endswith("……") or clean.endswith("…"):
        return "ellipsis"
    if clean.endswith(("？！", "！？")):
        return "question_exclaim"
    if clean.endswith(("？", "?")):
        return "question"
    if clean.endswith(("！", "!")):
        return "exclaim"
    if clean.endswith(("；", ";")):
        return "semicolon"
    if clean.endswith(("。", ".")):
        return "period"
    if clean.endswith(("——", "—")):
        return "dash"
    if clean.endswith(("，", ",", "、", "：", ":")):
        return "comma"
    return "none"


def pause_after(unit: SpeechUnit) -> int:
    """Return the pause in milliseconds after a unit."""
    pause = PAUSE_MS[ending_punctuation(unit.text)]
    if unit.paragraph_end:
        pause += PARAGRAPH_PAUSE_MS
    return pause


def pause_after_text(text: str, paragraph_end: bool = False) -> int:
    """Convenience wrapper for multi-voice segment boundaries."""
    return pause_after(SpeechUnit(text=text, paragraph_end=paragraph_end))


def style_for(
    unit: SpeechUnit,
    mode: str,
    base_rate: float,
    base_pitch: int,
    base_volume: float,
) -> Tuple[float, int, float]:
    """Return absolute TTS parameters for one unit."""
    rate = base_rate
    pitch = base_pitch
    volume = base_volume

    if mode == "prosody":
        punct = ending_punctuation(unit.text)
        if punct == "question":
            rate -= 0.02
            pitch += 2
        elif punct == "question_exclaim":
            pitch += 2
            volume += 0.05
        elif punct == "exclaim":
            rate += 0.02
            pitch += 1
            volume += 0.05
        elif punct == "ellipsis":
            rate -= 0.03

    rate_delta = float(config.SEGMENT_MAX_RATE_DELTA)
    pitch_delta = int(config.SEGMENT_MAX_PITCH_DELTA)
    volume_delta = float(config.SEGMENT_MAX_VOLUME_DELTA)

    rate = max(base_rate - rate_delta, min(base_rate + rate_delta, rate))
    pitch = max(base_pitch - pitch_delta, min(base_pitch + pitch_delta, pitch))
    volume = max(base_volume - volume_delta, min(base_volume + volume_delta, volume))

    return round(rate, 2), int(pitch), round(volume, 2)


def has_speech(text: str) -> bool:
    """Whether a unit contains anything a TTS engine can speak."""
    return bool(re.search(r"[^\W_]", text, re.UNICODE))


async def generate_with_prosody(
    tts_manager,
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: Optional[float] = None,
    volume: Optional[float] = None,
    pitch: Optional[int] = None,
    mode: Optional[str] = None,
) -> str:
    """Generate audio using the selected prosody mode."""
    mode = normalize_prosody_mode(mode)
    base_rate = config.TTS_RATE if rate is None else rate
    base_volume = config.TTS_VOLUME if volume is None else volume
    base_pitch = config.TTS_PITCH if pitch is None else pitch

    if mode == "off":
        return await tts_manager.generate_audio(
            text=text,
            output_path=output_path,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )

    units = split_units(text)
    if not units:
        return await tts_manager.generate_audio(
            text=text,
            output_path=output_path,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )

    # A single unit needs no silence; still apply the optional tone change.
    if len(units) == 1:
        unit_rate, unit_pitch, unit_volume = style_for(
            units[0], mode, base_rate, base_pitch, base_volume
        )
        return await tts_manager.generate_audio(
            text=text,
            output_path=output_path,
            voice=voice,
            rate=unit_rate,
            volume=unit_volume,
            pitch=unit_pitch,
        )

    logger.info(t("tts.prosody_started", mode=mode, units=len(units)))
    temp_dir = Path("cache/audio_temp") / f"prosody_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_files: List[str] = []
    pauses: List[int] = []

    try:
        for index, unit in enumerate(units):
            if not has_speech(unit.text):
                continue

            unit_path = temp_dir / f"unit_{index:03d}.mp3"
            unit_rate, unit_pitch, unit_volume = style_for(
                unit, mode, base_rate, base_pitch, base_volume
            )
            await tts_manager.generate_audio(
                text=unit.text,
                output_path=str(unit_path),
                voice=voice,
                rate=unit_rate,
                volume=unit_volume,
                pitch=unit_pitch,
            )
            audio_files.append(str(unit_path))
            pauses.append(unit.pause_ms)

        if not audio_files:
            return await tts_manager.generate_audio(
                text=text,
                output_path=output_path,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )

        # Do not add a long tail after the final word.
        pauses[-1] = 0
        merger = AudioMerger()
        # pydub decoding/export is CPU-bound; do not block status requests.
        merged = await asyncio.to_thread(
            merger.merge_audio_files_with_pauses,
            audio_files,
            output_path,
            pauses,
        )
        if not merged:
            raise RuntimeError(t("audio.merge_failed"))

        logger.info(t("tts.prosody_complete", path=output_path))
        return output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
