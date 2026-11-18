"""Thin v2 Control API.

All long-running execution lives in ``engine``. This process only accepts
uploads, forwards commands over the localhost channel, and reads ``tasks.db``
in read-only mode for status/history.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import hashlib
import hmac
import os
import sqlite3
from typing import Any, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from models.api import (
    CleanupRequest,
    CommandMeta,
    GenerateRequest,
    ParseRequest,
)
from routers import system_config, tts
from services.config_service import ConfigService
from services.control.client import EngineCommandError, EngineUnavailable
from services.control.service import ControlService
from system.config import PROJECT_ROOT, settings
from system.deps import get_config_service, get_control_service
from system.paths import (
    PathSafetyError,
    ensure_under,
    ensure_under_any,
    resolve_path,
    validate_output_path,
)
from system.response import fail, success

NO_STORE = {"Cache-Control": "no-store"}
API_TOKEN_COOKIE = "ga_api_token"
UPLOAD_BODY_OVERHEAD_BYTES = 1024 * 1024

SUPPORTED_INPUT_EXTENSIONS = {".txt", ".md", ".pdf"}

if settings.API_AUTH_ENABLED:
    _auth_token = (settings.API_AUTH_TOKEN or "").strip()
    if len(_auth_token) < 16:
        raise RuntimeError(
            "API_AUTH_TOKEN must be set to at least 16 characters when "
            "API_AUTH_ENABLED=true"
        )

app = FastAPI(
    title="GA Sprite Birds Control API",
    description="Thin control plane for the standalone Core engine",
    version="2.0.0",
    debug=settings.API_DEBUG,
)

if settings.API_CORS_ENABLED:
    origins = [item.strip() for item in settings.API_CORS_ORIGINS.split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _request_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return (
        request.headers.get("X-API-Token")
        or request.cookies.get(API_TOKEN_COOKIE)
        or ""
    ).strip()


@app.middleware("http")
async def api_guard(request: Request, call_next):
    """Enforce optional API auth, request-size limits and API cache policy."""
    path = request.url.path
    is_api = path.startswith("/fcgi-bin/api")
    if is_api and request.method in {"POST", "PUT", "PATCH"}:
        raw_length = request.headers.get("content-length")
        if raw_length:
            try:
                length = int(raw_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content=fail(1001, "Invalid Content-Length", {}),
                    headers=NO_STORE,
                )
            is_upload = path == "/fcgi-bin/api/upload"
            limit_mb = (
                settings.API_MAX_UPLOAD_SIZE
                if is_upload
                else settings.API_MAX_JSON_BODY_SIZE
            )
            if limit_mb > 0:
                limit = limit_mb * 1024 * 1024
                if is_upload:
                    limit += UPLOAD_BODY_OVERHEAD_BYTES
                if length > limit:
                    return JSONResponse(
                        status_code=413,
                        content=fail(
                            1003,
                            "Request body is too large",
                            {"limit_mb": limit_mb},
                        ),
                        headers=NO_STORE,
                    )

    if (
        is_api
        and settings.API_AUTH_ENABLED
        and request.method != "OPTIONS"
        and path != "/fcgi-bin/api/status"
    ):
        expected = (settings.API_AUTH_TOKEN or "").strip()
        if not expected or not hmac.compare_digest(
            _request_token(request), expected
        ):
            return JSONResponse(
                status_code=401,
                content=fail(2001, "Unauthorized", {}),
                headers=NO_STORE,
            )

    response = await call_next(request)
    if is_api and path != "/fcgi-bin/api/tts/preview":
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(system_config.router, prefix="/fcgi-bin/api")
app.include_router(tts.router, prefix="/fcgi-bin/api")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=fail(
            1001,
            "Invalid request parameters",
            {"errors": exc.errors()[:20]},
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # 错误响应必须显式禁缓存：浏览器会把 404 当作可启发式缓存的状态码，
    # 一旦路由后来才加上，同一个 URL 仍会从缓存里回放 404（GET /tts/preview 踩过）。
    no_store = {"Cache-Control": "no-store"}
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content=fail(3002, "Not found", {"path": request.url.path}),
            headers=no_store,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(4000, str(exc.detail), {}),
        headers=no_store,
    )


@app.exception_handler(sqlite3.DatabaseError)
async def database_error_handler(
    request: Request, exc: sqlite3.DatabaseError
) -> JSONResponse:
    """Return a clean envelope when tasks.db is corrupted or unreadable.

    Without this handler a malformed database surfaces as an unhandled ASGI
    exception (HTTP 500) on read-only status/history queries.
    """
    logger.error("Task storage error on {}: {}", request.url.path, exc)
    return JSONResponse(
        status_code=200,
        content=fail(
            4001,
            "Task storage is corrupted or unavailable; run `python -m engine doctor`",
            {},
        ),
        headers={"Cache-Control": "no-store"},
    )


def _control_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, EngineCommandError):
        return JSONResponse(
            status_code=200,
            content=fail(exc.code, str(exc), exc.data),
        )
    if isinstance(exc, EngineUnavailable):
        return JSONResponse(
            status_code=503,
            content=fail(3004, "Core engine is not running", {}),
        )
    return JSONResponse(
        status_code=500,
        content=fail(4000, "Internal API error", {}),
    )


def _ensure_dirs() -> None:
    for path in (settings.DATA_DIR, settings.RUN_DIR, settings.API_UPLOAD_DIR):
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass


_ensure_dirs()


def _gui_response() -> FileResponse:
    index_path = PROJECT_ROOT / "index.html"
    if not index_path.exists():
        return JSONResponse(
            status_code=404,
            content=fail(3002, "GUI has not been built", {}),
        )
    return FileResponse(
        index_path,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/")
async def root():
    return _gui_response()


@app.get("/index.html")
async def gui_index():
    return _gui_response()


@app.get("/fcgi-bin/api/status")
async def api_status(
    config_service: ConfigService = Depends(get_config_service),
) -> dict[str, Any]:
    return success(
        {
            "name": "GA Sprite Birds",
            "version": "2.0.0",
            "status": "running",
            "defaults": {
                "voice": config_service.get("TTS_VOICE"),
                "rate": config_service.get("TTS_RATE"),
                "enable_llm": config_service.get("ENABLE_LLM"),
                "prosody_mode": config_service.get("TTS_PROSODY_MODE"),
                "language": config_service.get("LANGUAGE"),
                "chapter_intro_outro": config_service.get("CHAPTER_INTRO_OUTRO"),
                "chapter_lead_in_enabled": config_service.get(
                    "CHAPTER_LEAD_IN_ENABLED"
                ),
            },
        }
    )


@app.get("/fcgi-bin/api/engine")
async def engine_status(
    control: ControlService = Depends(get_control_service),
) -> dict[str, Any]:
    try:
        return success(control.client.stats())
    except Exception as exc:
        return _control_error(exc)


def _validate_source_name(name: str) -> str | None:
    """Return an error message when the extension is not supported."""
    suffix = Path(name).suffix.lower()
    if suffix in SUPPORTED_INPUT_EXTENSIONS:
        return None
    return f"Unsupported file format: {suffix or name}"


def _local_read_roots() -> list[Path]:
    """Roots allowed for the server-local upload ``path`` query parameter."""
    roots: list[Path] = [settings.API_UPLOAD_DIR]
    for item in settings.API_LOCAL_READ_ROOTS.split(","):
        value = item.strip()
        if value:
            roots.append(resolve_path(value))
    return roots


def _checked_output_path(value: str | None, config_service: ConfigService) -> str | None:
    if value is None:
        return None
    try:
        return str(
            validate_output_path(value, config_service.get("OUTPUT_BASE_PATH"))
        )
    except PathSafetyError as exc:
        raise ValueError(str(exc)) from exc


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@app.post("/fcgi-bin/api/upload")
async def upload_file(
    file: Optional[UploadFile] = File(None),
    path: Optional[str] = None,
    output_path: Optional[str] = None,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    control: ControlService = Depends(get_control_service),
    config_service: ConfigService = Depends(get_config_service),
) -> Any:
    """Store an upload, then create the task via the Core command channel."""
    uploaded_path: Path | None = None
    temporary_path: Path | None = None
    try:
        if output_path:
            try:
                output_path = _checked_output_path(output_path, config_service)
            except ValueError as exc:
                return fail(1000, str(exc), {"output_path": output_path})
        if path:
            try:
                source = ensure_under_any(_local_read_roots(), path)
            except PathSafetyError:
                return fail(
                    1000,
                    "Source path is outside the allowed read roots",
                    {"path": path},
                )
            if not source.is_file():
                return fail(3002, "Source file not found", {"path": path})
            error = _validate_source_name(source.name)
            if error:
                return fail(
                    1000, error, {"allowed": sorted(SUPPORTED_INPUT_EXTENSIONS)}
                )
            if settings.API_MAX_UPLOAD_SIZE > 0 and source.stat().st_size > (
                settings.API_MAX_UPLOAD_SIZE * 1024 * 1024
            ):
                return fail(
                    1003,
                    "Source file is too large",
                    {"limit_mb": settings.API_MAX_UPLOAD_SIZE},
                )
            file_path = source
            source_name = source.name
        elif file:
            original_name = os.path.basename(
                (file.filename or "").replace("\\", "/")
            )
            if not original_name:
                return fail(1001, "File name is required", {})
            error = _validate_source_name(original_name)
            if error:
                return fail(
                    1000, error, {"allowed": sorted(SUPPORTED_INPUT_EXTENSIONS)}
                )
            source_name = original_name
            # 幂等键决定落盘路径：客户端重试同一 Idempotency-Key 时命令载荷保持不变，
            # 引擎才能把重复提交识别为同一次操作而不是「输入不同」。
            prefix = (
                hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:16]
                if idempotency_key
                else uuid4().hex
            )
            file_path = settings.API_UPLOAD_DIR / f"{prefix}_{original_name}"
            # Write to a temporary file first. An idempotent retry with the same
            # key must never overwrite the source file of an existing task.
            temporary_path = file_path.with_name(
                f".{file_path.name}.{uuid4().hex}.upload"
            )
            pre_existing = file_path.exists()
            max_bytes = settings.API_MAX_UPLOAD_SIZE * 1024 * 1024
            written = 0
            with open(temporary_path, "wb") as handle:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if max_bytes > 0 and written > max_bytes:
                        temporary_path.unlink(missing_ok=True)
                        temporary_path = None
                        return fail(
                            1003,
                            "Uploaded file is too large",
                            {"limit_mb": settings.API_MAX_UPLOAD_SIZE},
                        )
                    handle.write(chunk)
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                pass

            if pre_existing:
                if _file_sha256(temporary_path) != _file_sha256(file_path):
                    temporary_path.unlink(missing_ok=True)
                    temporary_path = None
                    return fail(
                        1001,
                        "Idempotency-Key was reused with different file content",
                        {},
                    )
                temporary_path.unlink(missing_ok=True)
                temporary_path = None
            else:
                os.replace(temporary_path, file_path)
                temporary_path = None
                uploaded_path = file_path
        else:
            return fail(1001, "file or path is required", {})

        task = control.add_task(
            {
                "file_path": str(file_path),
                "output_path": output_path,
                "filename": file_path.name,
                "source_name": source_name,
            },
            command_id=idempotency_key,
            idempotency_key=idempotency_key,
        )
        return success(task)
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if uploaded_path is not None:
            uploaded_path.unlink(missing_ok=True)
        return _control_error(exc)


@app.post("/fcgi-bin/api/parse")
async def parse_text(
    request: ParseRequest,
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.parse(request.task_id, command_id=request.command_id)
        )
    except Exception as exc:
        return _control_error(exc)


@app.post("/fcgi-bin/api/generate")
async def generate_audio(
    request: GenerateRequest,
    control: ControlService = Depends(get_control_service),
    config_service: ConfigService = Depends(get_config_service),
) -> Any:
    try:
        if request.output_path:
            request.output_path = _checked_output_path(
                request.output_path, config_service
            )
        if request.character_template:
            ensure_under(
                settings.CHARACTER_CACHE_DIR, request.character_template
            )
    except (ValueError, PathSafetyError) as exc:
        return fail(1000, str(exc), {})
    options = request.model_dump(
        exclude={"task_id", "command_id", "language"},
        exclude_none=True,
    )
    try:
        return success(
            control.generate(
                request.task_id,
                options,
                command_id=request.command_id,
            )
        )
    except Exception as exc:
        return _control_error(exc)


@app.post("/fcgi-bin/api/task/{task_id}/pause")
async def pause_generation(
    task_id: str,
    meta: CommandMeta | None = None,
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.pause(task_id, command_id=meta.command_id if meta else None)
        )
    except Exception as exc:
        return _control_error(exc)


@app.post("/fcgi-bin/api/task/{task_id}/resume")
async def resume_generation(
    task_id: str,
    meta: CommandMeta | None = None,
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.resume(task_id, command_id=meta.command_id if meta else None)
        )
    except Exception as exc:
        return _control_error(exc)


@app.post("/fcgi-bin/api/task/{task_id}/cancel")
async def cancel_generation(
    task_id: str,
    meta: CommandMeta | None = None,
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.cancel(task_id, command_id=meta.command_id if meta else None)
        )
    except Exception as exc:
        return _control_error(exc)


@app.post("/fcgi-bin/api/task/{task_id}/retry")
async def retry_generation(
    task_id: str,
    meta: CommandMeta | None = None,
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.retry(task_id, command_id=meta.command_id if meta else None)
        )
    except Exception as exc:
        return _control_error(exc)


@app.delete("/fcgi-bin/api/task/{task_id}")
async def delete_task(
    task_id: str,
    delete_outputs: bool = Query(default=False),
    command_id: str | None = Query(default=None),
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.remove(
                task_id,
                delete_outputs=delete_outputs,
                command_id=command_id,
            )
        )
    except Exception as exc:
        return _control_error(exc)


@app.delete("/fcgi-bin/api/task/{task_id}/chapter/{chapter_index}")
async def delete_chapter_audio(
    task_id: str,
    chapter_index: int,
    command_id: str | None = Query(default=None),
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.remove_chapter(
                task_id, chapter_index, command_id=command_id
            )
        )
    except Exception as exc:
        return _control_error(exc)


@app.get("/fcgi-bin/api/task/{task_id}/status")
async def get_task_status(
    task_id: str,
    control: ControlService = Depends(get_control_service),
) -> Any:
    task = control.status(task_id)
    if task is None:
        return fail(3002, "Task not found", {"task_id": task_id})
    return JSONResponse(
        status_code=200,
        content=success(task),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/fcgi-bin/api/task/{task_id}/events")
async def get_task_events(
    task_id: str,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    control: ControlService = Depends(get_control_service),
) -> Any:
    if control.status(task_id) is None:
        return fail(3002, "Task not found", {"task_id": task_id})
    return success({"events": control.events(task_id, after_id=after_id, limit=limit)})


@app.get("/fcgi-bin/api/tasks")
async def list_tasks(
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    control: ControlService = Depends(get_control_service),
) -> Any:
    return success(
        control.list_tasks(
            status=status,
            task_type=type,
            page=page,
            page_size=page_size,
        )
    )


@app.get("/fcgi-bin/api/task/{task_id}/chapter/{chapter_index}")
async def get_chapter_audio(
    task_id: str,
    chapter_index: int,
    control: ControlService = Depends(get_control_service),
    config_service: ConfigService = Depends(get_config_service),
) -> Any:
    chapter = control.query.get_chapter(task_id, chapter_index)
    if chapter is None:
        return fail(
            3002,
            "Chapter not found",
            {"task_id": task_id, "chapter_index": chapter_index},
        )
    audio_path = chapter.get("audio_path")
    if not audio_path:
        return fail(
            3002,
            "Chapter audio is not available",
            {"chapter_index": chapter_index},
        )
    path = Path(audio_path)
    task = control.query.get_task(task_id)
    snapshot = (task or {}).get("params", {}).get("config_snapshot") or {}
    output_root = snapshot.get("OUTPUT_BASE_PATH") or config_service.get(
        "OUTPUT_BASE_PATH"
    )
    try:
        path = ensure_under(output_root, path)
    except PathSafetyError:
        return fail(
            3003,
            "Audio path is outside the configured output root",
            {"chapter_index": chapter_index},
        )
    if not path.is_file():
        return fail(3002, "Audio file not found", {"path": str(path)})
    if path.stat().st_size == 0:
        return fail(3003, "Audio file is empty", {"path": str(path)})
    media_type = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/fcgi-bin/api/tasks/cleanup")
async def cleanup_tasks(
    request: CleanupRequest,
    control: ControlService = Depends(get_control_service),
) -> Any:
    try:
        return success(
            control.cleanup(
                ttl_seconds=request.ttl_seconds,
                dry_run=request.dry_run,
                delete_outputs=request.delete_outputs,
                command_id=request.command_id,
            )
        )
    except Exception as exc:
        return _control_error(exc)


@app.get("/{full_path:path}")
async def gui_history_fallback(full_path: str) -> Any:
    """SPA history fallback for client-side routes (non-API/static paths)."""
    if full_path.startswith(("fcgi-bin/", "gui-assets/", "uploads/")):
        return JSONResponse(
            status_code=404,
            content=fail(3002, "Not found", {"path": "/" + full_path}),
            headers={"Cache-Control": "no-store"},
        )
    return _gui_response()
