"""TTS voice catalog API; mount this router under /fcgi-bin/api."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from services.tts_service import (
    InvalidVoiceError,
    TTSVoiceService,
    VoicePreviewError,
)
from system.deps import get_tts_voice_service
from system.response import fail, success

router = APIRouter(prefix="/tts", tags=["tts"])

# 试听是二进制端点，错误体是 JSON：两者都不能被浏览器/代理缓存。
# 404 属于可启发式缓存的状态码，一旦被缓存，同一 URL 之后即使路由存在也会回放旧 404。
NO_STORE = {"Cache-Control": "no-store"}


@router.get("/voices")
def get_tts_voices(
    locale: str | None = Query(default=None, min_length=1),
    gender: str | None = Query(default=None, min_length=1),
    service: TTSVoiceService = Depends(get_tts_voice_service),
) -> dict:
    catalog = service.get_voices(locale=locale, gender=gender)
    return success({"voices": catalog.voices, "warning": catalog.warning})


@router.get("/preview")
def preview_tts_voice(
    voice: str = Query(min_length=1, max_length=200),
    text: str | None = Query(default=None, max_length=200),
    service: TTSVoiceService = Depends(get_tts_voice_service),
):
    """Return a short audition clip (MP3 bytes) for one Edge voice.

    Binary endpoint: success does not use the ``{code,msg,data}`` envelope,
    failures still return the envelope with a non-zero ``code``.
    """
    try:
        service.validate_voice(voice)  # 明确区分「音色名不存在」和「合成失败」
        audio = service.synthesize_preview(voice, text)
    except InvalidVoiceError:
        return JSONResponse(
            content=fail(1000, "config.error.invalid_voice", {"voice": voice}),
            headers=NO_STORE,
        )
    except VoicePreviewError as exc:
        return JSONResponse(
            content=fail(
                4000,
                "config.error.voice_preview_failed",
                {"voice": voice, "reason": str(exc)[:200]},
            ),
            headers=NO_STORE,
        )

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": 'inline; filename="voice-preview.mp3"',
        },
    )
