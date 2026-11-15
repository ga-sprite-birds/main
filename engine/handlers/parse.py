"""Parse-stage handler for audiobook tasks."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger

import config
from engine.store import TaskStore
from ga_birds.Common.i18n import set_locale

SUPPORTED_INPUT_EXTENSIONS = {".txt", ".md", ".pdf"}


class ParseError(ValueError):
    """A parse error safe to return to the command client."""


def _parse_sync(file_path: Path) -> list[dict[str, Any]]:
    from ga_birds.Common.chapter_loader import load_chapters

    chapters = load_chapters(str(file_path))
    return [
        {
            "index": chapter.index,
            "title": chapter.title,
            "content": chapter.content,
        }
        for chapter in chapters
    ]


async def run_parse(store: TaskStore, task_id: str) -> dict[str, Any]:
    """Parse an uploaded book inside the Core process."""
    task = store.require_task(task_id)
    if task["status"] in ("queued", "running"):
        raise ParseError("Task is already queued or running")
    if task["status"] in ("succeeded", "canceled", "removed"):
        raise ParseError(f"Task status {task['status']} cannot be parsed")

    file_path_value = task["params"].get("file_path")
    if not file_path_value:
        raise ParseError("Task has no source file")
    file_path = Path(file_path_value)
    if not file_path.is_file():
        raise ParseError(f"Source file not found: {file_path}")
    if file_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        raise ParseError(f"Unsupported file format: {file_path.suffix}")

    if any(chapter["audio_path"] for chapter in store.list_chapters(task_id)):
        raise ParseError("Task already has generated audio; remove it before re-parsing")

    snapshot = task["params"].get("parse_config_snapshot")
    if not isinstance(snapshot, dict):
        snapshot = config.business_config_snapshot()
        params = dict(task["params"])
        params["parse_config_snapshot"] = snapshot
        store.update_task(task_id, params=params)

    store.update_task(task_id, phase="parsing", error=None)
    set_locale(str(snapshot.get("LANGUAGE", "zh_CN")))

    try:
        with config.use_config_snapshot(snapshot):
            chapters = await asyncio.to_thread(_parse_sync, file_path)
    except Exception as exc:
        store.update_task(
            task_id,
            phase="parse_failed",
            error=str(exc),
        )
        logger.exception("Parse failed for task {}", task_id)
        raise ParseError(str(exc)) from exc

    if not chapters:
        message = "No chapters found in source file"
        store.update_task(task_id, phase="parse_failed", error=message)
        raise ParseError(message)

    store.replace_chapters(task_id, chapters)
    # 重新解析会替换整份章节列表，上一次生成的 chapter_indexes 已不再有效；
    # 清掉它，避免状态视图继续按旧选集计算「本次生成目标」。
    latest_params = dict(store.require_task(task_id)["params"])
    if latest_params.pop("generation", None) is not None:
        store.update_task(task_id, params=latest_params)
    store.update_task(
        task_id,
        phase="ready",
        error=None,
        result={"total_chapters": len(chapters)},
    )
    return {"task_id": task_id, "phase": "ready", "total_chapters": len(chapters)}
