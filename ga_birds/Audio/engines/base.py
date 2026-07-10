"""
TTS engine base class
Defines a unified TTS engine interface
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from loguru import logger
from ga_birds.Common.i18n import t


class BaseTTSEngine(ABC):
    """TTS engine base class"""

    def __init__(self):
        """Initialize the engine"""
        self.engine_name = self.__class__.__name__
        logger.info(t("tts.base_engine_initialized", name=self.engine_name))

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
        Generate audio file

        Args:
            text: text to convert
            output_path: output file path
            voice: voice / speaker (uses configured default if None)
            rate: speech rate multiplier (1.0 = normal, 0.5-2.0; uses configured default if None)
            volume: volume multiplier (1.0 = normal, 0.0-2.0; uses configured default if None)
            pitch: pitch offset (Hz, 0 = normal, -20 to +20; uses configured default if None)

        Returns:
            generated audio file path
        """
        pass

    @abstractmethod
    def validate_setup(self) -> bool:
        """
        Verify whether the engine setup is correct

        Returns:
            True if the setup is valid, otherwise False
        """
        pass

    def _ensure_output_dir(self, output_path: str) -> Path:
        """
        Ensure the output directory exists

        Args:
            output_path: output file path

        Returns:
            Path object
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
        """Log the generation start"""
        logger.info(t("tts.generation_start", path=output_path, voice=voice, rate=rate, length=text_length))

    def _log_generation_complete(self, output_path: str):
        """Log the generation completion"""
        logger.info(t("tts.generation_complete", path=output_path))

