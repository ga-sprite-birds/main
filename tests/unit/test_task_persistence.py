"""
Tests for on-disk task persistence (cache/*.json).
"""

import json
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from ga_birds.Task import ChapterProgress, TaskManager, TaskStatus


def _manager(tmp_path, monkeypatch):
    """Create a manager whose records live in the test temp directory."""
    monkeypatch.setattr(config, "TASK_CACHE_DIR", str(tmp_path))
    return TaskManager()


def _task_with_chapters(manager, count=2):
    task_id = manager.create_task(metadata={"filename": "book.md"})
    task = manager.get_task(task_id)
    task.total_chapters = count
    task.chapters = [
        ChapterProgress(index=index, title=f"Chapter {index}")
        for index in range(1, count + 1)
    ]
    manager.update_task_status(task_id, TaskStatus.PARSED)
    return task_id


@pytest.mark.unit
def test_record_is_written_as_json(tmp_path, monkeypatch):
    """Task state is persisted as readable JSON."""
    manager = _manager(tmp_path, monkeypatch)
    task_id = _task_with_chapters(manager)
    manager.update_chapter_status(
        task_id, 1, TaskStatus.COMPLETED, audio_path="/tmp/1.mp3"
    )

    path = tmp_path / f"{task_id}.json"
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["task_id"] == task_id
    assert data["status"] == "parsed"
    assert data["metadata"]["filename"] == "book.md"
    assert data["chapters"][0]["status"] == "completed"
    assert data["chapters"][0]["audio_path"] == "/tmp/1.mp3"


@pytest.mark.unit
def test_record_is_restored_on_startup(tmp_path, monkeypatch):
    """A new manager restores tasks from the cache directory."""
    first = _manager(tmp_path, monkeypatch)
    task_id = _task_with_chapters(first)
    first.update_chapter_status(task_id, 1, TaskStatus.COMPLETED, audio_path="/tmp/1.mp3")

    second = TaskManager()
    restored = second.get_task(task_id)

    assert restored is not None
    assert restored.status == TaskStatus.PARSED
    assert restored.total_chapters == 2
    assert restored.completed_chapters == 1
    assert restored.metadata["filename"] == "book.md"
    assert restored.chapters[0].status == TaskStatus.COMPLETED


@pytest.mark.unit
def test_interrupted_generation_becomes_paused(tmp_path, monkeypatch):
    """A task that was generating during shutdown is restored as paused."""
    first = _manager(tmp_path, monkeypatch)
    task_id = _task_with_chapters(first)
    first.update_task_status(task_id, TaskStatus.GENERATING)
    first.update_chapter_status(task_id, 1, TaskStatus.COMPLETED)
    first.update_chapter_status(task_id, 2, TaskStatus.GENERATING)

    second = TaskManager()
    restored = second.get_task(task_id)

    assert restored.status == TaskStatus.PAUSED
    assert restored.chapters[1].status == TaskStatus.PENDING
    assert restored.chapters[1].started_at is None


@pytest.mark.unit
def test_record_is_deleted_when_task_completes(tmp_path, monkeypatch):
    """Completing a task removes its record from the cache directory."""
    manager = _manager(tmp_path, monkeypatch)
    task_id = _task_with_chapters(manager)
    path = tmp_path / f"{task_id}.json"
    assert path.exists()

    manager.update_chapter_status(task_id, 1, TaskStatus.COMPLETED)
    manager.update_chapter_status(task_id, 2, TaskStatus.COMPLETED)
    manager.update_task_status(task_id, TaskStatus.COMPLETED)

    assert not path.exists()
