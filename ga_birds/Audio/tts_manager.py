"""
GA Sprite Birds - TTS 管理器
统一管理本地和 API 模式的 TTS 调用

版本: v2.0 (模块化架构)
开发团队: Tiger
"""

import asyncio
from typing import Optional
from loguru import logger

import config
from .engines import (
    BaseTTSEngine,
    EdgeTTSEngine,
)


class TTSManager:
    """TTS 管理器（统一入口）"""

    def __init__(self):
        """初始化 TTS 管理器"""
        # 统一转为小写，支持大小写不敏感
        self.mode = config.TTS_MODE.lower()
        self.engine_name = config.TTS_ENGINE.lower()

        # 创建 TTS 引擎实例
        self.engine = self._create_engine()

        # 验证引擎设置
        if not self.engine.validate_setup():
            raise RuntimeError(f"TTS 引擎 {self.engine_name} 设置验证失败")

        logger.info(f"TTS 管理器初始化完成，模式: {self.mode}, 引擎: {self.engine_name}")

    def _create_engine(self) -> BaseTTSEngine:
        """
        创建 TTS 引擎实例

        Returns:
            TTS 引擎实例

        Raises:
            ValueError: 不支持的引擎类型
        """
        # 引擎映射表
        engine_map = {
            "edge": EdgeTTSEngine,
        }

        # 获取引擎类
        engine_class = engine_map.get(self.engine_name.lower())

        if engine_class is None:
            supported = ", ".join(engine_map.keys())
            raise ValueError(
                f"不支持的 TTS 引擎: {self.engine_name}，"
                f"支持的引擎: {supported}"
            )

        # 创建引擎实例
        return engine_class()

    async def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None,
        volume: Optional[float] = None,
        pitch: Optional[int] = None,
    ) -> str:
        """
        生成音频文件（统一入口）

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色/说话人（如果为 None，使用配置中的默认值）
            rate: 语速倍数（1.0 = 正常，如果为 None，使用配置中的默认值）
            volume: 音量倍数（1.0 = 正常，如果为 None，使用配置中的默认值）
            pitch: 音调偏移（Hz，0 = 正常，如果为 None，使用配置中的默认值）

        Returns:
            生成的音频文件路径
        """
        try:
            return await self.engine.generate(
                text=text,
                output_path=output_path,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )
        except Exception as e:
            logger.error(f"TTS 生成失败: {e}")
            raise

    def generate_audio_sync(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None,
    ) -> str:
        """
        同步方式生成音频（内部调用异步方法）

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色/说话人
            rate: 语速倍数

        Returns:
            生成的音频文件路径
        """
        return asyncio.run(
            self.generate_audio(
                text=text,
                output_path=output_path,
                voice=voice,
                rate=rate,
            )
        )

