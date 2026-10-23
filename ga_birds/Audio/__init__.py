"""
Audio processing module
Responsible for TTS generation and audio file management
"""

from .tts_manager import TTSManager
from .audio_exporter import AudioExporter
from .audio_merger import AudioMerger
from .interjection_mapper import InterjectionMapper
from .chapter_generator import (
    ChapterAudioResult,
    generate_single_voice_chapter,
    resolve_output_path,
)

__all__ = [
    "TTSManager",
    "AudioExporter",
    "AudioMerger",
    "InterjectionMapper",
    "ChapterAudioResult",
    "generate_single_voice_chapter",
    "resolve_output_path",
]

