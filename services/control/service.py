"""Shared control-plane operations for HTTP API and CLI."""

from __future__ import annotations

from typing import Any, Mapping

from services.control.client import EngineClient
from services.task_query_service import TaskQueryService


class ControlService:
    def __init__(
        self,
        client: EngineClient | None = None,
        query: TaskQueryService | None = None,
    ) -> None:
        self.client = client or EngineClient()
        self.query = query or TaskQueryService()

    def add_task(
        self,
        params: Mapping[str, Any],
        *,
        task_type: str = "audiobook",
        command_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self.client.command(
            "task.add",
            {
                "type": task_type,
                "params": dict(params),
                "idempotency_key": idempotency_key,
            },
            command_id=command_id,
        )

    def parse(self, task_id: str, *, command_id: str | None = None) -> dict[str, Any]:
        return self.client.command(
            "task.parse", {"task_id": task_id}, command_id=command_id
        )

    def generate(
        self,
        task_id: str,
        options: Mapping[str, Any],
        *,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        return self.client.command(
            "task.generate",
            {"task_id": task_id, **dict(options)},
            command_id=command_id,
        )

    def pause(self, task_id: str, *, command_id: str | None = None) -> dict[str, Any]:
        return self.client.command(
            "task.pause", {"task_id": task_id}, command_id=command_id
        )

    def resume(self, task_id: str, *, command_id: str | None = None) -> dict[str, Any]:
        return self.client.command(
            "task.resume", {"task_id": task_id}, command_id=command_id
        )

    def cancel(self, task_id: str, *, command_id: str | None = None) -> dict[str, Any]:
        return self.client.command(
            "task.cancel", {"task_id": task_id}, command_id=command_id
        )

    def retry(self, task_id: str, *, command_id: str | None = None) -> dict[str, Any]:
        return self.client.command(
            "task.retry", {"task_id": task_id}, command_id=command_id
        )

    def remove(
        self,
        task_id: str,
        *,
        delete_outputs: bool = False,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        return self.client.command(
            "task.remove",
            {"task_id": task_id, "delete_outputs": delete_outputs},
            command_id=command_id,
        )

    def remove_chapter(
        self,
        task_id: str,
        chapter_index: int,
        *,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        return self.client.command(
            "task.chapter.remove",
            {"task_id": task_id, "chapter_index": chapter_index},
            command_id=command_id,
        )

    def cleanup(
        self,
        *,
        ttl_seconds: int | None = None,
        dry_run: bool = False,
        delete_outputs: bool = False,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {"dry_run": dry_run, "delete_outputs": delete_outputs}
        if ttl_seconds is not None:
            payload["ttl_seconds"] = ttl_seconds
        return self.client.command(
            "task.cleanup", payload, command_id=command_id
        )

    def update_options(
        self,
        task_id: str,
        options: Mapping[str, Any],
        *,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        return self.client.command(
            "task.update_options",
            {"task_id": task_id, "options": dict(options)},
            command_id=command_id,
        )

    def status(self, task_id: str) -> dict[str, Any] | None:
        return self.query.get_task_view(task_id)

    def list_tasks(self, **filters: Any) -> dict[str, Any]:
        return self.query.list_tasks(**filters)

    def events(
        self, task_id: str, *, after_id: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self.query.list_events(task_id, after_id=after_id, limit=limit)
