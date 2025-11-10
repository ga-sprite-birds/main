"""
TTS 引擎基类
定义统一的 TTS 引擎接口
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from loguru import logger


class BaseTTSEngine(ABC):
    """TTS 引擎基类"""

    def __init__(self):
        """初始化引擎"""
        self.engine_name = self.__class__.__name__
        logger.info(f"初始化 TTS 引擎: {self.engine_name}")

    @abstractmethod
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
        生成音频文件

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色/说话人（如果为 None，使用配置中的默认值）
            rate: 语速倍数（1.0 = 正常，0.5-2.0，如果为 None，使用配置中的默认值）
            volume: 音量倍数（1.0 = 正常，0.0-2.0，如果为 None，使用配置中的默认值）
            pitch: 音调偏移（Hz，0 = 正常，-20 到 +20，如果为 None，使用配置中的默认值）

        Returns:
            生成的音频文件路径
        """
        pass

    @abstractmethod
    def validate_setup(self) -> bool:
        """
        验证引擎设置是否正确

        Returns:
            设置有效返回 True，否则返回 False
        """
        pass

    def _ensure_output_dir(self, output_path: str) -> Path:
        """
        确保输出目录存在

        Args:
            output_path: 输出文件路径

        Returns:
            Path 对象
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        return output_file

    def _log_generation_start(
        self,
        output_path: str,
        voice: str,
        rate: float,
        text_length: int
    ):
        """记录生成开始日志"""
        logger.info(
            f"开始生成音频: {output_path}, "
            f"音色: {voice}, "
            f"语速: {rate}, "
            f"文本长度: {text_length} 字符"
        )

    def _log_generation_complete(self, output_path: str):
        """记录生成完成日志"""
        logger.info(f"音频生成完成: {output_path}")

