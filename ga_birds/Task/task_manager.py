"""
GA Sprite Birds - Task manager
Manages async task creation, execution, and status queries

Version: v1.0
Dev team: Tiger
"""

import os
import json
import uuid
import asyncio
import importlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

from ga_birds.Common.i18n import t

import config

# Dynamically import the core module
_core_module_name = config.CORE_DIR.replace('-', '_')
_parser_module = importlib.import_module(f'{_core_module_name}.Parser')
Chapter = _parser_module.Chapter


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"  # waiting
    PARSING = "parsing"  # parsing
    PARSED = "parsed"  # parsed
    GENERATING = "generating"  # generating
    PAUSED = "paused"  # paused (between chapters)
    COMPLETED = "completed"  # completed
    FAILED = "failed"  # failed
    CANCELLED = "cancelled"  # cancelled


@dataclass
class ChapterProgress:
    """Chapter progress"""
    index: int  # chapter number
    title: str  # chapter title
    status: TaskStatus = TaskStatus.PENDING  # status
    audio_path: Optional[str] = None  # audio file path
    error: Optional[str] = None  # error message
    started_at: Optional[datetime] = None  # start time
    completed_at: Optional[datetime] = None  # completion time


@dataclass
class Task:
    """Task data class"""
    task_id: str  # task ID
    status: TaskStatus = TaskStatus.PENDING  # task status
    total_chapters: int = 0  # total chapter count
    completed_chapters: int = 0  # completed chapter count
    chapters: List[ChapterProgress] = field(default_factory=list)  # chapter progress list
    error: Optional[str] = None  # error message
    created_at: datetime = field(default_factory=datetime.now)  # creation time
    started_at: Optional[datetime] = None  # start time
    completed_at: Optional[datetime] = None  # completion time
    metadata: Dict[str, Any] = field(default_factory=dict)  # metadata (file name, config, etc.)
    pause_requested: bool = False  # transient flag: pause after the current chapter


class TaskManager:
    """Task manager"""

    def __init__(self, persist: bool = True):
        """Initialize the task manager"""
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.persist = persist
        self.record_dir = Path(config.TASK_CACHE_DIR)

        logger.info(t("task.manager_initialized"))
        self._load_records()

    def create_task(
        self,
        chapters: Optional[List[Chapter]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new task

        Args:
            chapters: chapter list
            metadata: metadata

        Returns:
            task ID
        """
        task_id = str(uuid.uuid4())

        # Create the chapter progress list
        chapter_progress = []
        if chapters:
            for chapter in chapters:
                chapter_progress.append(ChapterProgress(
                    index=chapter.index,
                    title=chapter.title
                ))

        task = Task(
            task_id=task_id,
            total_chapters=len(chapter_progress),
            chapters=chapter_progress,
            metadata=metadata or {}
        )

        self.tasks[task_id] = task
        logger.info(t("task.task_created", task_id=task_id, count=task.total_chapters))
        self._save_record(task_id)

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task

        Args:
            task_id: task ID

        Returns:
            task object, or None if it does not exist
        """
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        Update task status

        Args:
            task_id: task ID
            status: new status
        """
        task = self.get_task(task_id)
        if task:
            task.status = status

            if status == TaskStatus.GENERATING:
                if task.started_at is None:
                    task.started_at = datetime.now()
                # A new run starts cleanly even after a failure or cancellation.
                task.completed_at = None
                task.error = None
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()

            logger.info(t("task.task_status_updated", task_id=task_id, status=status.value))
            self._save_record(task_id)

    def update_chapter_status(
        self,
        task_id: str,
        chapter_index: int,
        status: TaskStatus,
        audio_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update chapter status

        Args:
            task_id: task ID
            chapter_index: chapter number
            status: new status
            audio_path: audio file path
            error: error message
        """
        task = self.get_task(task_id)
        if not task:
            return

        # Find the chapter
        for chapter in task.chapters:
            if chapter.index == chapter_index:
                chapter.status = status

                if status == TaskStatus.GENERATING and chapter.started_at is None:
                    chapter.started_at = datetime.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    chapter.completed_at = datetime.now()

                if audio_path:
                    chapter.audio_path = audio_path

                # A retried chapter starts clean; only FAILED keeps an error.
                chapter.error = error if status == TaskStatus.FAILED else None

                # Recompute the completed chapter count so repeated generation
                # or deletion never makes the counter drift
                task.completed_chapters = sum(
                    1 for item in task.chapters
                    if item.status == TaskStatus.COMPLETED
                )

                if status == TaskStatus.COMPLETED:
                    logger.info(t("task.chapter_completed", task_id=task_id, index=chapter_index, title=chapter.title))

                self._save_record(task_id)
                break

    def get_chapter_audio(self, task_id: str, chapter_index: int) -> Optional[str]:
        """
        Get the chapter audio path

        Args:
            task_id: task ID
            chapter_index: chapter number

        Returns:
            audio file path, or None if it does not exist
        """
        task = self.get_task(task_id)
        if not task:
            return None

        for chapter in task.chapters:
            if chapter.index == chapter_index:
                return chapter.audio_path

        return None

    def get_chapter_status(self, task_id: str, chapter_index: int) -> Optional[TaskStatus]:
        """Return a chapter's status, or None when it does not exist."""
        task = self.get_task(task_id)
        if not task:
            return None
        for chapter in task.chapters:
            if chapter.index == chapter_index:
                return chapter.status
        return None

    def is_running(self, task_id: str) -> bool:
        """Return whether the task currently has a running generation job."""
        running = self.running_tasks.get(task_id)
        return bool(running and not running.done())

    def request_pause(self, task_id: str) -> bool:
        """Ask a running task to pause after the current chapter."""
        task = self.get_task(task_id)
        if not task:
            return False
        task.pause_requested = True
        logger.info(t("task.pause_requested", task_id=task_id))
        return True

    def clear_pause(self, task_id: str) -> bool:
        """Clear the pause flag before resuming."""
        task = self.get_task(task_id)
        if not task:
            return False
        task.pause_requested = False
        return True

    def mark_chapters_paused(
        self,
        task_id: str,
        chapter_indexes: Optional[List[int]] = None
    ) -> None:
        """Mark pending chapters as paused so the UI reflects the pause."""
        task = self.get_task(task_id)
        if not task:
            return
        wanted = set(chapter_indexes) if chapter_indexes is not None else None
        for chapter in task.chapters:
            if wanted is not None and chapter.index not in wanted:
                continue
            if chapter.status == TaskStatus.PENDING:
                chapter.status = TaskStatus.PAUSED

        self._save_record(task_id)

    def delete_chapter_audio(
        self,
        task_id: str,
        chapter_index: int,
        delete_file: bool = True
    ) -> bool:
        """
        Delete a chapter's generated audio and reset it to pending.

        Args:
            task_id: task ID
            chapter_index: chapter number
            delete_file: whether to also remove the file from disk

        Returns:
            whether the chapter was found and reset
        """
        task = self.get_task(task_id)
        if not task:
            return False

        for chapter in task.chapters:
            if chapter.index != chapter_index:
                continue

            path = chapter.audio_path
            if delete_file and path:
                self._remove_chapter_files(path)

            chapter.audio_path = None
            chapter.status = TaskStatus.PENDING
            chapter.error = None
            chapter.started_at = None
            chapter.completed_at = None
            task.completed_chapters = sum(
                1 for item in task.chapters if item.status == TaskStatus.COMPLETED
            )
            # A completed task no longer has a disk record. Reopen it so the
            # deletion survives a restart and the chapter can be regenerated.
            if task.status == TaskStatus.COMPLETED:
                task.status = TaskStatus.PARSED
                task.completed_at = None

            logger.info(t("task.chapter_audio_deleted", task_id=task_id, index=chapter_index))
            self._save_record(task_id)
            return True

        return False

    def delete_task(self, task_id: str, delete_files: bool = True) -> bool:
        """
        Delete a whole task, its generated audio, and its persisted record.

        Uploaded source files are intentionally kept; they may be the user's
        original book and are not owned by the task record.
        """
        task = self.get_task(task_id)
        if not task:
            return False

        running = self.running_tasks.pop(task_id, None)
        if running and not running.done():
            running.cancel()

        if delete_files:
            for chapter in task.chapters:
                if chapter.audio_path:
                    self._remove_chapter_files(chapter.audio_path)

        self.tasks.pop(task_id, None)
        self._delete_record(task_id)
        logger.info(t("task.task_deleted", task_id=task_id))
        return True

    @staticmethod
    def _remove_chapter_files(audio_path: str) -> None:
        """Remove the audio file and its sibling text exports."""
        path = Path(audio_path)
        candidates = [
            path,
            path.with_suffix(".txt"),
            path.with_name(path.stem + "-raw.txt"),
            path.with_name(path.stem + "-原文.txt"),
            path.with_name(path.stem + "-LLM.txt"),
        ]
        for candidate in candidates:
            try:
                candidate.unlink(missing_ok=True)
            except OSError as error:
                logger.warning(
                    t("task.audio_delete_failed", path=candidate, error=error)
                )

    def _record_path(self, task_id: str) -> Path:
        return self.record_dir / f"{task_id}.json"

    @staticmethod
    def _iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    def _serialize_record(self, task: Task) -> Dict[str, Any]:
        """Build a JSON-safe snapshot of the task."""
        return {
            "task_id": task.task_id,
            "status": task.status.value if hasattr(task.status, "value") else task.status,
            "total_chapters": task.total_chapters,
            "completed_chapters": task.completed_chapters,
            "error": task.error,
            "created_at": self._iso(task.created_at),
            "started_at": self._iso(task.started_at),
            "completed_at": self._iso(task.completed_at),
            "metadata": task.metadata,
            "chapters": [
                {
                    "index": chapter.index,
                    "title": chapter.title,
                    "status": chapter.status.value if hasattr(chapter.status, "value") else chapter.status,
                    "audio_path": chapter.audio_path,
                    "error": chapter.error,
                    "started_at": self._iso(chapter.started_at),
                    "completed_at": self._iso(chapter.completed_at),
                }
                for chapter in task.chapters
            ],
        }

    def _save_record(self, task_id: str) -> None:
        """Write the task record atomically; remove it once the task completes."""
        if not self.persist:
            return

        task = self.get_task(task_id)
        if not task:
            return

        if task.status == TaskStatus.COMPLETED:
            self._delete_record(task_id)
            return

        try:
            self.record_dir.mkdir(parents=True, exist_ok=True)
            path = self._record_path(task_id)
            temp_path = path.with_suffix(".json.tmp")
            temp_path.write_text(
                json.dumps(self._serialize_record(task), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temp_path, path)
        except (OSError, TypeError) as error:
            logger.warning(t("task.record_save_failed", task_id=task_id, error=error))

    def _delete_record(self, task_id: str) -> None:
        """Remove a task record from disk."""
        if not self.persist:
            return

        try:
            self._record_path(task_id).unlink(missing_ok=True)
        except OSError as error:
            logger.warning(t("task.record_delete_failed", task_id=task_id, error=error))

    def _load_records(self) -> None:
        """Restore tasks from the cache directory on startup."""
        if not self.persist or not self.record_dir.is_dir():
            return

        cutoff = None
        if config.TASK_RESULT_TTL > 0:
            cutoff = datetime.now() - timedelta(seconds=config.TASK_RESULT_TTL)

        for path in sorted(self.record_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                task = self._deserialize_record(data)
            except Exception as error:
                logger.warning(t("task.record_load_failed", path=path, error=error))
                continue

            if task.status == TaskStatus.COMPLETED:
                path.unlink(missing_ok=True)
                continue

            if cutoff and task.created_at < cutoff:
                path.unlink(missing_ok=True)
                logger.info(t("task.record_expired", task_id=task.task_id))
                continue

            # A restart kills running jobs; resume from the last finished chapter
            if task.status == TaskStatus.GENERATING:
                for chapter in task.chapters:
                    if chapter.status == TaskStatus.GENERATING:
                        chapter.status = TaskStatus.PENDING
                        chapter.started_at = None
                task.status = TaskStatus.PAUSED

            task.pause_requested = False
            self.tasks[task.task_id] = task
            logger.info(t("task.record_restored", task_id=task.task_id))
            self._save_record(task.task_id)

    def _deserialize_record(self, data: Dict[str, Any]) -> Task:
        """Rebuild a task object from a saved record."""
        def parse_time(value):
            return datetime.fromisoformat(value) if value else None

        chapters = [
            ChapterProgress(
                index=item.get("index"),
                title=item.get("title") or "",
                status=TaskStatus(item.get("status") or TaskStatus.PENDING.value),
                audio_path=item.get("audio_path"),
                error=item.get("error"),
                started_at=parse_time(item.get("started_at")),
                completed_at=parse_time(item.get("completed_at")),
            )
            for item in data.get("chapters", [])
        ]

        return Task(
            task_id=data["task_id"],
            status=TaskStatus(data.get("status") or TaskStatus.PENDING.value),
            total_chapters=data.get("total_chapters", len(chapters)),
            completed_chapters=data.get("completed_chapters", 0),
            chapters=chapters,
            error=data.get("error"),
            created_at=parse_time(data.get("created_at")) or datetime.now(),
            started_at=parse_time(data.get("started_at")),
            completed_at=parse_time(data.get("completed_at")),
            metadata=data.get("metadata") or {},
        )

    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """
        Get task progress

        Args:
            task_id: task ID

        Returns:
            progress info dictionary
        """
        task = self.get_task(task_id)
        if not task:
            return {}

        def serialize_chapter(chapter):
            if isinstance(chapter, dict):
                status = chapter.get("status")
                return {
                    "index": chapter.get("index"),
                    "title": chapter.get("title"),
                    "status": status.value if hasattr(status, "value") else status,
                    "audio_path": chapter.get("audio_path"),
                    "error": chapter.get("error"),
                    "started_at": chapter.get("started_at"),
                    "completed_at": chapter.get("completed_at"),
                }

            return {
                "index": chapter.index,
                "title": chapter.title,
                "status": chapter.status.value if hasattr(chapter.status, "value") else chapter.status,
                "audio_path": chapter.audio_path,
                "error": chapter.error,
                "started_at": chapter.started_at.isoformat() if chapter.started_at else None,
                "completed_at": chapter.completed_at.isoformat() if chapter.completed_at else None,
            }

        return {
            "task_id": task.task_id,
            "status": task.status,
            "total_chapters": task.total_chapters,
            "completed_chapters": task.completed_chapters,
            "progress": task.completed_chapters / task.total_chapters if task.total_chapters > 0 else 0,
            "chapters": [serialize_chapter(chapter) for chapter in task.chapters],
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error
        }
