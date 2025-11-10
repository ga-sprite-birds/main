"""
GA Sprite Birds - TTS 管理器
统一管理本地和 API 模式的 TTS 调用

版本: v1.0
开发团队: Tiger
"""

import asyncio
import importlib
from pathlib import Path
from typing import Optional

import edge_tts
from loguru import logger

import config

# 动态导入核心模块
_core_module_name = config.CORE_DIR.replace('-', '_')
_utils_module = importlib.import_module(f'{_core_module_name}.Utils.model_manager')
ModelManager = _utils_module.ModelManager


class TTSManager:
    """TTS 管理器"""

    def __init__(self):
        """初始化 TTS 管理器"""
        self.mode = config.TTS_MODE
        self.model_manager = ModelManager()

        if self.mode == "local":
            # 验证本地 TTS 设置
            if not self.model_manager.validate_local_tts_setup():
                raise RuntimeError("本地 TTS 设置验证失败，请检查配置")

            # 获取设备
            device_type, device_desc = self.model_manager.get_device(
                prefer_gpu=(config.TTS_LOCAL_DEVICE != 'cpu')
            )
            self.device = device_type

            # 本地模式（CosyVoice 等）
            # TODO: 实现本地 TTS 模型加载
            logger.info(f"TTS 模式: 本地, 引擎: {config.TTS_LOCAL_ENGINE}")
            logger.info(f"TTS 设备: {device_desc}")
            raise NotImplementedError("本地 TTS 模式暂未实现，请使用 API 模式")
        elif self.mode == "api":
            logger.info(f"TTS 模式: API (Edge TTS)")
        else:
            raise ValueError(f"不支持的 TTS 模式: {self.mode}")
    
    async def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None
    ) -> str:
        """
        生成音频文件

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色（如果为 None，使用配置中的默认音色）
            rate: 语速（如果为 None，使用配置中的默认语速）

        Returns:
            生成的音频文件路径
        """
        try:
            if self.mode == "local":
                return await self._generate_local(text, output_path, voice)
            else:
                return await self._generate_api(text, output_path, voice, rate)
        except Exception as e:
            logger.error(f"TTS 生成失败: {e}")
            raise
    
    async def _generate_local(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> str:
        """使用本地模型生成音频"""
        # TODO: 实现本地 TTS 生成（CosyVoice 等）
        raise NotImplementedError("本地 TTS 模式暂未实现")
    
    async def _generate_api(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None
    ) -> str:
        """使用 API 生成音频"""
        return await self._generate_edge_tts(text, output_path, voice, rate)

    async def _generate_edge_tts(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None
    ) -> str:
        """使用 Edge TTS 生成音频"""
        voice = voice or config.TTS_VOICE
        rate = rate if rate is not None else config.TTS_RATE

        # 确保输出目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始生成音频: {output_path}, 音色: {voice}, 语速: {rate}, 文本长度: {len(text)} 字符")

        # 创建 TTS 通信对象
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=self._format_rate(rate),
            volume=self._format_volume(config.TTS_VOLUME),
            pitch=self._format_pitch(config.TTS_PITCH)
        )

        # 生成音频文件
        await communicate.save(str(output_file))

        logger.info(f"音频生成完成: {output_path}")
        return str(output_file)
    
    @staticmethod
    def _format_rate(rate: float) -> str:
        """格式化语速参数"""
        # Edge TTS 语速格式: +0% 或 -50%
        percent = int((rate - 1.0) * 100)
        return f"{percent:+d}%"
    
    @staticmethod
    def _format_volume(volume: float) -> str:
        """格式化音量参数"""
        # Edge TTS 音量格式: +0% 或 -50%
        percent = int((volume - 1.0) * 100)
        return f"{percent:+d}%"
    
    @staticmethod
    def _format_pitch(pitch: int) -> str:
        """格式化音调参数"""
        # Edge TTS 音调格式: +0Hz 或 -50Hz
        # pitch 直接表示 Hz 偏移量（0 = 正常，正数 = 提高，负数 = 降低）
        return f"{pitch:+d}Hz"
    
    def generate_audio_sync(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> str:
        """
        同步方式生成音频（内部调用异步方法）
        
        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色
            
        Returns:
            生成的音频文件路径
        """
        return asyncio.run(self.generate_audio(text, output_path, voice))

