"""Core command handlers shared by the local HTTP channel."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Mapping

from engine.scheduler import Scheduler
from engine.store import TaskStore
from models.task import task_view
from system.config import settings

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 1
ENGINE_VERSION = "2.0.0"
SUPPORTED_COMMANDS = (
    "task.add",
    "task.parse",
    "task.generate",
    "task.pause",
    "task.resume",
    "task.cancel",
    "task.retry",
    "task.remove",
    "task.cleanup",
    "task.update_options",
    "task.chapter.remove",
    "config.get",
    "config.set",
    "system.info",
    "system.stats",
)


class ControlError(ValueError):
    def __init__(
        self,
        code: int,
        msg: str,
        data: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg
        self.data = dict(data or {})


class EngineService:
    """Validates and executes commands; owns no transport details."""

    def __init__(
        self,
        store: TaskStore,
        scheduler: Scheduler,
        *,
        started_at: str,
        max_concurrent: int,
    ) -> None:
        self.store = store
        self.scheduler = scheduler
        self.started_at = started_at
        self.max_concurrent = max_concurrent
        self._command_lock = __import__("threading").RLock()

    def system_info(self) -> dict[str, Any]:
        return {
            "app": "ga-sprite-birds",
            "engine_version": ENGINE_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "started_at": self.started_at,
            "commands": list(SUPPORTED_COMMANDS),
            "limits": {
                "max_concurrent": self.max_concurrent,
                "max_page_size": 100,
                "max_event_limit": 500,
            },
        }

    def system_stats(self) -> dict[str, Any]:
        return {
            **self.scheduler.stats(),
            "tasks": self.store.status_counts(),
            "schema_version": self.store.schema_version(),
            "uptime_seconds": max(0, int(time.time() - _iso_to_epoch(self.started_at))),
        }

    def execute(
        self,
        command_id: str,
        command: str,
        payload: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Execute one idempotent command and return a response envelope."""
        if not command_id:
            return {
                "code": 1001,
                "msg": "command_id is required",
                "data": {},
            }
        if not command or command not in SUPPORTED_COMMANDS:
            return {
                "code": 1001,
                "msg": "Unknown command",
                "data": {"command": command},
            }
        body = dict(payload or {})
        payload_hash = hashlib.sha256(
            json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

        with self._command_lock:
            existing = self.store.get_command(command_id)
            if existing is not None:
                if existing["payload_hash"] != payload_hash or (
                    existing["command"] != command
                ):
                    return {
                        "code": 3001,
                        "msg": "command_id was reused with different input",
                        "data": {"command_id": command_id},
                    }
                if existing["result"] is not None:
                    return existing["result"]

            try:
                data = self._dispatch(command, body)
                envelope = {"code": 0, "msg": "ok", "data": data}
            except ControlError as exc:
                envelope = {
                    "code": exc.code,
                    "msg": exc.msg,
                    "data": exc.data,
                }
            except Exception as exc:
                logger.exception("Command %s failed", command)
                envelope = {
                    "code": 4000,
                    "msg": "Internal engine error",
                    "data": {"error": str(exc)},
                }
            self.store.record_command(
                command_id, command, payload_hash, envelope
            )
            return envelope

    def _dispatch(self, command: str, payload: dict[str, Any]) -> Any:
        handlers = {
            "task.add": self._task_add,
            "task.parse": self._task_parse,
            "task.generate": self._task_generate,
            "task.pause": self._task_pause,
            "task.resume": self._task_resume,
            "task.cancel": self._task_cancel,
            "task.retry": self._task_retry,
            "task.remove": self._task_remove,
            "task.cleanup": self._task_cleanup,
            "task.update_options": self._task_update_options,
            "task.chapter.remove": self._task_chapter_remove,
            "config.get": self._config_get,
            "config.set": self._config_set,
            "system.info": lambda _: self.system_info(),
            "system.stats": lambda _: self.system_stats(),
        }
        return handlers[command](payload)

    def _require_task(self, task_id: Any) -> dict[str, Any]:
        if not isinstance(task_id, str) or not task_id:
            raise ControlError(1001, "task_id is required")
        task = self.store.get_task(task_id)
        if task is None:
            raise ControlError(3002, "Task not found", {"task_id": task_id})
        return task

    def _view(self, task_id: str) -> dict[str, Any]:
        task = self._require_task(task_id)
        return task_view(task, self.store.list_chapters(task_id))

    def _task_add(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_type = payload.get("type") or "audiobook"
        if not isinstance(task_type, str) or not task_type:
            raise ControlError(1001, "type must be a non-empty string")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            raise ControlError(1001, "params must be an object")
        file_path = params.get("file_path")
        if file_path is not None:
            if not isinstance(file_path, str) or not Path(file_path).is_file():
                raise ControlError(
                    1001,
                    "file_path does not exist",
                    {"file_path": file_path},
                )
            params["file_path"] = str(Path(file_path).expanduser().resolve())
        output_path = params.get("output_path")
        if output_path is not None and not isinstance(output_path, str):
            raise ControlError(1001, "output_path must be a string")
        task = self.store.create_task(
            task_type,
            params,
            task_id=payload.get("task_id"),
            phase=payload.get("phase") or "uploaded",
            idempotency_key=payload.get("idempotency_key"),
        )
        return task_view(task, [])

    def _task_parse(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["phase"] == "parsing":
            raise ControlError(3003, "Task is already parsing")
        if task["status"] in ("queued", "running"):
            raise ControlError(3003, "Task is busy")
        if task["status"] in ("succeeded", "canceled", "removed"):
            raise ControlError(
                3003, f"Task status {task['status']} cannot be parsed"
            )
        if any(
            chapter["audio_path"]
            for chapter in self.store.list_chapters(task["task_id"])
        ):
            raise ControlError(
                3003, "Task already has generated audio; remove it before re-parsing"
            )
        # Parse runs as a background engine job; the command returns immediately
        # and progress is observable through the task's ``phase`` field.
        self.store.update_task(task["task_id"], phase="parsing", error=None)
        self.scheduler.submit_parse(task["task_id"])
        return self._view(task["task_id"])

    def _validate_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        options: dict[str, Any] = {}
        voice = payload.get("voice")
        if voice is not None and (not isinstance(voice, str) or not voice.strip()):
            raise ControlError(1001, "voice must be a non-empty string")
        options["voice"] = voice
        output_path = payload.get("output_path")
        if output_path is not None and not isinstance(output_path, str):
            raise ControlError(1001, "output_path must be a string")
        options["output_path"] = output_path
        enable_llm = payload.get("enable_llm")
        if enable_llm is not None and type(enable_llm) is not bool:
            raise ControlError(1001, "enable_llm must be boolean")
        options["enable_llm"] = enable_llm

        chapter_intro_outro = payload.get("chapter_intro_outro")
        if chapter_intro_outro is not None and type(chapter_intro_outro) is not bool:
            raise ControlError(1001, "chapter_intro_outro must be boolean")
        options["chapter_intro_outro"] = chapter_intro_outro

        chapter_lead_in_enabled = payload.get("chapter_lead_in_enabled")
        if (
            chapter_lead_in_enabled is not None
            and type(chapter_lead_in_enabled) is not bool
        ):
            raise ControlError(1001, "chapter_lead_in_enabled must be boolean")
        options["chapter_lead_in_enabled"] = chapter_lead_in_enabled
        rate = payload.get("rate")
        if rate is not None:
            if type(rate) not in (int, float) or not 0.5 <= float(rate) <= 2.0:
                raise ControlError(1001, "rate must be between 0.5 and 2.0")
            rate = float(rate)
        options["rate"] = rate
        prosody = payload.get("prosody_mode")
        if prosody is not None:
            if prosody not in ("off", "pause", "prosody"):
                raise ControlError(1001, "Invalid prosody_mode")
        options["prosody_mode"] = prosody
        indexes = payload.get("chapter_indexes")
        if indexes is not None:
            if not isinstance(indexes, list) or not indexes:
                raise ControlError(1001, "chapter_indexes cannot be empty")
            if not all(type(index) is int and index > 0 for index in indexes):
                raise ControlError(1001, "chapter_indexes must be positive integers")
            options["chapter_indexes"] = sorted(set(indexes))
        else:
            options["chapter_indexes"] = None
        multi_voice = payload.get("multi_voice")
        if multi_voice is not None and type(multi_voice) is not bool:
            raise ControlError(1001, "multi_voice must be boolean")
        options["multi_voice"] = bool(multi_voice)
        character_template = payload.get("character_template")
        if character_template is not None and not isinstance(
            character_template, str
        ):
            raise ControlError(1001, "character_template must be a path string")
        options["character_template"] = character_template
        return options

    def _task_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] in ("running", "queued"):
            raise ControlError(3003, "Task is already running or queued")
        if task["status"] == "paused":
            raise ControlError(3003, "Use task.resume for a paused task")
        if not self.store.list_chapters(task["task_id"]):
            raise ControlError(3003, "Task has no chapters; parse it first")
        options = self._validate_generation(payload)
        available = {
            int(chapter["chapter_index"])
            for chapter in self.store.list_chapters(task["task_id"])
        }
        requested = options["chapter_indexes"]
        if requested is not None:
            invalid = sorted(set(requested) - available)
            if invalid:
                raise ControlError(
                    1001,
                    "Unknown chapter indexes",
                    {"chapter_indexes": invalid},
                )
        reopen = task["status"] in ("succeeded", "canceled")
        queued = self.store.queue_for_generation(
            task["task_id"], options=options, reopen=reopen
        )
        self.scheduler.wake()
        return task_view(queued, self.store.list_chapters(task["task_id"]))

    def _task_pause(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] != "running":
            raise ControlError(3003, "Only a running task can be paused")
        self.scheduler.request_pause(task["task_id"])
        return {"task_id": task["task_id"], "pause_requested": True}

    def _task_resume(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] != "paused":
            raise ControlError(3003, "Only a paused task can be resumed")
        queued = self.store.resume_paused_task(task["task_id"])
        self.scheduler.wake()
        return task_view(queued, self.store.list_chapters(task["task_id"]))

    def _task_cancel(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] == "running":
            self.scheduler.request_cancel(task["task_id"])
            result = {"task_id": task["task_id"], "cancel_requested": True}
        elif task["status"] in ("pending", "queued", "paused"):
            result = task_view(
                self.store.force_cancel(task["task_id"]),
                self.store.list_chapters(task["task_id"]),
            )
        else:
            raise ControlError(
                3003, f"Task status {task['status']} cannot be canceled"
            )
        return result

    def _task_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] != "failed":
            raise ControlError(3003, "Only a failed task can be retried")
        if not self.store.list_chapters(task["task_id"]):
            raise ControlError(3003, "Task has no chapters; parse it again")
        queued = self.store.queue_for_generation(task["task_id"], reopen=False)
        self.scheduler.wake()
        return task_view(queued, self.store.list_chapters(task["task_id"]))

    def _task_update_options(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] in ("running", "queued"):
            raise ControlError(3003, "Cannot update a running task")
        options = self._validate_generation(payload.get("options") or {})
        params = dict(task["params"])
        merged = dict(params.get("generation") or {})
        merged.update(options)
        params["generation"] = merged
        updated = self.store.update_task(task["task_id"], params=params)
        return task_view(updated, self.store.list_chapters(task["task_id"]))

    def _task_remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] == "running":
            raise ControlError(3003, "Cancel the running task before removing it")
        delete_outputs = payload.get("delete_outputs") is True
        audio_paths = [
            chapter["audio_path"]
            for chapter in self.store.list_chapters(task["task_id"])
            if chapter.get("audio_path")
        ]
        removed = self.store.transition(
            task["task_id"],
            "removed",
            phase="removed",
            event_type="task.removed",
        )
        if delete_outputs:
            for path in audio_paths:
                _remove_audio_and_text(path)
        return task_view(removed, self.store.list_chapters(task["task_id"]))

    def _task_chapter_remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._require_task(payload.get("task_id"))
        if task["status"] in ("running", "queued"):
            raise ControlError(3003, "Cannot remove a chapter while running")
        index = payload.get("chapter_index")
        if type(index) is not int:
            raise ControlError(1001, "chapter_index must be an integer")
        chapter = self.store.get_chapter(task["task_id"], index)
        if chapter is None:
            raise ControlError(
                3002,
                "Chapter not found",
                {"chapter_index": index},
            )
        if chapter.get("audio_path"):
            _remove_audio_and_text(str(chapter["audio_path"]))
        self.store.reset_chapter(task["task_id"], index)
        task = self.store.require_task(task["task_id"])
        if task["status"] in ("succeeded", "failed", "canceled"):
            self.store.reopen_for_generation(task["task_id"])
        return self._view(task["task_id"])

    def _task_cleanup(self, payload: dict[str, Any]) -> dict[str, Any]:
        ttl = payload.get("ttl_seconds", settings.TASK_RESULT_TTL)
        if type(ttl) is not int or ttl < 0:
            raise ControlError(1001, "ttl_seconds must be a non-negative integer")
        dry_run = payload.get("dry_run") is True
        delete_outputs = payload.get("delete_outputs") is True
        preview = self.store.cleanup_terminal_tasks(ttl, dry_run=True)
        artifacts: dict[str, list[str]] = {}
        if delete_outputs and not dry_run:
            for task_id in preview["removed_task_ids"]:
                artifacts[task_id] = [
                    chapter["audio_path"]
                    for chapter in self.store.list_chapters(task_id)
                    if chapter.get("audio_path")
                ]
        result = self.store.cleanup_terminal_tasks(ttl, dry_run=dry_run)
        if delete_outputs and not dry_run:
            for task_id in result["removed_task_ids"]:
                for audio_path in artifacts.get(task_id, []):
                    _remove_audio_and_text(audio_path)
        return result

    def _config_get(self, payload: dict[str, Any]) -> dict[str, Any]:
        import config

        service = config.get_config_service()
        key = payload.get("key")
        if key:
            return {"key": key, "value": service.get(key)}
        return {"values": service.get_all()}

    def _config_set(self, payload: dict[str, Any]) -> dict[str, Any]:
        import config

        values = payload.get("values")
        if not isinstance(values, dict):
            raise ControlError(1001, "values must be an object")
        try:
            return config.get_config_service().set(values)
        except Exception as exc:
            raise ControlError(
                1003,
                getattr(exc, "msg", str(exc)),
                getattr(exc, "details", {}),
            ) from exc


def _remove_audio_and_text(audio_path: str) -> None:
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
        except OSError:
            logger.warning("Unable to remove task artifact %s", candidate)


def _iso_to_epoch(value: str) -> float:
    from datetime import datetime

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return time.time()
