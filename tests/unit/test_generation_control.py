"""
Tests for chapter-level generation controls: pause, resume, and delete.
"""

import sys
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Dynamically import fcgi-bin.api
api_path = project_root / "fcgi-bin" / "api.py"
spec = importlib.util.spec_from_file_location("api", api_path)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

client = TestClient(api_module.app)
TaskStatus = api_module.TaskStatus
ChapterProgress = api_module.ChapterProgress


def _create_task_with_chapters(count):
    """Create an in-memory task with the given number of chapters."""
    task_id = api_module.task_manager.create_task()
    task = api_module.task_manager.get_task(task_id)
    for index in range(1, count + 1):
        task.chapters.append(ChapterProgress(index=index, title=f"Chapter {index}"))
    task.total_chapters = count
    return task_id


@pytest.mark.unit
def test_mark_chapters_paused_only_touches_pending():
    """Pausing marks pending chapters as paused but leaves others untouched."""
    task_id = _create_task_with_chapters(3)
    task = api_module.task_manager.get_task(task_id)
    api_module.task_manager.update_chapter_status(
        task_id, 1, TaskStatus.COMPLETED, audio_path="/tmp/one.mp3"
    )

    api_module.task_manager.mark_chapters_paused(task_id)

    assert task.chapters[0].status == TaskStatus.COMPLETED
    assert task.chapters[1].status == TaskStatus.PAUSED
    assert task.chapters[2].status == TaskStatus.PAUSED


@pytest.mark.unit
def test_delete_chapter_audio_removes_file_and_resets(tmp_path):
    """Deleting a chapter removes the mp3 and resets the chapter to pending."""
    task_id = _create_task_with_chapters(2)
    audio_file = tmp_path / "1.mp3"
    audio_file.write_bytes(b"audio")

    api_module.task_manager.update_chapter_status(
        task_id, 1, TaskStatus.COMPLETED, audio_path=str(audio_file)
    )
    task = api_module.task_manager.get_task(task_id)
    assert task.completed_chapters == 1

    assert api_module.task_manager.delete_chapter_audio(task_id, 1) is True

    assert not audio_file.exists()
    assert task.chapters[0].status == TaskStatus.PENDING
    assert task.chapters[0].audio_path is None
    assert task.completed_chapters == 0


@pytest.mark.unit
def test_delete_chapter_audio_unknown_chapter():
    """Deleting a chapter that does not exist returns False."""
    task_id = _create_task_with_chapters(1)
    assert api_module.task_manager.delete_chapter_audio(task_id, 99) is False


@pytest.mark.unit
def test_completed_count_does_not_drift():
    """Re-marking an already completed chapter does not inflate the counter."""
    task_id = _create_task_with_chapters(1)
    for _ in range(3):
        api_module.task_manager.update_chapter_status(task_id, 1, TaskStatus.COMPLETED)
    task = api_module.task_manager.get_task(task_id)
    assert task.completed_chapters == 1


@pytest.mark.unit
def test_pause_requires_generating():
    """Pausing a non-generating task is rejected."""
    task_id = _create_task_with_chapters(1)
    response = client.post(f"/task/{task_id}/pause")
    assert response.status_code == 409


@pytest.mark.unit
def test_pause_unknown_task():
    """Pausing an unknown task returns 404."""
    response = client.post("/task/unknown-task/pause")
    assert response.status_code == 404


@pytest.mark.unit
def test_resume_requires_paused():
    """Resuming a task that is not paused is rejected."""
    task_id = _create_task_with_chapters(1)
    response = client.post(f"/task/{task_id}/resume")
    assert response.status_code == 409


@pytest.mark.unit
def test_delete_chapter_via_api():
    """The DELETE endpoint resets the chapter and reports success."""
    task_id = _create_task_with_chapters(2)
    response = client.delete(f"/task/{task_id}/chapter/2")
    assert response.status_code == 200
    assert response.json()["chapter_index"] == 2

    task = api_module.task_manager.get_task(task_id)
    assert task.chapters[1].status == TaskStatus.PENDING


@pytest.mark.unit
def test_delete_chapter_unknown_returns_404():
    """Deleting an unknown chapter returns 404."""
    task_id = _create_task_with_chapters(1)
    response = client.delete(f"/task/{task_id}/chapter/99")
    assert response.status_code == 404
