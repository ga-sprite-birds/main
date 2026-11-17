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
LEAD_IN_TITLE = "导读篇"
LEAD_IN_SAMPLE_CHARS = 6000


class ParseError(ValueError):
    """A parse error safe to return to the command client."""


def _has_front_matter(chapters: list[dict[str, Any]]) -> bool:
    from ga_birds.Audio.audio_exporter import AudioExporter

    return any(
        AudioExporter.front_matter_marker(chapter.get("title") or "")
        for chapter in chapters
    )


async def _generate_lead_in(
    chapters: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> str | None:
    """Generate a lead-in chapter with the LLM when the source has none.

    The requested length scales with the source size; the caller decides
    whether to prepend it as chapter ``0``.
    """
    if _has_front_matter(chapters):
        return None

    from ga_birds.LLM import LLMManager

    total_chars = sum(len(chapter.get("content") or "") for chapter in chapters)
    target_chars = min(500, max(80, total_chars // 300))
    sample = "\n\n".join(
        chapter.get("content") or "" for chapter in chapters
    )[:LEAD_IN_SAMPLE_CHARS]
    if not sample.strip():
        return None

    llm = LLMManager()
    language = str(snapshot.get("LANGUAGE", "zh_CN"))
    if language.lower().startswith("en"):
        system_prompt = "You are an audiobook editor who writes engaging lead-ins."
        prompt = f"""Write an English lead-in of about {target_chars} words for the book below.
Requirements:
1. Summarize the theme, core ideas, or story arc.
2. Highlight what makes it worth reading, without spoiling the ending.
3. Natural tone, suitable to open an audiobook.
4. Output only the lead-in text - no title, no bullet points, no explanation.

Book excerpt:
{sample}
"""
    else:
        system_prompt = "你是有声书编辑，擅长撰写吸引人的导读。"
        prompt = f"""请根据下面的书籍内容，写一段约 {target_chars} 字的中文导读。
要求：
1. 概括全书主题、核心观点或故事梗概；
2. 点出主要看点，但不要剧透结局；
3. 语气自然，适合作为有声书的开篇朗读；
4. 直接输出导读正文，不要标题、不要分点、不要任何说明。

书籍内容节选：
{sample}
"""

    result = await asyncio.to_thread(llm.generate, prompt, system_prompt)
    text = (result or "").strip()
    return text or None


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

    if chapters and bool(snapshot.get("CHAPTER_LEAD_IN_ENABLED", False)):
        try:
            lead_in = await _generate_lead_in(chapters, snapshot)
        except Exception as exc:  # LLM unavailable / failed: keep parsing usable
            logger.warning("Lead-in generation skipped for task {}: {}", task_id, exc)
            lead_in = None
        if lead_in:
            chapters = [
                {"index": 0, "title": LEAD_IN_TITLE, "content": lead_in},
                *chapters,
            ]
            logger.info("Generated lead-in chapter for task {}", task_id)

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
