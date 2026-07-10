"""
GA Sprite Birds - TTS Manager
Unified management of TTS calls for local and API modes

Version: v2.0 (modular architecture)
Dev team: Tiger
"""

import asyncio
from typing import Optional
from loguru import logger

import config
from ga_birds.Common.i18n import t
from .engines import (
    BaseTTSEngine,
    EdgeTTSEngine,
)


class TTSManager:
    """TTS manager (unified entry point)"""

    def __init__(self):
        """Initialize the TTS manager"""
        # Normalize to lowercase for case-insensitive support
        self.mode = config.TTS_MODE.lower()
        self.engine_name = config.TTS_ENGINE.lower()

        # Create the TTS engine instance
        self.engine = self._create_engine()

        # Validate engine setup
        if not self.engine.validate_setup():
            raise RuntimeError(t("tts.validate_failed", engine=self.engine_name))

        logger.info(t("tts.manager_initialized", mode=self.mode, engine=self.engine_name))

    def _create_engine(self) -> BaseTTSEngine:
        """
        Create the TTS engine instance

        Returns:
            TTS engine instance

        Raises:
            ValueError: unsupported engine type
        """
        # Engine mapping table
        engine_map = {
            "edge": EdgeTTSEngine,
        }

        # Get the engine class
        engine_class = engine_map.get(self.engine_name.lower())

        if engine_class is None:
            supported = ", ".join(engine_map.keys())
            raise ValueError(
                f"Unsupported TTS engine: {self.engine_name}, "
                f"supported engines: {supported}"
            )

        # Create the engine instance
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
        Generate audio file (unified entry point)

        Args:
            text: text to convert
            output_path: output file path
            voice: voice / speaker (uses configured default if None)
            rate: speech rate multiplier (1.0 = normal; uses configured default if None)
            volume: volume multiplier (1.0 = normal; uses configured default if None)
            pitch: pitch offset (Hz, 0 = normal; uses configured default if None)

        Returns:
            generated audio file path
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
            logger.error(t("tts.generation_failed", error=e))
            raise

    def generate_audio_sync(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[float] = None,
    ) -> str:
        """
        Generate audio synchronously (internally calls the async method)

        Args:
            text: text to convert
            output_path: output file path
            voice: voice / speaker
            rate: speech rate multiplier

        Returns:
            generated audio file path
        """
        return asyncio.run(
            self.generate_audio(
                text=text,
                output_path=output_path,
                voice=voice,
                rate=rate,
            )
        )

