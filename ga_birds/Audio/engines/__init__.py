"""
TTS engine module
Provides a unified TTS engine interface and implementations
"""

from .base import BaseTTSEngine
from .edge_tts_engine import EdgeTTSEngine

__all__ = [
    "BaseTTSEngine",
    "EdgeTTSEngine",
]

