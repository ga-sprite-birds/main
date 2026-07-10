"""
Audio merger
Merges multiple audio segments into a single complete audio file
"""

import os
from pathlib import Path
from typing import List
from loguru import logger
import config
from ga_birds.Common.i18n import t

if config.FFMPEG_PATH:
    ffmpeg_path = Path(config.FFMPEG_PATH)
    os.environ['PATH'] = str(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')


class AudioMerger:

    def __init__(self):
        self.temp_dir = Path("cache/audio_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if config.FFMPEG_PATH:
            logger.info(t("audio.ffmpeg_path_set", path=config.FFMPEG_PATH))

        logger.info(t("audio.merger_initialized"))
    
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

            logger.info(t("audio.merge_start", count=len(audio_files)))

            # Load the first audio
            combined = AudioSegment.from_file(audio_files[0])

            # Merge the subsequent audio files in sequence
            for i, audio_file in enumerate(audio_files[1:], start=2):
                logger.debug(t("audio.merge_segment", i=i, total=len(audio_files), path=audio_file))
                segment = AudioSegment.from_file(audio_file)
                combined += segment

            # Export merged audio (using configured bitrate)
            output_format = Path(output_path).suffix[1:]  # strip the dot
            bitrate = f"{config.OUTPUT_BITRATE}k"
            combined.export(output_path, format=output_format, bitrate=bitrate)

            logger.debug(t("audio.merge_export_params", format=output_format, bitrate=bitrate))
            logger.info(t("audio.merge_complete", path=output_path))
            return True
            
        except ImportError:
            logger.error(t("tts.pydub_not_installed"))
            return self._merge_with_ffmpeg(audio_files, output_path)
        except Exception as e:
            logger.error(t("audio.merge_failed", error=e))
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

            logger.info(t("audio.merging_with_ffmpeg"))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(t("audio.merge_complete", path=output_path))
            return True

        except subprocess.CalledProcessError as e:
            logger.error(t("audio.ffmpeg_merge_failed", error=e.stderr))
            return False
        except FileNotFoundError:
            logger.error(t("audio.ffmpeg_not_found"))
            if config.FFMPEG_PATH:
                logger.error(t("audio.ffmpeg_configured_path", path=config.FFMPEG_PATH))
            logger.error(t("audio.ffmpeg_check_env"))
            return False
        except Exception as e:
            logger.error(t("audio.merge_failed", error=e))
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
                    logger.debug(t("audio.deleting_temp", path=audio_file))
            except Exception as e:
                logger.warning(t("audio.delete_temp_failed", path=audio_file, error=e))

