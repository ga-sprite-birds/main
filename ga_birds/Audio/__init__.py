"""
Audio processing module
Responsible for TTS generation and audio file management
"""

from .tts_manager import TTSManager
from .audio_exporter import AudioExporter
from .audio_merger import AudioMerger
from .interjection_mapper import InterjectionMapper

__all__ = ["TTSManager", "AudioExporter", "AudioMerger", "InterjectionMapper"]

