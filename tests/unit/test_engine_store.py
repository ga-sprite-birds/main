"""Unit tests for task persistence, transitions, recovery, and cleanup."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.models import InvalidTransitionError
from engine.store import TaskStore
from system.db import connect_tasks_db

pytestmark = pytest.mark.unit


def make_store(tmp_path: Path) -> TaskStore:
    return TaskStore(tmp_path / "data" / "tasks.db")


def test_task_and_chapters_round_trip(tmp_path):
    store = make_store(tmp_path)
    try:
        task = store.create_task(
            "audiobook", {"file_path": "book.txt"}, idempotency_key="book-1"
        )
        assert task["status"] == "pending"
        assert store.create_task(
            "audiobook", {"file_path": "other.txt"}, idempotency_key="book-1"
        )["task_id"] == task["task_id"]

        store.replace_chapters(
            task["task_id"],
            [
                {"index": 1, "title": "Chapter 1", "content": "one"},
                {"index": 2, "title": "Chapter 2", "content": "two"},
            ],
        )
        store.update_chapter(
            task["task_id"],
            1,
            status="succeeded",
            audio_path=str(tmp_path / "1.mp3"),
        )
        refreshed = store.require_task(task["task_id"])
        assert refreshed["total_chapters"] == 2
        assert refreshed["completed_chapters"] == 1
        assert store.get_chapter(task["task_id"], 2)["status"] == "pending"

        page = store.list_tasks(page=1, page_size=1)
        assert page["total"] == 1
        assert len(page["list"]) == 1
        assert page["page_size"] == 1
    finally:
        store.close()


def test_invalid_transition_is_rejected(tmp_path):
    store = make_store(tmp_path)
    try:
        task = store.create_task("audiobook")
        with pytest.raises(InvalidTransitionError):
            store.update_task(task["task_id"], status="running")
    finally:
        store.close()


def test_running_task_is_requeued_on_recovery_but_paused_is_kept(tmp_path):
    store = make_store(tmp_path)
    try:
        running = store.create_task("audiobook", phase="generating")
        store.replace_chapters(
            running["task_id"], [{"index": 1, "title": "One", "content": "x"}]
        )
        store.transition(running["task_id"], "queued")
        assert store.claim_queued_task(running["task_id"]) is not None

        paused = store.create_task("audiobook", phase="paused", status="paused")

        recovered = store.recover_interrupted_tasks()
        assert recovered == [running["task_id"]]
        assert store.require_task(running["task_id"])["status"] == "queued"
        assert store.require_task(paused["task_id"])["status"] == "paused"
        assert store.get_chapter(running["task_id"], 1)["status"] == "pending"
    finally:
        store.close()


def test_resume_clears_control_and_resets_interrupted_chapters(tmp_path):
    store = make_store(tmp_path)
    try:
        task = store.create_task("audiobook")
        store.replace_chapters(
            task["task_id"], [{"index": 1, "title": "One", "content": "x"}]
        )
        store.transition(task["task_id"], "queued")
        store.claim_queued_task(task["task_id"])
        store.update_chapter(task["task_id"], 1, status="running")
        store.set_control(task["task_id"], pause_requested=True)
        store.transition(task["task_id"], "paused")

        resumed = store.resume_paused_task(task["task_id"])
        assert resumed["status"] == "queued"
        assert "control" not in resumed["params"]
        assert store.get_chapter(task["task_id"], 1)["status"] == "pending"
    finally:
        store.close()


def test_command_log_is_ordered_idempotent_and_cleanup_is_bounded(tmp_path):
    store = make_store(tmp_path)
    try:
        store.record_command("c1", "system.info", "hash", {"code": 0})
        record = store.get_command("c1")
        assert record["result"] == {"code": 0}
        assert record["status"] == "completed"

        task = store.create_task("audiobook")
        store.transition(task["task_id"], "removed", phase="removed")
        connection = connect_tasks_db(tmp_path / "data" / "tasks.db")
        try:
            with connection:
                connection.execute(
                    "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
                    ("2000-01-01T00:00:00Z", task["task_id"]),
                )
        finally:
            connection.close()
        preview = store.cleanup_terminal_tasks(1, dry_run=True)
        assert task["task_id"] in preview["removed_task_ids"]
        removed = store.cleanup_terminal_tasks(1)
        assert task["task_id"] in removed["removed_task_ids"]
        assert store.get_task(task["task_id"]) is None
    finally:
        store.close()


def test_reopen_generation_applies_new_options(tmp_path):
    """Re-running a finished task must store the new generation options."""
    store = make_store(tmp_path)
    try:
        task = store.create_task("audiobook", {"file_path": "book.txt"})
        store.replace_chapters(
            task["task_id"],
            [
                {"index": 1, "title": "One", "content": "x"},
                {"index": 2, "title": "Two", "content": "y"},
            ],
        )

        store.queue_for_generation(
            task["task_id"], options={"chapter_indexes": [1]}
        )
        assert store.claim_queued_task(task["task_id"]) is not None
        store.update_task(task["task_id"], status="succeeded", phase="completed")

        store.queue_for_generation(
            task["task_id"],
            options={"chapter_indexes": [2], "chapter_intro_outro": False},
            reopen=True,
        )
        reopened = store.require_task(task["task_id"])
        generation = reopened["params"]["generation"]
        assert reopened["status"] == "queued"
        assert generation["chapter_indexes"] == [2]
        assert generation["chapter_intro_outro"] is False
    finally:
        store.close()
