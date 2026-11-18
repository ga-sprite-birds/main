"""Shared task response serialization."""

from __future__ import annotations

from typing import Any, Mapping


def task_view(
    task: Mapping[str, Any],
    chapters: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    total = int(task.get("total_chapters") or 0)
    completed = int(task.get("completed_chapters") or 0)

    # 一次生成可以只跑勾选的部分章节（params.generation.chapter_indexes）。
    # 此时「进度」必须相对于本次目标章节计算，否则选了 23 章、全书 31 章时，
    # 跑完也只有 23/31，和用户的预期对不上。target_* 字段表达本次生成的范围，
    # total_chapters / completed_chapters 仍保留全书口径。
    params = task.get("params") or {}
    generation = params.get("generation") or {}
    selected_raw = generation.get("chapter_indexes")
    selected: set[int] | None = None
    if isinstance(selected_raw, (list, tuple, set)) and selected_raw:
        selected = {int(index) for index in selected_raw}

    target = len(selected) if selected is not None else total
    target_completed = completed
    if chapters is not None and selected is not None:
        target_completed = sum(
            1
            for chapter in chapters
            if int(chapter["chapter_index"]) in selected
            and chapter["status"] == "succeeded"
        )

    if chapters is not None:
        progress = target_completed / target if target else 0
    else:
        # 列表视图没有章节明细，保持全书口径，避免分子分母口径混用。
        progress = completed / total if total else 0

    view = {
        "task_id": task["task_id"],
        "type": task["type"],
        "status": task["status"],
        "phase": task.get("phase"),
        "progress": progress,
        "total_chapters": total,
        "completed_chapters": completed,
        "target_chapters": target,
        "target_completed_chapters": target_completed,
        "attempts": task.get("attempts", 0),
        "error": task.get("error"),
        "result": task.get("result"),
        "created_at": task.get("created_at"),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "heartbeat_at": task.get("heartbeat_at"),
        "control": (task.get("params") or {}).get("control") or {},
    }
    if chapters is not None:
        view["chapters"] = [
            {
                "index": int(chapter["chapter_index"]),
                "title": chapter["title"],
                "status": chapter["status"],
                "audio_path": chapter.get("audio_path"),
                "error": chapter.get("error"),
                "started_at": chapter.get("started_at"),
                "completed_at": chapter.get("finished_at"),
            }
            for chapter in chapters
        ]
    return view
