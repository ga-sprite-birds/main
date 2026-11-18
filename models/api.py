"""Pydantic models for the thin v2 control API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CommandMeta(BaseModel):
    command_id: str | None = None


class ParseRequest(CommandMeta):
    task_id: str = Field(min_length=1)
    language: str | None = None


class GenerateRequest(CommandMeta):
    task_id: str = Field(min_length=1)
    voice: str | None = None
    output_path: str | None = None
    enable_llm: bool | None = None
    rate: float | None = Field(default=None, ge=0.5, le=2.0)
    prosody_mode: str | None = None
    language: str | None = None
    chapter_intro_outro: bool | None = None
    chapter_lead_in_enabled: bool | None = None
    chapter_indexes: list[int] | None = None
    multi_voice: bool | None = None
    character_template: str | None = None


class TaskCommandRequest(CommandMeta):
    task_id: str = Field(min_length=1)


class RemoveTaskRequest(CommandMeta):
    delete_outputs: bool = False


class CleanupRequest(CommandMeta):
    ttl_seconds: int | None = Field(default=None, ge=0)
    dry_run: bool = False
    delete_outputs: bool = False


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class CommandEnvelope(BaseModel):
    code: int
    msg: str
    data: Any
