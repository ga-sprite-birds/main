"""
TTS 引擎模块
提供统一的 TTS 引擎接口和实现
"""

from .base import BaseTTSEngine
from .edge_tts_engine import EdgeTTSEngine

__all__ = [
    "BaseTTSEngine",
    "EdgeTTSEngine",
]

