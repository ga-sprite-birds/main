"""
Edge TTS 引擎
微软 Edge TTS API 实现
"""

from typing import Optional
import edge_tts
from loguru import logger

import config
from .base import BaseTTSEngine
from ga_birds.Utils.retry_utils import tts_retry


class EdgeTTSEngine(BaseTTSEngine):
    """Edge TTS 引擎（API 模式）"""

    def __init__(self):
        """初始化 Edge TTS 引擎"""
        super().__init__()
        
        # 默认配置
        self.default_voice = config.TTS_VOICE
        self.default_rate = config.TTS_RATE
        self.default_volume = config.TTS_VOLUME
        self.default_pitch = config.TTS_PITCH
        
        logger.info(f"Edge TTS 引擎初始化完成，默认音色: {self.default_voice}")

    @tts_retry
    async def generate(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None,
        volume: Optional[float] = None,
        pitch: Optional[int] = None,
    ) -> str:
        """
        使用 Edge TTS 生成音频（带自动重试）

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色（如 zh-CN-YunxiNeural）
            rate: 语速倍数（1.0 = 正常）
            volume: 音量倍数（1.0 = 正常）
            pitch: 音调偏移（Hz，0 = 正常）

        Returns:
            生成的音频文件路径

        Raises:
            Exception: TTS 生成失败（已重试 5 次）
        """
        # 使用传入参数或默认值
        voice = voice or self.default_voice
        rate = rate if rate is not None else self.default_rate
        volume = volume if volume is not None else self.default_volume
        pitch = pitch if pitch is not None else self.default_pitch

        # 确保输出目录存在
        output_file = self._ensure_output_dir(output_path)

        # 记录日志
        self._log_generation_start(output_path, voice, rate, len(text))

        # 创建 TTS 通信对象
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=self._format_rate(rate),
            volume=self._format_volume(volume),
            pitch=self._format_pitch(pitch),
        )

        # 生成音频文件（如果失败会自动重试）
        await communicate.save(str(output_file))

        # 记录完成日志
        self._log_generation_complete(output_path)

        return str(output_file)

    def validate_setup(self) -> bool:
        """
        验证 Edge TTS 设置

        Returns:
            始终返回 True（Edge TTS 是在线服务，无需验证）
        """
        logger.info("✓ Edge TTS 无需验证（在线服务）")
        return True

    @staticmethod
    def _format_rate(rate: float) -> str:
        """
        格式化语速参数为 Edge TTS 格式

        Args:
            rate: 语速倍数（1.0 = 正常）

        Returns:
            Edge TTS 格式的语速字符串（如 "+30%"）
        """
        percent = int((rate - 1.0) * 100)
        return f"{percent:+d}%"

    @staticmethod
    def _format_volume(volume: float) -> str:
        """
        格式化音量参数为 Edge TTS 格式

        Args:
            volume: 音量倍数（1.0 = 正常）

        Returns:
            Edge TTS 格式的音量字符串（如 "+0%"）
        """
        percent = int((volume - 1.0) * 100)
        return f"{percent:+d}%"

    @staticmethod
    def _format_pitch(pitch: int) -> str:
        """
        格式化音调参数为 Edge TTS 格式

        Args:
            pitch: 音调偏移（Hz，0 = 正常）

        Returns:
            Edge TTS 格式的音调字符串（如 "+0Hz"）
        """
        return f"{pitch:+d}Hz"

