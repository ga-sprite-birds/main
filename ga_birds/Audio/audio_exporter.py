"""
GA Sprite Birds - 音频导出器
负责音频文件的保存和路径管理

版本: v1.0
开发团队: Tiger
"""

from pathlib import Path
from typing import Optional
from datetime import datetime

from pydub import AudioSegment
from loguru import logger

import config


class AudioExporter:
    """音频导出器"""

    def __init__(self):
        """初始化音频导出器"""
        self.base_path = Path(config.OUTPUT_BASE_PATH)
        self.strategy = config.OUTPUT_STRATEGY
        self.format = config.OUTPUT_FORMAT
        self.bitrate = config.OUTPUT_BITRATE
        self.filename_template = config.OUTPUT_FILENAME_TEMPLATE

        # 确保输出目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"音频导出器初始化完成，输出路径: {self.base_path}, 策略: {self.strategy}")
    
    def get_output_path(
        self,
        index: int,
        title: str,
        role: Optional[str] = None,
        custom_base_path: Optional[str] = None
    ) -> Path:
        """
        获取输出文件路径
        
        Args:
            index: 章节序号
            title: 章节标题
            role: 角色名称
            custom_base_path: 自定义基础路径（API 参数覆盖）
            
        Returns:
            输出文件路径
        """
        # 使用自定义路径或默认路径
        base = Path(custom_base_path) if custom_base_path else self.base_path
        
        # 根据策略确定子目录
        if self.strategy == "by_role":
            subdir = base / (role or "default")
        elif self.strategy == "by_model":
            model_name = config.TTS_LOCAL_ENGINE if config.TTS_MODE == "local" else "edge-tts"
            subdir = base / model_name
        elif self.strategy == "by_date":
            date_str = datetime.now().strftime("%Y%m%d")
            subdir = base / date_str
        else:
            subdir = base
        
        # 确保子目录存在
        subdir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        filename = self.filename_template.format(
            index=index,
            title=self._sanitize_filename(title),
            role=role or "default",
            date=datetime.now().strftime("%Y%m%d"),
            format=self.format
        )
        
        output_path = subdir / filename
        logger.debug(f"生成输出路径: {output_path}")
        
        return output_path
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除或替换非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        max_length = 100
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        return filename
    
    def convert_format(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        target_format: Optional[str] = None,
        bitrate: Optional[int] = None
    ) -> str:
        """
        转换音频格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（如果为 None，则自动生成）
            target_format: 目标格式（如果为 None，使用配置中的格式）
            bitrate: 比特率（如果为 None，使用配置中的比特率）
            
        Returns:
            输出文件路径
        """
        target_format = target_format or self.format
        bitrate = bitrate or self.bitrate
        
        # 如果未指定输出路径，则自动生成
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(input_file.with_suffix(f".{target_format}"))
        
        logger.info(f"开始转换音频格式: {input_path} -> {output_path}")
        
        try:
            # 加载音频
            audio = AudioSegment.from_file(input_path)
            
            # 导出为目标格式
            audio.export(
                output_path,
                format=target_format,
                bitrate=f"{bitrate}k"
            )
            
            logger.info(f"音频格式转换完成: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            raise
    
    def merge_audio_files(
        self,
        input_paths: list[str],
        output_path: str,
        crossfade: int = 0
    ) -> str:
        """
        合并多个音频文件
        
        Args:
            input_paths: 输入文件路径列表
            output_path: 输出文件路径
            crossfade: 交叉淡入淡出时长（毫秒）
            
        Returns:
            输出文件路径
        """
        logger.info(f"开始合并 {len(input_paths)} 个音频文件")
        
        try:
            # 加载第一个音频
            combined = AudioSegment.from_file(input_paths[0])
            
            # 依次合并其他音频
            for path in input_paths[1:]:
                audio = AudioSegment.from_file(path)
                if crossfade > 0:
                    combined = combined.append(audio, crossfade=crossfade)
                else:
                    combined = combined + audio
            
            # 导出合并后的音频
            combined.export(
                output_path,
                format=self.format,
                bitrate=f"{self.bitrate}k"
            )
            
            logger.info(f"音频合并完成: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"音频合并失败: {e}")
            raise

