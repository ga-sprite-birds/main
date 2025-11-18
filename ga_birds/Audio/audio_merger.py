"""
音频合并器
合并多个音频片段为一个完整的音频文件
"""

import os
from pathlib import Path
from typing import List
from loguru import logger


class AudioMerger:
    """音频合并器"""
    
    def __init__(self):
        """初始化音频合并器"""
        self.temp_dir = Path("cache/audio_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("音频合并器初始化完成")
    
    def merge_audio_files(self, audio_files: List[str], output_path: str) -> bool:
        """
        合并多个音频文件
        
        Args:
            audio_files: 音频文件路径列表
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            from pydub import AudioSegment
            
            logger.info(f"开始合并 {len(audio_files)} 个音频片段")
            
            # 加载第一个音频
            combined = AudioSegment.from_file(audio_files[0])
            
            # 依次合并后续音频
            for i, audio_file in enumerate(audio_files[1:], start=2):
                logger.debug(f"合并片段 {i}/{len(audio_files)}: {audio_file}")
                segment = AudioSegment.from_file(audio_file)
                combined += segment
            
            # 导出合并后的音频
            output_format = Path(output_path).suffix[1:]  # 去掉点号
            combined.export(output_path, format=output_format)
            
            logger.info(f"音频合并完成: {output_path}")
            return True
            
        except ImportError:
            logger.error("pydub 未安装，尝试使用 ffmpeg")
            return self._merge_with_ffmpeg(audio_files, output_path)
        except Exception as e:
            logger.error(f"音频合并失败: {e}")
            return False
    
    def _merge_with_ffmpeg(self, audio_files: List[str], output_path: str) -> bool:
        """
        使用 ffmpeg 合并音频（备用方案）
        
        Args:
            audio_files: 音频文件路径列表
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            import subprocess
            
            # 创建文件列表
            list_file = self.temp_dir / "concat_list.txt"
            with open(list_file, 'w', encoding='utf-8') as f:
                for audio_file in audio_files:
                    # ffmpeg concat 需要绝对路径
                    abs_path = Path(audio_file).resolve()
                    f.write(f"file '{abs_path}'\n")
            
            # 使用 ffmpeg concat
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c', 'copy',
                '-y',  # 覆盖输出文件
                str(output_path)
            ]
            
            logger.info(f"使用 ffmpeg 合并音频")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"音频合并完成: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg 合并失败: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("ffmpeg 未安装，无法合并音频")
            logger.error("请安装 pydub 或 ffmpeg")
            return False
        except Exception as e:
            logger.error(f"音频合并失败: {e}")
            return False
    
    def cleanup_temp_files(self, audio_files: List[str]):
        """
        清理临时音频文件
        
        Args:
            audio_files: 要删除的音频文件列表
        """
        for audio_file in audio_files:
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    logger.debug(f"删除临时文件: {audio_file}")
            except Exception as e:
                logger.warning(f"删除临时文件失败 {audio_file}: {e}")

