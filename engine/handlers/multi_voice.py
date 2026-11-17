"""Multi-character chapter generation for the Core engine."""

from __future__ import annotations

import asyncio
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from engine.store import TaskStore
from system.config import settings

PauseCheck = Callable[[], bool]
CancelCheck = Callable[[], bool]


async def generate_multi_voice_chapters(
    store: TaskStore,
    task: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    chapters: list[dict[str, Any]],
    requested: set[int],
    prosody_mode: str,
    enable_llm: bool,
    llm_manager: Any,
    voice: str | None,
    rate: float | None,
    output_path: str | None,
    source_name: str | None,
    intro_outro_enabled: bool | None = None,
    should_pause: PauseCheck,
    should_cancel: CancelCheck,
) -> dict[str, Any]:
    from ga_birds.Audio import (
        AudioExporter,
        AudioMerger,
        InterjectionMapper,
        TTSManager,
        generate_with_prosody,
        pause_after_text,
        resolve_output_path,
    )
    from ga_birds.Common.chapter_processor import ChapterProcessor
    from ga_birds.Common.text_saver import ChapterTextSaver
    from ga_birds.character_analyzer.dialogue_parser import DialogueParser
    from ga_birds.character_analyzer.voice_assigner import VoiceAssigner

    task_id = task["task_id"]
    options = task["params"].get("generation") or {}
    source_stem = Path(source_name).stem if source_name else task_id
    template_value = options.get("character_template")
    template_path = (
        Path(template_value)
        if template_value
        else settings.CHARACTER_CACHE_DIR / f"{source_stem}_characters.json"
    )
    if not template_path.is_file():
        message = f"Character template not found: {template_path}"
        store.update_task(task_id, status="failed", phase="failed", error=message)
        store.add_event(task_id, "task.failed", {"error": message})
        return {"error": message}

    import json

    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
        characters = template["characters"]
    except (OSError, KeyError, ValueError) as error:
        message = f"Invalid character template: {error}"
        store.update_task(task_id, status="failed", phase="failed", error=message)
        store.add_event(task_id, "task.failed", {"error": message})
        return {"error": message}

    selected_contents = [
        chapter["content"] or ""
        for chapter in chapters
        if int(chapter["chapter_index"]) in requested
    ]
    voice_assigner = await asyncio.to_thread(
        VoiceAssigner, source_text="\n\n".join(selected_contents)
    )
    tts_manager = TTSManager()
    audio_exporter = AudioExporter()
    audio_merger = AudioMerger()
    # Display numbering: front matter = 0, real chapters = 1..N.
    display_indexes = AudioExporter.display_index_map(chapters)

    generated: list[int] = []
    failed: list[dict[str, Any]] = []
    skipped: list[int] = []

    for chapter in chapters:
        chapter_index = int(chapter["chapter_index"])
        if chapter_index not in requested:
            continue
        if should_cancel():
            store.update_task(task_id, status="canceled", phase="canceled", error=None)
            store.add_event(task_id, "task.canceled", {})
            return {"generated": generated, "failed": failed, "canceled": True}
        if should_pause():
            store.update_task(task_id, status="paused", phase="paused")
            store.add_event(task_id, "task.paused", {})
            return {"generated": generated, "failed": failed, "paused": True}
        if chapter["status"] == "succeeded":
            skipped.append(chapter_index)
            continue

        store.update_chapter(
            task_id,
            chapter_index,
            status="running",
            increment_attempts=True,
        )
        try:
            content = chapter["content"] or ""
            original_content = content
            colloquialized_content = None
            if enable_llm and llm_manager:
                try:
                    colloquialized_content = await asyncio.to_thread(
                        llm_manager.colloquialize_text, content
                    )
                    if colloquialized_content:
                        content = colloquialized_content
                except Exception as error:
                    logger.warning(
                        "LLM colloquialization failed for task {} chapter {}: {}",
                        task_id,
                        chapter_index,
                        error,
                    )
                    colloquialized_content = None

            file_index = display_indexes.get(chapter_index, chapter_index)
            if file_index == 0:
                intro, outro = None, None
            else:
                intro, outro = ChapterProcessor.prepare_intro_outro(
                    file_index, chapter["title"], enabled=intro_outro_enabled
                )
            parser = DialogueParser(llm_manager, characters)
            segments = await asyncio.to_thread(
                parser.parse_chapter, content, chapter_index
            )
            segments = DialogueParser.add_intro_outro_to_segments(
                segments, intro, outro
            )
            audio_path = audio_exporter.get_output_path(
                index=file_index,
                title=chapter["title"],
                role="multi",
                custom_base_path=output_path,
                source_name=source_name,
            )
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_path = resolve_output_path(audio_path)
            if resolved_path is None:
                store.update_chapter(
                    task_id,
                    chapter_index,
                    status="succeeded",
                    audio_path=str(audio_path),
                )
                skipped.append(chapter_index)
                continue
            audio_path = resolved_path

            ChapterTextSaver.save_multi_voice_text(
                audio_path=audio_path,
                segments=segments,
                original_content=original_content,
                llm_content=colloquialized_content,
                enable_llm=enable_llm,
            )

            temp_dir = (
                settings.CACHE_DIR
                / "audio_temp"
                / task_id
                / f"chapter_{chapter_index}_{uuid.uuid4().hex}"
            )
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_files: list[str] = []
            try:
                for index, segment in enumerate(segments):
                    speaker = parser.normalize_speaker(segment["speaker"])
                    segment["speaker"] = speaker
                    segment_voice = voice_assigner.get_voice_for_segment(
                        segment, template
                    )
                    tts_params = segment.get("tts_params") or {}
                    temp_audio = temp_dir / f"segment_{index:03d}.mp3"
                    tts_text = InterjectionMapper.process_text_for_tts(
                        segment["text"]
                    )
                    if prosody_mode == "off":
                        await tts_manager.generate_audio(
                            text=tts_text,
                            output_path=str(temp_audio),
                            voice=segment_voice,
                            rate=tts_params.get("rate", rate),
                            volume=tts_params.get("volume"),
                            pitch=tts_params.get("pitch"),
                        )
                    else:
                        await generate_with_prosody(
                            tts_manager=tts_manager,
                            text=tts_text,
                            output_path=str(temp_audio),
                            voice=segment_voice,
                            rate=tts_params.get("rate", rate),
                            volume=tts_params.get("volume"),
                            pitch=tts_params.get("pitch"),
                            mode=prosody_mode,
                        )
                    temp_files.append(str(temp_audio))

                if prosody_mode == "off":
                    merged = await asyncio.to_thread(
                        audio_merger.merge_audio_files,
                        temp_files,
                        str(audio_path),
                    )
                else:
                    pauses = [pause_after_text(item["text"]) for item in segments]
                    if pauses:
                        pauses[-1] = 0
                    merged = await asyncio.to_thread(
                        audio_merger.merge_audio_files_with_pauses,
                        temp_files,
                        str(audio_path),
                        pauses,
                    )
                if not merged:
                    raise RuntimeError("Audio merge failed")
            finally:
                if not snapshot.get("OUTPUT_KEEP_TEMP_FILES", False):
                    await asyncio.to_thread(
                        audio_merger.cleanup_temp_files, temp_files
                    )
                    shutil.rmtree(temp_dir, ignore_errors=True)

            store.update_chapter(
                task_id,
                chapter_index,
                status="succeeded",
                audio_path=str(audio_path),
            )
            generated.append(chapter_index)
        except Exception as error:
            logger.exception(
                "Multi-voice chapter {} failed for task {}",
                chapter_index,
                task_id,
            )
            store.update_chapter(
                task_id,
                chapter_index,
                status="failed",
                error=str(error),
            )
            failed.append({"chapter_index": chapter_index, "error": str(error)})
        store.heartbeat(task_id)

    if should_cancel():
        store.update_task(task_id, status="canceled", phase="canceled", error=None)
        store.add_event(task_id, "task.canceled", {})
        return {"generated": generated, "failed": failed, "canceled": True}
    if should_pause():
        store.update_task(task_id, status="paused", phase="paused")
        store.add_event(task_id, "task.paused", {})
        return {"generated": generated, "failed": failed, "paused": True}

    result = {
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "requested": sorted(requested),
    }
    if failed:
        message = f"{len(failed)} chapter(s) failed"
        store.update_task(
            task_id,
            status="failed",
            phase="failed",
            error=message,
            result=result,
        )
        store.add_event(task_id, "task.failed", {"error": message, **result})
    else:
        store.update_task(
            task_id,
            status="succeeded",
            phase="completed",
            error=None,
            result=result,
        )
        store.add_event(task_id, "task.succeeded", result)
    return result
