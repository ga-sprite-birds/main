"""Generation-stage handler; runs inside the Core process only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger

import config
from engine.handlers.lead_in import LEAD_IN_TITLE, generate_lead_in, has_front_matter
from engine.store import TaskStore
from ga_birds.Common.i18n import set_locale
from system.paths import PathSafetyError, validate_output_path

PauseCheck = Callable[[], bool]
CancelCheck = Callable[[], bool]


def _ensure_generation_snapshot(store: TaskStore, task: dict[str, Any]) -> dict[str, Any]:
    """Freeze business config for this task and reuse it on resume."""
    snapshot = task["params"].get("config_snapshot")
    if isinstance(snapshot, dict) and snapshot:
        return snapshot
    snapshot = config.business_config_snapshot()
    params = dict(task["params"])
    params["config_snapshot"] = snapshot
    store.update_task(task["task_id"], params=params)
    return snapshot


def _normalize_prosody(value: Any, snapshot: dict[str, Any]) -> str:
    from ga_birds.Audio import PROSODY_MODES, normalize_prosody_mode

    if value is None:
        snapshot_mode = str(snapshot.get("TTS_PROSODY_MODE", "off")).lower()
        value = snapshot_mode if snapshot_mode in PROSODY_MODES else "off"
    normalized = normalize_prosody_mode(str(value))
    if normalized not in PROSODY_MODES:
        raise ValueError(f"Invalid prosody mode: {value}")
    return normalized


async def run_generation(
    store: TaskStore,
    task_id: str,
    *,
    should_pause: PauseCheck,
    should_cancel: CancelCheck,
) -> dict[str, Any]:
    """Generate selected chapters for a task with chapter-level checkpoints."""
    task = store.require_task(task_id)
    snapshot = _ensure_generation_snapshot(store, task)
    set_locale(str(snapshot.get("LANGUAGE", "zh_CN")))

    with config.use_config_snapshot(snapshot):
        return await _run_with_snapshot(
            store,
            task,
            snapshot,
            should_pause=should_pause,
            should_cancel=should_cancel,
        )


async def _run_with_snapshot(
    store: TaskStore,
    task: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    should_pause: PauseCheck,
    should_cancel: CancelCheck,
) -> dict[str, Any]:
    from ga_birds.Audio import TTSManager
    from ga_birds.Audio.audio_exporter import AudioExporter
    from ga_birds.Audio.chapter_generator import generate_single_voice_chapter

    task_id = task["task_id"]
    params = task["params"]
    options = params.get("generation") or {}
    chapters = store.list_chapters(task_id)
    if not chapters:
        message = "Task has no parsed chapters"
        store.update_task(
            task_id,
            status="failed",
            phase="failed",
            error=message,
        )
        store.add_event(task_id, "task.failed", {"error": message})
        return {"error": message}

    # Optional lead-in chapter (导读). Per-task option overrides the snapshot.
    lead_in_option = options.get("chapter_lead_in_enabled")
    lead_in_enabled = bool(
        snapshot.get("CHAPTER_LEAD_IN_ENABLED", False)
        if lead_in_option is None
        else lead_in_option
    )
    if lead_in_enabled and not has_front_matter(chapters):
        try:
            lead_in_text = await generate_lead_in(
                chapters, str(snapshot.get("LANGUAGE", "zh_CN"))
            )
        except Exception as exc:  # LLM unavailable / failed: keep generating
            logger.warning("Lead-in generation skipped for task {}: {}", task_id, exc)
            lead_in_text = None
        if lead_in_text:
            store.insert_chapter(
                task_id, index=0, title=LEAD_IN_TITLE, content=lead_in_text
            )
            chapters = store.list_chapters(task_id)
            logger.info("Generated lead-in chapter for task {}", task_id)

    selected_indexes = options.get("chapter_indexes")
    available = {int(chapter["chapter_index"]) for chapter in chapters}
    if selected_indexes is not None:
        if not selected_indexes:
            message = "chapter_indexes cannot be empty"
            store.update_task(task_id, status="failed", phase="failed", error=message)
            return {"error": message}
        requested = {int(index) for index in selected_indexes}
        invalid = sorted(requested - available)
        if invalid:
            message = f"Unknown chapter indexes: {invalid}"
            store.update_task(task_id, status="failed", phase="failed", error=message)
            return {"error": message}
    else:
        requested = set(available)

    # Display numbering: front matter = 0, real chapters = 1..N.
    display_indexes = AudioExporter.display_index_map(chapters)

    prosody_mode = _normalize_prosody(options.get("prosody_mode"), snapshot)
    enable_llm = bool(
        snapshot.get("ENABLE_LLM")
        if options.get("enable_llm") is None
        else options.get("enable_llm")
    )
    intro_outro_option = options.get("chapter_intro_outro")
    intro_outro_enabled = bool(
        snapshot.get("CHAPTER_INTRO_OUTRO", True)
        if intro_outro_option is None
        else intro_outro_option
    )
    voice = options.get("voice")
    rate = options.get("rate")
    output_path = options.get("output_path") or params.get("output_path")
    if output_path:
        try:
            output_path = str(
                validate_output_path(
                    output_path,
                    snapshot.get("OUTPUT_BASE_PATH") or config.OUTPUT_BASE_PATH,
                )
            )
        except PathSafetyError as exc:
            message = f"Invalid output path: {exc}"
            store.update_task(
                task_id,
                status="failed",
                phase="failed",
                error=message,
            )
            store.add_event(task_id, "task.failed", {"error": message})
            return {"error": message}
    source_name = params.get("source_name") or params.get("filename")

    llm_manager = None
    if enable_llm or options.get("multi_voice"):
        try:
            from ga_birds.LLM import LLMManager

            llm_manager = LLMManager()
        except Exception as error:
            logger.error("LLM initialization failed for task {}: {}", task_id, error)
            if options.get("multi_voice"):
                message = f"Multi-voice generation requires LLM: {error}"
                store.update_task(
                    task_id,
                    status="failed",
                    phase="failed",
                    error=message,
                )
                return {"error": message}

    if options.get("multi_voice"):
        from engine.handlers.multi_voice import generate_multi_voice_chapters

        return await generate_multi_voice_chapters(
            store,
            task,
            snapshot,
            chapters=chapters,
            requested=requested,
            prosody_mode=prosody_mode,
            enable_llm=enable_llm,
            llm_manager=llm_manager,
            voice=voice,
            rate=rate,
            output_path=output_path,
            source_name=source_name,
            intro_outro_enabled=intro_outro_enabled,
            should_pause=should_pause,
            should_cancel=should_cancel,
        )

    tts_manager = TTSManager()
    audio_exporter = AudioExporter()
    generated: list[int] = []
    failed: list[dict[str, Any]] = []
    skipped: list[int] = []

    for chapter in chapters:
        chapter_index = int(chapter["chapter_index"])
        if chapter_index not in requested:
            continue
        if should_cancel():
            store.update_task(
                task_id,
                status="canceled",
                phase="canceled",
                error=None,
            )
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
        store.heartbeat(task_id)
        try:
            file_index = display_indexes.get(chapter_index, chapter_index)
            result = await generate_single_voice_chapter(
                chapter_index=chapter_index,
                chapter_title=chapter["title"],
                content=chapter["content"] or "",
                output_dir=output_path,
                voice=voice,
                rate=rate,
                enable_llm=enable_llm,
                llm_manager=llm_manager,
                tts_manager=tts_manager,
                audio_exporter=audio_exporter,
                prosody_mode=prosody_mode,
                source_name=source_name,
                display_index=file_index,
                is_front_matter=file_index == 0,
                intro_outro_enabled=intro_outro_enabled,
            )
            store.update_chapter(
                task_id,
                chapter_index,
                status="succeeded",
                audio_path=str(result.audio_path),
            )
            if result.skipped:
                skipped.append(chapter_index)
            else:
                generated.append(chapter_index)
        except Exception as error:
            logger.exception("Chapter {} failed for task {}", chapter_index, task_id)
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
