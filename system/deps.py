"""FastAPI dependency providers for shared v2 services."""

from functools import lru_cache

from services.config_service import ConfigService
from services.control.service import ControlService
from services.tts_service import TTSVoiceService
from system.config import settings


@lru_cache(maxsize=1)
def get_tts_voice_service() -> TTSVoiceService:
    return TTSVoiceService(cache_path=settings.TTS_VOICE_CATALOG_CACHE)


@lru_cache(maxsize=1)
def get_config_service() -> ConfigService:
    return ConfigService(tts_service=get_tts_voice_service())


@lru_cache(maxsize=1)
def get_control_service() -> ControlService:
    return ControlService()
