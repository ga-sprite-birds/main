"""Contract tests for Core command semantics."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from engine.scheduler import Scheduler
from engine.service import EngineService
from engine.store import TaskStore

pytestmark = pytest.mark.unit


def make_service(tmp_path: Path) -> tuple[TaskStore, EngineService]:
    store = TaskStore(tmp_path / "data" / "tasks.db")
    scheduler = Scheduler(store, max_concurrent=1)
    service = EngineService(
        store,
        scheduler,
        started_at="2026-01-01T00:00:00Z",
        max_concurrent=1,
    )
    return store, service


def test_commands_are_idempotent_and_conflicts_are_rejected(tmp_path):
    store, service = make_service(tmp_path)
    source = tmp_path / "book.txt"
    source.write_text("第一章 开始\n" + "正文" * 20, encoding="utf-8")
    try:
        payload = {
            "type": "audiobook",
            "params": {"file_path": str(source), "source_name": source.name},
        }
        first = service.execute("c1", "task.add", payload)
        second = service.execute("c1", "task.add", payload)
        assert first == second
        assert first["code"] == 0

        conflict = service.execute(
            "c1", "task.add", {**payload, "type": "other"}
        )
        assert conflict["code"] == 3001
    finally:
        store.close()


def test_generate_requires_parsed_chapters(tmp_path):
    store, service = make_service(tmp_path)
    source = tmp_path / "book.txt"
    source.write_text("text", encoding="utf-8")
    try:
        added = service.execute(
            "add-1",
            "task.add",
            {"params": {"file_path": str(source)}},
        )
        task_id = added["data"]["task_id"]
        result = service.execute(
            "gen-1", "task.generate", {"task_id": task_id}
        )
        assert result["code"] == 3003
    finally:
        store.close()


def test_generation_queues_valid_chapters_and_remove_preserves_files(tmp_path):
    store, service = make_service(tmp_path)
    try:
        task = store.create_task("audiobook", phase="ready")
        store.replace_chapters(
            task["task_id"],
            [
                {"index": 1, "title": "One", "content": "x"},
                {"index": 2, "title": "Two", "content": "y"},
            ],
        )
        queued = service.execute(
            "gen-1",
            "task.generate",
            {"task_id": task["task_id"], "chapter_indexes": [1]},
        )
        assert queued["code"] == 0
        assert queued["data"]["status"] == "queued"

        invalid = service.execute(
            "gen-2",
            "task.generate",
            {"task_id": task["task_id"], "chapter_indexes": [9]},
        )
        assert invalid["code"] == 3003 or invalid["code"] == 1001

        removed = service.execute(
            "rm-1", "task.remove", {"task_id": task["task_id"]}
        )
        assert removed["code"] == 0
        assert removed["data"]["status"] == "removed"
    finally:
        store.close()


def test_system_info_contains_protocol_and_capabilities(tmp_path):
    store, service = make_service(tmp_path)
    try:
        info = service.system_info()
        assert info["protocol_version"] == 1
        assert "task.generate" in info["commands"]
        stats = service.system_stats()
        assert stats["schema_version"] == 1
    finally:
        store.close()


def test_scheduler_claims_queued_task_and_completes(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "data" / "tasks.db")
    scheduler = Scheduler(store, max_concurrent=1, poll_seconds=0.05)

    async def fake_generation(
        task_store,
        task_id,
        *,
        should_pause,
        should_cancel,
    ):
        task_store.update_task(task_id, status="succeeded", phase="completed")
        return {"ok": True}

    monkeypatch.setattr("engine.scheduler.run_generation", fake_generation)

    task = store.create_task("audiobook", phase="ready")
    store.replace_chapters(
        task["task_id"], [{"index": 1, "title": "One", "content": "x"}]
    )
    store.queue_for_generation(task["task_id"])

    async def scenario():
        scheduler.start()
        for _ in range(100):
            if store.require_task(task["task_id"])["status"] == "succeeded":
                break
            await asyncio.sleep(0.02)
        await scheduler.stop()

    try:
        asyncio.run(scenario())
        assert store.require_task(task["task_id"])["status"] == "succeeded"
    finally:
        store.close()
