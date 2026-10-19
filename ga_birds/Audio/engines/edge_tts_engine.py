"""
Edge TTS engine
Microsoft Edge TTS API implementation
"""

import os
import uuid
from typing import Optional
import edge_tts
from loguru import logger

import config
from ga_birds.Common.i18n import t
from .base import BaseTTSEngine
from ga_birds.Utils.retry_utils import NonRetryableError, tts_retry


class EdgeTTSEngine(BaseTTSEngine):
    """Edge TTS engine (API mode)"""

    def __init__(self):
        """Initialize the Edge TTS engine"""
        super().__init__()

        # Default configuration
        self.default_voice = config.TTS_VOICE
        self.default_rate = config.TTS_RATE
        self.default_volume = config.TTS_VOLUME
        self.default_pitch = config.TTS_PITCH
        
        logger.info(t("tts.edge_engine_initialized", voice=self.default_voice))

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
        Generate audio using Edge TTS (with automatic retry)

        Args:
            text: text to convert
            output_path: output file path
            voice: voice (e.g. zh-CN-YunxiNeural)
            rate: speech rate multiplier (1.0 = normal)
            volume: volume multiplier (1.0 = normal)
            pitch: pitch offset (Hz, 0 = normal)

        Returns:
            generated audio file path

        Raises:
            Exception: TTS generation failed (retried 5 times)
        """
        if not text or not text.strip():
            raise NonRetryableError(t("tts.empty_text"))

        # Use passed parameters or defaults
        voice = voice or self.default_voice
        rate = rate if rate is not None else self.default_rate
        volume = volume if volume is not None else self.default_volume
        pitch = pitch if pitch is not None else self.default_pitch

        # Ensure output directory exists
        output_file = self._ensure_output_dir(output_path)
        temp_path = output_file.with_name(
            f".{output_file.name}.{uuid.uuid4().hex}.part"
        )

        # Log
        self._log_generation_start(output_path, voice, rate, len(text))

        try:
            # Create TTS communication object
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=self._format_rate(rate),
                volume=self._format_volume(volume),
                pitch=self._format_pitch(pitch),
            )

            # Write to a temporary file first; only publish it when complete
            await communicate.save(str(temp_path))

            if not temp_path.exists() or temp_path.stat().st_size == 0:
                raise RuntimeError(t("tts.empty_audio"))

            os.replace(temp_path, output_file)

            # Log completion
            self._log_generation_complete(output_path)

            return str(output_file)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def validate_setup(self) -> bool:
        """
        Validate Edge TTS setup

        Returns:
            always True (Edge TTS is an online service and requires no validation)
        """
        logger.info(t("tts.setup_valid"))
        return True

    @staticmethod
    def _format_rate(rate: float) -> str:
        """
        Format the speech rate parameter into Edge TTS format

        Args:
            rate: speech rate multiplier (1.0 = normal)

        Returns:
            Edge TTS format rate string (e.g. "+30%")
        """
        percent = int((rate - 1.0) * 100)
        return f"{percent:+d}%"

    @staticmethod
    def _format_volume(volume: float) -> str:
        """
        Format the volume parameter into Edge TTS format

        Args:
            volume: volume multiplier (1.0 = normal)

        Returns:
            Edge TTS format volume string (e.g. "+0%")
        """
        percent = int((volume - 1.0) * 100)
        return f"{percent:+d}%"

    @staticmethod
    def _format_pitch(pitch: int) -> str:
        """
        Format the pitch parameter into Edge TTS format

        Args:
            pitch: pitch offset (Hz, 0 = normal)

        Returns:
            Edge TTS format pitch string (e.g. "+0Hz")
        """
        return f"{pitch:+d}Hz"

