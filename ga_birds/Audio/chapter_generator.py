"""
GA Sprite Birds - Single-voice chapter generator
Shared by the CLI and the API so both apply the same LLM fallback, intro/outro,
text-saving, duplicate-file handling, and TTS flow.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

import config
from ga_birds.Common.chapter_processor import ChapterProcessor
from ga_birds.Common.i18n import t
from ga_birds.Common.text_saver import ChapterTextSaver
from ga_birds.Utils.file_utils import get_unique_filename
from .prosody import generate_with_prosody


@dataclass
class ChapterAudioResult:
    """Result of one chapter generation."""
    audio_path: Path
    skipped: bool = False


def resolve_output_path(audio_path: Path) -> Optional[Path]:
    """
    Apply the configured duplicate-file policy.

    Returns:
        the path to write, or None when an existing non-empty file should be kept
    """
    if not audio_path.exists():
        return audio_path

    # A zero-byte file is a failed previous attempt, not a duplicate.
    if audio_path.stat().st_size == 0:
        audio_path.unlink(missing_ok=True)
        logger.info(t("api.empty_file_removed", path=audio_path))
        return audio_path

    if config.OUTPUT_DUPLICATE_HANDLING == "skip":
        logger.info(t("api.file_exists_skip", path=audio_path))
        return None

    if config.OUTPUT_DUPLICATE_HANDLING == "rename":
        new_path = get_unique_filename(audio_path)
        logger.info(t("api.file_exists_rename", path=new_path))
        return new_path

    # Overwrite mode can safely reuse the path.
    return audio_path


async def generate_single_voice_chapter(
    *,
    chapter_index: int,
    chapter_title: str,
    content: str,
    output_dir: Optional[str],
    voice: Optional[str],
    rate: Optional[float],
    enable_llm: bool,
    llm_manager,
    tts_manager,
    audio_exporter,
    prosody_mode: Optional[str] = None,
    source_name: Optional[str] = None,
) -> ChapterAudioResult:
    """
    Generate one chapter with a single voice.

    The function handles LLM colloquialization (with fallback), intro/outro,
    chapter-text saving, duplicate-file policy, and the actual TTS call.
    ``prosody_mode`` selects off, pause-only, or pause plus light tone.
    ``source_name`` is used as the per-book output subdirectory.
    """
    original_content = content
    llm_content = None

    if enable_llm and llm_manager:
        logger.info(t("api.chapter_llm_start", index=chapter_index))
        try:
            # LLM clients are synchronous; keep the API event loop responsive.
            llm_content = await asyncio.to_thread(
                llm_manager.colloquialize_text, content
            )
            if llm_content:
                content = llm_content
        except Exception as error:
            logger.error(t("api.chapter_llm_failed", index=chapter_index, error=error))
            logger.warning(t("api.chapter_llm_fallback", index=chapter_index))
            llm_content = None
    elif enable_llm:
        logger.warning(t("api.chapter_llm_fallback", index=chapter_index))

    intro, outro = ChapterProcessor.prepare_intro_outro(chapter_index, chapter_title)
    final_content = ChapterProcessor.combine_content_with_intro_outro(
        content, intro, outro
    )

    audio_path = audio_exporter.get_output_path(
        index=chapter_index,
        title=chapter_title,
        role="default",
        custom_base_path=output_dir,
        source_name=source_name,
    )
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_path = resolve_output_path(audio_path)
    if resolved_path is None:
        return ChapterAudioResult(audio_path=audio_path, skipped=True)

    ChapterTextSaver.save_single_voice_text(
        audio_path=resolved_path,
        final_content=final_content,
        original_content=original_content,
        llm_content=llm_content,
        enable_llm=enable_llm
    )

    logger.info(t("api.chapter_tts_start", index=chapter_index))
    tts_kwargs = {
        "text": final_content,
        "output_path": str(resolved_path),
        "voice": voice,
        "mode": prosody_mode,
    }
    if rate is not None:
        tts_kwargs["rate"] = rate

    await generate_with_prosody(tts_manager=tts_manager, **tts_kwargs)
    logger.info(t("api.chapter_complete", index=chapter_index, path=str(resolved_path)))
    return ChapterAudioResult(audio_path=resolved_path)
