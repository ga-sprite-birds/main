"""
Audio merger
Merges multiple audio segments into a single complete audio file
"""

import os
from pathlib import Path
from typing import List
from loguru import logger
import config

if config.FFMPEG_PATH:
    ffmpeg_path = Path(config.FFMPEG_PATH)
    os.environ['PATH'] = str(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')


class AudioMerger:

    def __init__(self):
        self.temp_dir = Path("cache/audio_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if config.FFMPEG_PATH:
            logger.info(f"  ffmpeg PATH: {config.FFMPEG_PATH}")

        logger.info("Audio merger initialized")
    
    def merge_audio_files(self, audio_files: List[str], output_path: str) -> bool:
        """
        Merge multiple audio files

        Args:
            audio_files: list of audio file paths
            output_path: output file path

        Returns:
            whether successful
        """
        try:
            from pydub import AudioSegment

            logger.info(f"Start merging {len(audio_files)} audio segments")

            # Load the first audio
            combined = AudioSegment.from_file(audio_files[0])

            # Merge the subsequent audio files in sequence
            for i, audio_file in enumerate(audio_files[1:], start=2):
                logger.debug(f"合并片段 {i}/{len(audio_files)}: {audio_file}")
                segment = AudioSegment.from_file(audio_file)
                combined += segment

            # Export merged audio (using configured bitrate)
            output_format = Path(output_path).suffix[1:]  # strip the dot
            bitrate = f"{config.OUTPUT_BITRATE}k"
            combined.export(output_path, format=output_format, bitrate=bitrate)

            logger.debug(f"音频导出参数: format={output_format}, bitrate={bitrate}")
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
        Merge audio using ffmpeg (fallback method)

        Args:
            audio_files: list of audio file paths
            output_path: output file path

        Returns:
            whether successful
        """
        try:
            import subprocess

            # Create file list
            list_file = self.temp_dir / "concat_list.txt"
            with open(list_file, 'w', encoding='utf-8') as f:
                for audio_file in audio_files:
                    # ffmpeg concat requires absolute paths
                    abs_path = Path(audio_file).resolve()
                    f.write(f"file '{abs_path}'\n")

            # Determine ffmpeg path
            if config.FFMPEG_PATH:
                ffmpeg_bin = str(Path(config.FFMPEG_PATH) / 'ffmpeg')
            else:
                ffmpeg_bin = 'ffmpeg'

            # Use ffmpeg concat
            cmd = [
                ffmpeg_bin,
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c', 'copy',
                '-y',
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
            logger.error("ffmpeg 未找到，无法合并音频")
            if config.FFMPEG_PATH:
                logger.error(f"配置的路径: {config.FFMPEG_PATH}")
            logger.error("请检查 .env 中的 FFMPEG_PATH 配置")
            return False
        except Exception as e:
            logger.error(f"音频合并失败: {e}")
            return False
    
    def cleanup_temp_files(self, audio_files: List[str]):
        """
        Clean up temporary audio files

        Args:
            audio_files: list of audio files to delete
        """
        for audio_file in audio_files:
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    logger.debug(f"删除临时文件: {audio_file}")
            except Exception as e:
                logger.warning(f"删除临时文件失败 {audio_file}: {e}")

