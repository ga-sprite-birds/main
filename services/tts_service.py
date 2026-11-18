"""Edge TTS voice catalog retrieval, TTL caching, and validation."""

import asyncio
import hashlib
import inspect
import json
import logging
import os
import threading
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from system.config import PROJECT_ROOT, settings
from system.db import utc_now_iso

logger = logging.getLogger(__name__)

VoiceList = Sequence[dict[str, Any]]
VoiceFetcher = Callable[[], VoiceList | Awaitable[VoiceList]]

PREVIEW_TEXT_ZH = "你好，我是当前选中的配音员，这是音色试听。"
PREVIEW_TEXT_EN = "Hello, this is a preview of the selected voice."
PREVIEW_TIMEOUT_SECONDS = 25.0


@dataclass(frozen=True)
class VoiceCatalog:
    voices: list[dict[str, Any]]
    available: bool
    warning: str | None = None


class InvalidVoiceError(ValueError):
    """Raised when a known Edge catalog does not contain a ShortName."""


class VoicePreviewError(RuntimeError):
    """Raised when a voice preview cannot be synthesized."""


class TTSVoiceService:
    def __init__(
        self,
        cache_path: str | Path | None = None,
        cache_ttl_seconds: int = 86400,
        fetcher: VoiceFetcher | None = None,
        preview_dir: str | Path | None = None,
        preview_synthesizer: Callable[[str, str], bytes] | None = None,
    ) -> None:
        if cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be greater than zero")
        self._cache_path = (
            Path(cache_path)
            if cache_path
            else settings.TTS_VOICE_CATALOG_CACHE
        )
        self._cache_ttl_seconds = cache_ttl_seconds
        self._fetcher = fetcher
        self._preview_dir = Path(preview_dir) if preview_dir else (
            PROJECT_ROOT / "cache" / "tts" / "preview"
        )
        self._preview_synthesizer = preview_synthesizer
        self._preview_lock = threading.Lock()

    def get_voices(
        self,
        locale: str | None = None,
        gender: str | None = None,
    ) -> VoiceCatalog:
        """Return fresh cached voices, fetching Edge only when necessary."""
        cached = self._read_cache()
        if cached is not None and cached[1]:
            catalog = VoiceCatalog(voices=cached[0], available=True)
            return self._filter(catalog, locale, gender)

        try:
            voices = list(self._fetch_voices())
            self._write_cache(voices)
            catalog = VoiceCatalog(voices=voices, available=True)
        except Exception as exc:
            logger.warning("Unable to fetch Edge TTS voices: %s", exc)
            if cached is not None:
                catalog = VoiceCatalog(
                    voices=cached[0],
                    available=True,
                    warning="config.warning.tts_voices_stale",
                )
            else:
                catalog = VoiceCatalog(
                    voices=[],
                    available=False,
                    warning="config.warning.tts_voices_unavailable",
                )
        return self._filter(catalog, locale, gender)

    def validate_voice(self, short_name: str) -> str | None:
        """Validate ShortName, or allow it with a warning when offline."""
        catalog = self.get_voices()
        if not catalog.available:
            return catalog.warning
        if not any(voice.get("ShortName") == short_name for voice in catalog.voices):
            raise InvalidVoiceError(short_name)
        return catalog.warning

    def synthesize_preview(self, short_name: str, text: str | None = None) -> bytes:
        """Synthesize (and cache) a short audition clip for one voice.

        Preview audio is a stateless service call, not a task: it never touches
        ``tasks.db`` and is safe to serve from the API process.
        """
        voice = (short_name or "").strip()
        if not voice:
            raise InvalidVoiceError(short_name)
        sample = (text or "").strip() or self._preview_text(voice)
        cache_file = self._preview_path(voice, sample)

        cached = self._read_preview(cache_file)
        if cached is not None:
            return cached

        audio = self._synthesize_preview(voice, sample)
        with self._preview_lock:
            self._write_preview(cache_file, audio)
        return audio

    @staticmethod
    def _preview_text(voice: str) -> str:
        return PREVIEW_TEXT_ZH if voice.lower().startswith("zh") else PREVIEW_TEXT_EN

    def _preview_path(self, voice: str, text: str) -> Path:
        digest = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:20]
        return self._preview_dir / f"{digest}.mp3"

    @staticmethod
    def _read_preview(path: Path) -> bytes | None:
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path.read_bytes()
        except OSError:
            return None
        return None

    @staticmethod
    def _write_preview(path: Path, audio: bytes) -> None:
        temporary = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(audio)
            os.replace(temporary, path)
        except OSError as exc:  # 缓存写失败不影响本次试听
            logger.warning("Unable to cache voice preview %s: %s", path, exc)
            temporary.unlink(missing_ok=True)

    def _synthesize_preview(self, voice: str, text: str) -> bytes:
        if self._preview_synthesizer is not None:
            try:
                audio = self._preview_synthesizer(voice, text)
            except InvalidVoiceError:
                raise
            except Exception as exc:
                raise VoicePreviewError(str(exc)) from exc
            if not audio:
                raise VoicePreviewError("empty audio")
            return bytes(audio)

        import edge_tts

        async def collect() -> bytes:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    buffer.extend(chunk["data"])
            return bytes(buffer)

        try:
            audio = asyncio.run(
                asyncio.wait_for(collect(), timeout=PREVIEW_TIMEOUT_SECONDS)
            )
        except Exception as exc:
            logger.warning("Voice preview failed for %s: %s", voice, exc)
            raise VoicePreviewError(str(exc)) from exc
        if not audio:
            raise VoicePreviewError("empty audio")
        return audio

    def _fetch_voices(self) -> VoiceList:
        if self._fetcher is None:
            import edge_tts

            result = edge_tts.list_voices()
        else:
            result = self._fetcher()
        if inspect.isawaitable(result):
            return asyncio.run(result)
        return result

    def _read_cache(self) -> tuple[list[dict[str, Any]], bool] | None:
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            voices = payload["voices"]
            fetched_at = datetime.fromisoformat(
                payload["fetched_at"].replace("Z", "+00:00")
            )
            if not isinstance(voices, list) or not all(
                isinstance(voice, dict) for voice in voices
            ):
                return None
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
            fresh = age <= self._cache_ttl_seconds
            return voices, fresh
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def _write_cache(self, voices: list[dict[str, Any]]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"fetched_at": utc_now_iso(), "voices": voices}
        self._cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _filter(
        catalog: VoiceCatalog,
        locale: str | None,
        gender: str | None,
    ) -> VoiceCatalog:
        voices = catalog.voices
        if locale:
            voices = [
                voice
                for voice in voices
                if str(voice.get("Locale", "")).casefold() == locale.casefold()
            ]
        if gender:
            voices = [
                voice
                for voice in voices
                if str(voice.get("Gender", "")).casefold() == gender.casefold()
            ]
        return VoiceCatalog(
            voices=list(voices),
            available=catalog.available,
            warning=catalog.warning,
        )
