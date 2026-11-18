"""Task repository for the Core engine; the only writer of tasks.db."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from engine.migrations import migrate_tasks_db
from engine.models import (
    TERMINAL_STATUSES,
    InvalidTransitionError,
    TaskNotFoundError,
    ensure_transition,
)
from system.db import connect_tasks_db, utc_now_iso

_UNSET = object()

_TASK_COLUMNS = """
  task_id, type, status, phase, params_json, result_json, error,
  total_chapters, completed_chapters, attempts, heartbeat_at, queued_at,
  started_at, finished_at, created_at, updated_at, idempotency_key
"""

_CHAPTER_COLUMNS = """
  task_id, chapter_index, title, status, content, audio_path, error,
  attempts, started_at, finished_at, created_at, updated_at
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["params"] = _decode(item.pop("params_json"), {})
    item["result"] = _decode(item.pop("result_json"), None)
    return item


def _row_to_chapter(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class TaskStore:
    """Persistence and state transitions for tasks, chapters, and events."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else None
        migrate_tasks_db(self.db_path)
        self._lock = threading.RLock()
        self._local = threading.local()
        self._connections: set[sqlite3.Connection] = set()

    def _conn(self) -> sqlite3.Connection:
        """Return this thread's own connection; never share across threads."""
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = connect_tasks_db(self.db_path)
            self._local.connection = connection
            with self._lock:
                self._connections.add(connection)
        return connection

    def close_thread_connection(self) -> None:
        """Close the calling thread's connection (call at request teardown)."""
        connection = getattr(self._local, "connection", None)
        if connection is None:
            return
        self._local.connection = None
        with self._lock:
            self._connections.discard(connection)
        try:
            connection.close()
        except sqlite3.Error:
            pass

    def close(self) -> None:
        with self._lock:
            connections = list(self._connections)
            self._connections.clear()
        for connection in connections:
            try:
                connection.close()
            except sqlite3.Error:
                pass

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def create_task(
        self,
        task_type: str,
        params: Mapping[str, Any] | None = None,
        *,
        task_id: str | None = None,
        phase: str = "uploaded",
        idempotency_key: str | None = None,
        status: str = "pending",
    ) -> dict[str, Any]:
        now = utc_now_iso()
        new_task_id = task_id or str(uuid.uuid4())
        with self._lock, self._conn():
            if idempotency_key is not None:
                existing = self._conn().execute(
                    f"""
                    SELECT {_TASK_COLUMNS}
                    FROM tasks
                    WHERE idempotency_key = ?
                    LIMIT 1
                    """,
                    (idempotency_key,),
                ).fetchone()
                if existing is not None:
                    return _row_to_task(existing)

            self._conn().execute(
                """
                INSERT INTO tasks (
                  task_id, type, status, phase, params_json, result_json, error,
                  total_chapters, completed_chapters, attempts, heartbeat_at,
                  queued_at, started_at, finished_at, created_at, updated_at,
                  idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, NULL, NULL, 0, 0, 0, NULL, NULL, NULL,
                        NULL, ?, ?, ?)
                """,
                (
                    new_task_id,
                    task_type,
                    status,
                    phase,
                    _json(dict(params or {})),
                    now,
                    now,
                    idempotency_key,
                ),
            )
            self._insert_event_unlocked(
                new_task_id, "task.created", {"type": task_type, "phase": phase}
            )
        return self.get_task(new_task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn().execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM tasks
                WHERE task_id = ?
                LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        return _row_to_task(row) if row is not None else None

    def require_task(self, task_id: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

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
        filters: list[str] = []
        values: list[Any] = []
        if status:
            filters.append("status = ?")
            values.append(status)
        if task_type:
            filters.append("type = ?")
            values.append(task_type)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._lock:
            total_row = self._conn().execute(
                f"SELECT COUNT(*) AS total FROM tasks {where}",
                values,
            ).fetchone()
            rows = self._conn().execute(
                f"""
                SELECT {_TASK_COLUMNS}
                FROM tasks
                {where}
                ORDER BY created_at DESC, task_id DESC
                LIMIT ? OFFSET ?
                """,
                [*values, page_size, (page - 1) * page_size],
            ).fetchall()
        return {
            "list": [_row_to_task(row) for row in rows],
            "total": int(total_row["total"]) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }

    def status_counts(self) -> dict[str, int]:
        with self._lock:
            rows = self._conn().execute(
                """
                SELECT status, COUNT(*) AS count
                FROM tasks
                GROUP BY status
                ORDER BY status
                LIMIT 100
                """
            ).fetchall()
        return {row["status"]: int(row["count"]) for row in rows}

    def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        phase: Any = _UNSET,
        error: Any = _UNSET,
        result: Any = _UNSET,
        params: Any = _UNSET,
        heartbeat: bool = False,
        increment_attempts: bool = False,
        queued: bool = False,
        started: bool = False,
        finished: bool = False,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        task = self.require_task(task_id)
        if expected_status is not None and task["status"] != expected_status:
            raise InvalidTransitionError(task_id, task["status"], status or "")
        if status is not None:
            ensure_transition(task_id, task["status"], status)
        now = utc_now_iso()
        assignments = ["updated_at = ?"]
        values: list[Any] = [now]
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
            if status in TERMINAL_STATUSES:
                assignments.append("finished_at = ?")
                values.append(now)
            elif status in ("pending", "queued"):
                assignments.append("finished_at = NULL")
        if phase is not _UNSET:
            assignments.append("phase = ?")
            values.append(phase)
        if error is not _UNSET:
            assignments.append("error = ?")
            values.append(error)
        if result is not _UNSET:
            assignments.append("result_json = ?")
            values.append(_json(result) if result is not None else None)
        if params is not _UNSET:
            assignments.append("params_json = ?")
            values.append(_json(dict(params)))
        if heartbeat:
            assignments.append("heartbeat_at = ?")
            values.append(now)
        if increment_attempts:
            assignments.append("attempts = attempts + 1")
        if queued:
            assignments.append("queued_at = ?")
            values.append(now)
        if started:
            assignments.append("started_at = ?")
            values.append(now)
        if finished:
            assignments.append("finished_at = ?")
            values.append(now)
        values.append(task_id)
        where = "task_id = ?"
        if expected_status is not None:
            where += " AND status = ?"
            values.append(expected_status)
        with self._lock, self._conn():
            cursor = self._conn().execute(
                f"""
                UPDATE tasks
                SET {", ".join(assignments)}
                WHERE {where}
                """,
                values,
            )
            if cursor.rowcount != 1:
                raise InvalidTransitionError(
                    task_id, task["status"], status or ""
                )
        return self.require_task(task_id)

    def transition(
        self,
        task_id: str,
        target: str,
        *,
        phase: Any = _UNSET,
        error: Any = _UNSET,
        result: Any = _UNSET,
        event_type: str | None = None,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        updated = self.update_task(
            task_id,
            status=target,
            phase=phase,
            error=error,
            result=result,
            expected_status=expected_status,
        )
        if event_type:
            self.add_event(task_id, event_type, {"status": target})
        return updated

    def queue_for_generation(
        self,
        task_id: str,
        *,
        options: Mapping[str, Any] | None = None,
        reopen: bool = False,
    ) -> dict[str, Any]:
        task = self.require_task(task_id)
        target_current = task["status"]
        params = task["params"]
        if options:
            params = {**params, "generation": dict(options)}
        if reopen and target_current in ("succeeded", "failed", "canceled"):
            phase = "generation_requested"
            now = utc_now_iso()
            with self._lock, self._conn():
                self._conn().execute(
                    """
                    UPDATE tasks
                    SET status = 'queued', phase = ?, params_json = ?, error = NULL,
                        result_json = NULL, queued_at = ?, finished_at = NULL,
                        updated_at = ?
                    WHERE task_id = ?
                    """,
                    (phase, _json(params), now, now, task_id),
                )
                self._conn().execute(
                    """
                    UPDATE task_chapters
                    SET status = 'pending', error = NULL, updated_at = ?
                    WHERE task_id = ? AND status IN ('running', 'paused')
                    """,
                    (now, task_id),
                )
                self._insert_event_unlocked(
                    task_id,
                    "task.queued",
                    {"phase": phase, "reopened_from": target_current},
                )
            return self.require_task(task_id)

        ensure_transition(task_id, target_current, "queued")
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                UPDATE tasks
                SET status = 'queued', phase = 'generation_requested',
                    params_json = ?, error = NULL, result_json = NULL,
                    queued_at = ?, finished_at = NULL, updated_at = ?
                WHERE task_id = ?
                """,
                (_json(params), now, now, task_id),
            )
            self._insert_event_unlocked(
                task_id, "task.queued", {"phase": "generation_requested"}
            )
        return self.require_task(task_id)

    def claim_queued_task(self, task_id: str) -> dict[str, Any] | None:
        """Atomically claim a queued task; returns None when another worker won."""
        now = utc_now_iso()
        with self._lock, self._conn():
            cursor = self._conn().execute(
                """
                UPDATE tasks
                SET status = 'running',
                    phase = CASE
                      WHEN phase = 'generation_resume' THEN 'generation_resume'
                      ELSE 'generating'
                    END,
                    attempts = attempts + 1,
                    heartbeat_at = ?,
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE task_id = ? AND status = 'queued'
                """,
                (now, now, now, task_id),
            )
            if cursor.rowcount != 1:
                return None
            self._insert_event_unlocked(
                task_id, "task.started", {"attempts": self._attempts(task_id)}
            )
        return self.require_task(task_id)

    def next_queued_task_id(self) -> str | None:
        with self._lock:
            row = self._conn().execute(
                """
                SELECT task_id
                FROM tasks
                WHERE status = 'queued'
                ORDER BY queued_at ASC, created_at ASC
                LIMIT 1
                """
            ).fetchone()
        return row["task_id"] if row else None

    def heartbeat(self, task_id: str) -> None:
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                UPDATE tasks
                SET heartbeat_at = ?, updated_at = ?
                WHERE task_id = ? AND status = 'running'
                """,
                (now, now, task_id),
            )

    def cancel_queued_or_pending(self, task_id: str) -> dict[str, Any]:
        """Cancel a task that has not yet produced a running chapter."""
        task = self.require_task(task_id)
        if task["status"] not in ("pending", "queued"):
            ensure_transition(task_id, task["status"], "canceled")
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                UPDATE tasks
                SET status = 'canceled', phase = 'canceled', finished_at = ?,
                    updated_at = ?
                WHERE task_id = ? AND status IN ('pending', 'queued')
                """,
                (now, now, task_id),
            )
            self._insert_event_unlocked(task_id, "task.canceled", {})
        return self.require_task(task_id)

    def set_control(self, task_id: str, **flags: bool) -> dict[str, Any]:
        """Persist cooperative pause/cancel requests on the task."""
        task = self.require_task(task_id)
        params = dict(task["params"])
        control = dict(params.get("control") or {})
        control.update(flags)
        params["control"] = control
        return self.update_task(task_id, params=params)

    def clear_control(self, task_id: str) -> dict[str, Any]:
        task = self.require_task(task_id)
        params = dict(task["params"])
        params.pop("control", None)
        return self.update_task(task_id, params=params)

    def resume_paused_task(self, task_id: str) -> dict[str, Any]:
        task = self.require_task(task_id)
        ensure_transition(task_id, task["status"], "queued")
        now = utc_now_iso()
        params = dict(task["params"])
        params.pop("control", None)
        with self._lock, self._conn():
            cursor = self._conn().execute(
                """
                UPDATE tasks
                SET status = 'queued', phase = 'generation_resume',
                    queued_at = ?, error = NULL, finished_at = NULL,
                    updated_at = ?, params_json = ?
                WHERE task_id = ? AND status = 'paused'
                """,
                (now, now, _json(params), task_id),
            )
            if cursor.rowcount != 1:
                raise InvalidTransitionError(task_id, task["status"], "queued")
            self._conn().execute(
                """
                UPDATE task_chapters
                SET status = 'pending', error = NULL, started_at = NULL,
                    finished_at = NULL, updated_at = ?
                WHERE task_id = ? AND status IN ('running', 'paused')
                """,
                (now, task_id),
            )
            self._insert_event_unlocked(task_id, "task.resumed", {})
        return self.require_task(task_id)

    def force_cancel(
        self,
        task_id: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any] | None:
        """Cancel a pending, queued, or paused task immediately.

        Returns None when another actor changed the state first (for example,
        the scheduler claimed a queued task as running).
        """
        task = self.require_task(task_id)
        current = expected_status or task["status"]
        if current not in ("pending", "queued", "paused"):
            ensure_transition(task_id, current, "canceled")
        now = utc_now_iso()
        with self._lock, self._conn():
            cursor = self._conn().execute(
                """
                UPDATE tasks
                SET status = 'canceled', phase = 'canceled', error = NULL,
                    finished_at = ?, updated_at = ?
                WHERE task_id = ? AND status = ?
                """,
                (now, now, task_id, current),
            )
            if cursor.rowcount != 1:
                return None
            self._insert_event_unlocked(task_id, "task.canceled", {})
        return self.require_task(task_id)

    def reopen_for_generation(self, task_id: str) -> None:
        """Controlled reopen for another generation run on an existing book."""
        task = self.require_task(task_id)
        if task["status"] == "running":
            raise ValueError("Task is running")
        self.update_task(task_id, phase="ready", error=None, result=None)
        if task["status"] in ("succeeded", "failed", "canceled"):
            with self._lock, self._conn():
                self._conn().execute(
                    """
                    UPDATE tasks
                    SET status = 'pending', phase = 'ready', error = NULL,
                        result_json = NULL, finished_at = NULL, updated_at = ?
                    WHERE task_id = ?
                    """,
                    (utc_now_iso(), task_id),
                )

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------
    def replace_chapters(
        self,
        task_id: str,
        chapters: Iterable[Mapping[str, Any]],
    ) -> None:
        now = utc_now_iso()
        chapter_list = list(chapters)
        with self._lock, self._conn():
            self._conn().execute(
                "DELETE FROM task_chapters WHERE task_id = ?",
                (task_id,),
            )
            for chapter in chapter_list:
                self._conn().execute(
                    """
                    INSERT INTO task_chapters (
                      task_id, chapter_index, title, status, content, audio_path,
                      error, attempts, started_at, finished_at, created_at,
                      updated_at
                    )
                    VALUES (?, ?, ?, 'pending', ?, NULL, NULL, 0, NULL, NULL, ?, ?)
                    """,
                    (
                        task_id,
                        int(chapter["index"]),
                        str(chapter["title"]),
                        chapter.get("content"),
                        now,
                        now,
                    ),
                )
            self._conn().execute(
                """
                UPDATE tasks
                SET total_chapters = ?, completed_chapters = 0, updated_at = ?
                WHERE task_id = ?
                """,
                (len(chapter_list), now, task_id),
            )
            self._insert_event_unlocked(
                task_id, "task.parsed", {"total_chapters": len(chapter_list)}
            )

    def insert_chapter(
        self,
        task_id: str,
        *,
        index: int,
        title: str,
        content: str | None = None,
    ) -> None:
        """Insert one chapter if it does not exist, then refresh total_chapters."""
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                INSERT OR IGNORE INTO task_chapters (
                  task_id, chapter_index, title, status, content, audio_path,
                  error, attempts, started_at, finished_at, created_at, updated_at
                )
                VALUES (?, ?, ?, 'pending', ?, NULL, NULL, 0, NULL, NULL, ?, ?)
                """,
                (task_id, int(index), str(title), content, now, now),
            )
            self._conn().execute(
                """
                UPDATE tasks
                SET total_chapters = (
                  SELECT COUNT(*) FROM task_chapters WHERE task_id = ?
                ), updated_at = ?
                WHERE task_id = ?
                """,
                (task_id, now, task_id),
            )

    def list_chapters(self, task_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn().execute(
                f"""
                SELECT {_CHAPTER_COLUMNS}
                FROM task_chapters
                WHERE task_id = ?
                ORDER BY chapter_index ASC
                LIMIT 100000
                """,
                (task_id,),
            ).fetchall()
        return [_row_to_chapter(row) for row in rows]

    def get_chapter(self, task_id: str, chapter_index: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn().execute(
                f"""
                SELECT {_CHAPTER_COLUMNS}
                FROM task_chapters
                WHERE task_id = ? AND chapter_index = ?
                LIMIT 1
                """,
                (task_id, chapter_index),
            ).fetchone()
        return _row_to_chapter(row) if row else None

    def update_chapter(
        self,
        task_id: str,
        chapter_index: int,
        *,
        status: str,
        audio_path: str | None = None,
        error: str | None = None,
        content: str | None = None,
        increment_attempts: bool = False,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        assignments = ["status = ?", "updated_at = ?"]
        values: list[Any] = [status, now]
        if audio_path is not None:
            assignments.append("audio_path = ?")
            values.append(audio_path)
        if status in ("succeeded", "failed", "canceled"):
            assignments.append("finished_at = ?")
            values.append(now)
        if status == "running":
            assignments.append("started_at = COALESCE(started_at, ?)")
            values.append(now)
        assignments.append("error = ?")
        values.append(error if status == "failed" else None)
        if content is not None:
            assignments.append("content = ?")
            values.append(content)
        if increment_attempts:
            assignments.append("attempts = attempts + 1")
        values.extend([task_id, chapter_index])
        with self._lock, self._conn():
            self._conn().execute(
                f"""
                UPDATE task_chapters
                SET {", ".join(assignments)}
                WHERE task_id = ? AND chapter_index = ?
                """,
                values,
            )
            self._refresh_completed_unlocked(task_id)
            self._insert_event_unlocked(
                task_id,
                "task.progress",
                {
                    "chapter_index": chapter_index,
                    "chapter_status": status,
                    "has_audio": bool(audio_path),
                    "error": error if status == "failed" else None,
                },
            )
        chapter = self.get_chapter(task_id, chapter_index)
        if chapter is None:
            raise TaskNotFoundError(f"{task_id}#{chapter_index}")
        return chapter

    def recover_running_task(self, task_id: str) -> bool:
        """Requeue a task interrupted by a Core crash and reset its current chapter."""
        task = self.require_task(task_id)
        if task["status"] != "running":
            return False
        now = utc_now_iso()
        params = dict(task["params"])
        params.pop("control", None)
        with self._lock, self._conn():
            self._conn().execute(
                """
                UPDATE tasks
                SET status = 'queued', phase = 'generation_resume',
                    queued_at = ?, heartbeat_at = NULL, finished_at = NULL,
                    updated_at = ?, params_json = ?
                WHERE task_id = ? AND status = 'running'
                """,
                (now, now, _json(params), task_id),
            )
            self._conn().execute(
                """
                UPDATE task_chapters
                SET status = 'pending', error = NULL, started_at = NULL,
                    finished_at = NULL, updated_at = ?
                WHERE task_id = ? AND status IN ('running', 'paused')
                """,
                (now, task_id),
            )
            self._insert_event_unlocked(
                task_id, "task.recovered", {"action": "requeued"}
            )
        return True

    def reset_interrupted_parse(self) -> int:
        """Mark parses interrupted by a Core restart as failed."""
        now = utc_now_iso()
        with self._lock, self._conn():
            cursor = self._conn().execute(
                """
                UPDATE tasks
                SET phase = 'parse_failed',
                    error = 'parse interrupted by restart',
                    updated_at = ?
                WHERE phase = 'parsing'
                """,
                (now,),
            )
        return cursor.rowcount

    def recover_interrupted_tasks(self) -> list[str]:
        """Apply the configured crash-recovery policy to all running tasks."""
        with self._lock:
            rows = self._conn().execute(
                """
                SELECT task_id
                FROM tasks
                WHERE status = 'running'
                ORDER BY updated_at ASC
                LIMIT 1000
                """
            ).fetchall()
        recovered = []
        for row in rows:
            if self.recover_running_task(row["task_id"]):
                recovered.append(row["task_id"])
        return recovered

    def reset_chapter(self, task_id: str, chapter_index: int) -> bool:
        now = utc_now_iso()
        with self._lock, self._conn():
            cursor = self._conn().execute(
                """
                UPDATE task_chapters
                SET status = 'pending', audio_path = NULL, error = NULL,
                    started_at = NULL, finished_at = NULL, updated_at = ?
                WHERE task_id = ? AND chapter_index = ?
                """,
                (now, task_id, chapter_index),
            )
            self._refresh_completed_unlocked(task_id)
        return cursor.rowcount == 1

    def reset_interrupted_chapters(self, task_id: str) -> None:
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                UPDATE task_chapters
                SET status = 'pending', error = NULL, started_at = NULL,
                    finished_at = NULL, updated_at = ?
                WHERE task_id = ? AND status IN ('running', 'paused')
                """,
                (now, task_id),
            )
            self._refresh_completed_unlocked(task_id)

    def _refresh_completed_unlocked(self, task_id: str) -> None:
        row = self._conn().execute(
            """
            SELECT COUNT(*) AS completed
            FROM task_chapters
            WHERE task_id = ? AND status = 'succeeded'
            """,
            (task_id,),
        ).fetchone()
        self._conn().execute(
            """
            UPDATE tasks
            SET completed_chapters = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (int(row["completed"]) if row else 0, utc_now_iso(), task_id),
        )

    def _attempts(self, task_id: str) -> int:
        row = self._conn().execute(
            "SELECT attempts FROM tasks WHERE task_id = ? LIMIT 1",
            (task_id,),
        ).fetchone()
        return int(row["attempts"]) if row else 0

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def add_event(
        self,
        task_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> int:
        with self._lock, self._conn():
            return self._insert_event_unlocked(task_id, event_type, payload)

    def _insert_event_unlocked(
        self,
        task_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> int:
        cursor = self._conn().execute(
            """
            INSERT INTO task_events (task_id, type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, event_type, _json(dict(payload or {})), utc_now_iso()),
        )
        return int(cursor.lastrowid)

    def list_events(
        self,
        task_id: str | None = None,
        *,
        after_id: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        limit = min(max(1, limit), 500)
        with self._lock:
            if task_id:
                rows = self._conn().execute(
                    """
                    SELECT event_id, task_id, type, payload_json, created_at
                    FROM task_events
                    WHERE task_id = ? AND event_id > ?
                    ORDER BY event_id ASC
                    LIMIT ?
                    """,
                    (task_id, max(0, after_id), limit),
                ).fetchall()
            else:
                rows = self._conn().execute(
                    """
                    SELECT event_id, task_id, type, payload_json, created_at
                    FROM task_events
                    WHERE event_id > ?
                    ORDER BY event_id ASC
                    LIMIT ?
                    """,
                    (max(0, after_id), limit),
                ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            item["payload"] = _decode(item.pop("payload_json"), {})
            events.append(item)
        return events

    # ------------------------------------------------------------------
    # Idempotent command log
    # ------------------------------------------------------------------
    def get_command(self, command_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn().execute(
                """
                SELECT command_id, command, payload_hash, status, result_json,
                       created_at, updated_at
                FROM command_log
                WHERE command_id = ?
                LIMIT 1
                """,
                (command_id,),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["result"] = _decode(item.pop("result_json"), None)
        return item

    def begin_command(
        self,
        command_id: str,
        command: str,
        payload_hash: str,
    ) -> None:
        """Persist an in-progress marker before dispatching a command.

        A crash after this point leaves ``status='in_progress'`` with no result.
        Retries of non-additive commands are rejected instead of risking a
        duplicate side effect; ``task.add`` is safe to retry because it has a
        unique idempotency key.
        """
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                INSERT INTO command_log (
                  command_id, command, payload_hash, status, result_json,
                  created_at, updated_at
                )
                VALUES (?, ?, ?, 'in_progress', NULL, ?, ?)
                ON CONFLICT(command_id) DO NOTHING
                """,
                (command_id, command, payload_hash, now, now),
            )

    def record_command(
        self,
        command_id: str,
        command: str,
        payload_hash: str,
        result: Mapping[str, Any],
    ) -> None:
        now = utc_now_iso()
        with self._lock, self._conn():
            self._conn().execute(
                """
                INSERT INTO command_log (
                  command_id, command, payload_hash, status, result_json,
                  created_at, updated_at
                )
                VALUES (?, ?, ?, 'completed', ?, ?, ?)
                ON CONFLICT(command_id) DO UPDATE SET
                  status = 'completed',
                  result_json = excluded.result_json,
                  updated_at = excluded.updated_at
                """,
                (command_id, command, payload_hash, _json(dict(result)), now, now),
            )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def cleanup_terminal_tasks(
        self,
        ttl_seconds: int,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if ttl_seconds <= 0:
            return {"removed_task_ids": [], "count": 0, "dry_run": dry_run}
        cutoff = (
            datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._lock:
            rows = self._conn().execute(
                """
                SELECT task_id
                FROM tasks
                WHERE status IN ('succeeded', 'failed', 'canceled', 'removed')
                  AND updated_at < ?
                ORDER BY updated_at ASC
                LIMIT 1000
                """,
                (cutoff,),
            ).fetchall()
        task_ids = [row["task_id"] for row in rows]
        if dry_run or not task_ids:
            return {"removed_task_ids": task_ids, "count": len(task_ids), "dry_run": dry_run}

        placeholders = ",".join("?" for _ in task_ids)
        with self._lock, self._conn():
            self._conn().execute(
                f"DELETE FROM task_events WHERE task_id IN ({placeholders})",
                task_ids,
            )
            self._conn().execute(
                f"DELETE FROM task_chapters WHERE task_id IN ({placeholders})",
                task_ids,
            )
            self._conn().execute(
                f"DELETE FROM tasks WHERE task_id IN ({placeholders})",
                task_ids,
            )
        return {"removed_task_ids": task_ids, "count": len(task_ids), "dry_run": False}

    def referenced_source_paths(self) -> set[str]:
        """Return resolved source paths still referenced by any task."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT params_json FROM tasks LIMIT 100000"
            ).fetchall()
        paths: set[str] = set()
        for row in rows:
            params = _decode(row["params_json"], {})
            if not isinstance(params, dict):
                continue
            value = params.get("file_path")
            if isinstance(value, str) and value:
                try:
                    paths.add(str(Path(value).expanduser().resolve(strict=False)))
                except OSError:
                    continue
        return paths

    def cleanup_uploads(self, upload_dir: str | Path, ttl_seconds: int) -> int:
        """Remove orphan upload files older than the TTL."""
        if ttl_seconds <= 0:
            return 0
        root = Path(upload_dir).expanduser().resolve(strict=False)
        if not root.is_dir():
            return 0
        cutoff = time.time() - ttl_seconds
        referenced = self.referenced_source_paths()
        removed = 0
        for path in root.iterdir():
            if not path.is_file():
                continue
            try:
                resolved = path.resolve(strict=False)
                if str(resolved) in referenced or path.stat().st_mtime >= cutoff:
                    continue
                path.unlink()
                removed += 1
            except OSError:
                continue
        return removed

    def cleanup_command_log(self, ttl_seconds: int, *, dry_run: bool = False) -> int:
        """Remove old idempotency records so command_log cannot grow forever."""
        if ttl_seconds <= 0:
            return 0
        cutoff = (
            datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._lock:
            rows = self._conn().execute(
                """
                SELECT command_id
                FROM command_log
                WHERE updated_at < ?
                ORDER BY updated_at ASC
                LIMIT 1000
                """,
                (cutoff,),
            ).fetchall()
        command_ids = [row["command_id"] for row in rows]
        if dry_run or not command_ids:
            return len(command_ids)
        placeholders = ",".join("?" for _ in command_ids)
        with self._lock, self._conn():
            self._conn().execute(
                f"DELETE FROM command_log WHERE command_id IN ({placeholders})",
                command_ids,
            )
        return len(command_ids)

    def schema_version(self) -> int:
        with self._lock:
            row = self._conn().execute(
                """
                SELECT tasks_schema_version
                FROM schema_meta
                WHERE id = 1
                LIMIT 1
                """
            ).fetchone()
        return int(row["tasks_schema_version"]) if row else 0

    def integrity_check(self) -> str:
        """Return "ok" or a diagnostic string from PRAGMA quick_check."""
        with self._lock:
            rows = self._conn().execute("PRAGMA quick_check").fetchall()
        if len(rows) == 1 and rows[0][0] == "ok":
            return "ok"
        return "; ".join(str(row[0]) for row in rows)
