"""Read-only task queries used by the API and CLI when Core is offline."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from models.task import task_view
from system.config import PROJECT_ROOT
from system.db import connect_tasks_db

TASK_COLUMNS = """
  task_id, type, status, phase, params_json, result_json, error,
  total_chapters, completed_chapters, attempts, heartbeat_at, queued_at,
  started_at, finished_at, created_at, updated_at, idempotency_key
"""

CHAPTER_COLUMNS = """
  task_id, chapter_index, title, status, content, audio_path, error,
  attempts, started_at, finished_at, created_at, updated_at
"""


def _decode(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _task(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["params"] = _decode(item.pop("params_json"), {})
    item["result"] = _decode(item.pop("result_json"), None)
    return item


class TaskQueryService:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else (
            PROJECT_ROOT / "data" / "tasks.db"
        )

    def _connect(self) -> sqlite3.Connection | None:
        if not self.db_path.exists():
            return None
        return connect_tasks_db(self.db_path, readonly=True)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        if connection is None:
            return None
        try:
            row = connection.execute(
                f"""
                SELECT {TASK_COLUMNS}
                FROM tasks
                WHERE task_id = ?
                LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        finally:
            connection.close()
        return _task(row) if row else None

    def list_chapters(self, task_id: str) -> list[dict[str, Any]]:
        connection = self._connect()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                f"""
                SELECT {CHAPTER_COLUMNS}
                FROM task_chapters
                WHERE task_id = ?
                ORDER BY chapter_index ASC
                LIMIT 100000
                """,
                (task_id,),
            ).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

    def get_chapter(self, task_id: str, index: int) -> dict[str, Any] | None:
        connection = self._connect()
        if connection is None:
            return None
        try:
            row = connection.execute(
                f"""
                SELECT {CHAPTER_COLUMNS}
                FROM task_chapters
                WHERE task_id = ? AND chapter_index = ?
                LIMIT 1
                """,
                (task_id, index),
            ).fetchone()
        finally:
            connection.close()
        return dict(row) if row else None

    def get_task_view(self, task_id: str) -> dict[str, Any] | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        return task_view(task, self.list_chapters(task_id))

    def list_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        connection = self._connect()
        if connection is None:
            return {
                "list": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_more": False,
            }
        filters: list[str] = []
        values: list[Any] = []
        if status:
            filters.append("status = ?")
            values.append(status)
        if task_type:
            filters.append("type = ?")
            values.append(task_type)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        try:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM tasks {where}", values
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT {TASK_COLUMNS}
                FROM tasks
                {where}
                ORDER BY created_at DESC, task_id DESC
                LIMIT ? OFFSET ?
                """,
                [*values, page_size, (page - 1) * page_size],
            ).fetchall()
        finally:
            connection.close()
        total = int(total_row["total"]) if total_row else 0
        return {
            "list": [_task(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total,
        }

    def list_events(
        self,
        task_id: str,
        *,
        after_id: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        limit = min(max(1, limit), 500)
        connection = self._connect()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                """
                SELECT event_id, task_id, type, payload_json, created_at
                FROM task_events
                WHERE task_id = ? AND event_id > ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (task_id, max(0, after_id), limit),
            ).fetchall()
        finally:
            connection.close()
        events = []
        for row in rows:
            item = dict(row)
            item["payload"] = _decode(item.pop("payload_json"), {})
            events.append(item)
        return events

    def stats(self) -> dict[str, Any]:
        connection = self._connect()
        if connection is None:
            return {"tasks": {}, "schema_version": 0}
        try:
            rows = connection.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM tasks
                GROUP BY status
                ORDER BY status
                LIMIT 100
                """
            ).fetchall()
            schema = connection.execute(
                """
                SELECT tasks_schema_version
                FROM schema_meta
                WHERE id = 1
                LIMIT 1
                """
            ).fetchone()
        finally:
            connection.close()
        return {
            "tasks": {row["status"]: int(row["count"]) for row in rows},
            "schema_version": int(schema["tasks_schema_version"]) if schema else 0,
        }
