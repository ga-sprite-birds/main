"""Cooperative task scheduler for the Core engine."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from engine.handlers.generate import run_generation
from engine.handlers.parse import run_parse
from engine.store import TaskStore
from system.config import settings

logger = logging.getLogger(__name__)


class Scheduler:
    """Runs queued generation tasks with a bounded worker pool."""

    def __init__(
        self,
        store: TaskStore,
        *,
        max_concurrent: int = 2,
        grace_seconds: float = 30.0,
        poll_seconds: float = 0.5,
        cleanup_ttl_seconds: int = 0,
        cleanup_interval_seconds: float = 3600.0,
        upload_dir: str | Path | None = None,
    ) -> None:
        self.store = store
        self.upload_dir = Path(upload_dir or settings.API_UPLOAD_DIR)
        self.max_concurrent = max(1, max_concurrent)
        self.grace_seconds = max(0.0, grace_seconds)
        self.poll_seconds = max(0.1, poll_seconds)
        self.cleanup_ttl_seconds = max(0, cleanup_ttl_seconds)
        self.cleanup_interval_seconds = max(60.0, cleanup_interval_seconds)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_task: asyncio.Task | None = None
        self._jobs: dict[str, asyncio.Task] = {}
        self._wake = asyncio.Event()
        self._shutdown = asyncio.Event()
        self._pause_ids: set[str] = set()
        self._cancel_ids: set[str] = set()
        self._last_heartbeat: dict[str, float] = {}
        self._last_cleanup: float | None = None
        self._parse_queue: asyncio.Queue[str] = asyncio.Queue()
        self._parse_task: asyncio.Task | None = None

    @property
    def active_count(self) -> int:
        return len(self._jobs)

    @property
    def active_task_ids(self) -> list[str]:
        return sorted(self._jobs)

    def start(self) -> None:
        if self._loop_task is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._shutdown.clear()
        self._loop_task = asyncio.create_task(
            self._run_loop(), name="engine-scheduler"
        )
        self._parse_task = asyncio.create_task(
            self._parse_loop(), name="engine-parse-worker"
        )

    def wake(self) -> None:
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._wake.set)

    def submit_parse(self, task_id: str) -> None:
        """Queue a background parse job; safe to call from any thread."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._parse_queue.put_nowait, task_id)
        else:
            self._parse_queue.put_nowait(task_id)

    async def _parse_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                task_id = await self._parse_queue.get()
            except asyncio.CancelledError:
                break
            try:
                await run_parse(self.store, task_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Parse worker failed for task %s", task_id)

    def request_pause(self, task_id: str) -> None:
        self._pause_ids.add(task_id)
        self.store.set_control(task_id, pause_requested=True)
        self.wake()
        logger.info("Pause requested for task %s", task_id)

    def request_cancel(self, task_id: str) -> None:
        self._cancel_ids.add(task_id)
        self.store.set_control(task_id, cancel_requested=True)
        self.wake()
        logger.info("Cancel requested for task %s", task_id)

    def _should_pause(self, task_id: str) -> bool:
        if task_id in self._pause_ids:
            return True
        task = self.store.get_task(task_id)
        return bool(
            task
            and (task["params"].get("control") or {}).get("pause_requested")
        )

    def _should_cancel(self, task_id: str) -> bool:
        if task_id in self._cancel_ids:
            return True
        task = self.store.get_task(task_id)
        return bool(
            task
            and (task["params"].get("control") or {}).get("cancel_requested")
        )

    async def _run_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                started_any = False
                while len(self._jobs) < self.max_concurrent:
                    task_id = self.store.next_queued_task_id()
                    if task_id is None:
                        break
                    claimed = self.store.claim_queued_task(task_id)
                    if claimed is None:
                        continue
                    job = asyncio.create_task(
                        self._execute(task_id), name=f"task-{task_id}"
                    )
                    self._jobs[task_id] = job
                    self._last_heartbeat[task_id] = time.monotonic()
                    started_any = True

                self._heartbeat_active()
                self._maybe_cleanup()
                if started_any:
                    await asyncio.sleep(0)
                    continue
                try:
                    await asyncio.wait_for(
                        self._wake.wait(), timeout=self.poll_seconds
                    )
                except asyncio.TimeoutError:
                    pass
                self._wake.clear()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Scheduler loop error")
                await asyncio.sleep(self.poll_seconds)

    def _heartbeat_active(self) -> None:
        now = time.monotonic()
        for task_id in list(self._jobs):
            if now - self._last_heartbeat.get(task_id, 0.0) < 10.0:
                continue
            try:
                self.store.heartbeat(task_id)
            except Exception:
                logger.exception("Heartbeat failed for task %s", task_id)
            self._last_heartbeat[task_id] = now

    def _maybe_cleanup(self) -> None:
        """Drop terminal task records past TASK_RESULT_TTL, at most once per interval."""
        if self.cleanup_ttl_seconds <= 0:
            return
        now = time.monotonic()
        if (
            self._last_cleanup is not None
            and now - self._last_cleanup < self.cleanup_interval_seconds
        ):
            return
        self._last_cleanup = now
        try:
            result = self.store.cleanup_terminal_tasks(
                self.cleanup_ttl_seconds, dry_run=False
            )
            self.store.cleanup_command_log(self.cleanup_ttl_seconds)
            self.store.cleanup_uploads(
                self.upload_dir, self.cleanup_ttl_seconds
            )
        except Exception:
            logger.exception("Periodic cleanup failed")
            return
        if result.get("removed_task_ids"):
            logger.info(
                "Periodic cleanup removed %d task(s)",
                len(result["removed_task_ids"]),
            )

    async def _execute(self, task_id: str) -> None:
        try:
            await run_generation(
                self.store,
                task_id,
                should_pause=lambda: self._should_pause(task_id),
                should_cancel=lambda: self._should_cancel(task_id),
            )
        except asyncio.CancelledError:
            # Leave the persisted state as running. Recovery requeues it so the
            # next Core starts from the last succeeded chapter checkpoint.
            logger.warning("Generation worker canceled for task %s", task_id)
            raise
        except Exception as exc:
            logger.exception("Unhandled generation error for task %s", task_id)
            task = self.store.get_task(task_id)
            if task and task["status"] == "running":
                try:
                    self.store.update_task(
                        task_id,
                        status="failed",
                        phase="failed",
                        error=str(exc),
                    )
                    self.store.add_event(
                        task_id, "task.failed", {"error": str(exc)}
                    )
                except Exception:
                    logger.exception("Failed to mark task %s failed", task_id)
        finally:
            self._jobs.pop(task_id, None)
            self._last_heartbeat.pop(task_id, None)
            self._pause_ids.discard(task_id)
            self._cancel_ids.discard(task_id)
            self.wake()

    async def stop(self) -> None:
        """Stop accepting work, then wait for chapters or cancel at the grace limit."""
        self._shutdown.set()
        self.wake()
        if self._parse_task is not None:
            self._parse_task.cancel()
            await asyncio.gather(self._parse_task, return_exceptions=True)
            self._parse_task = None
        if self._loop_task is not None:
            await asyncio.gather(self._loop_task, return_exceptions=True)
            self._loop_task = None

        if not self._jobs:
            return
        jobs = list(self._jobs.values())
        done, pending = await asyncio.wait(
            jobs, timeout=self.grace_seconds
        )
        for job in pending:
            job.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        if done:
            await asyncio.gather(*done, return_exceptions=True)

    def stats(self) -> dict[str, Any]:
        return {
            "max_concurrent": self.max_concurrent,
            "active_count": self.active_count,
            "active_task_ids": self.active_task_ids,
        }
