"""
GA Sprite Birds - FastAPI unified routing entry point
Provides APIs for text upload, parsing, generation, and task query

Version: v1.0
Dev team: Tiger
"""

import os
import asyncio
import importlib
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
from ga_birds.Common.i18n import t

import config

# Initialize multilingual support (defaults to config file)
_core_module_name = config.CORE_DIR.replace('-', '_')
_i18n_module = importlib.import_module(f'{_core_module_name}.Common.i18n')
_i18n_module.set_locale(config.LANGUAGE)

# Dynamically import core modules (based on config.CORE_DIR)
_utils_module = importlib.import_module(f'{_core_module_name}.Utils')
_llm_module = importlib.import_module(f'{_core_module_name}.LLM')
_audio_module = importlib.import_module(f'{_core_module_name}.Audio')
_common_module = importlib.import_module(f'{_core_module_name}.Common')
_task_module = importlib.import_module(f'{_core_module_name}.Task')

# Import required classes and functions
SUPPORTED_INPUT_EXTENSIONS = _utils_module.SUPPORTED_INPUT_EXTENSIONS
load_chapters = _common_module.load_chapters
generate_single_voice_chapter = _audio_module.generate_single_voice_chapter
LLMManager = _llm_module.LLMManager
TTSManager = _audio_module.TTSManager
AudioExporter = _audio_module.AudioExporter
PROSODY_MODES = _audio_module.PROSODY_MODES
normalize_prosody_mode = _audio_module.normalize_prosody_mode
TaskManager = _task_module.TaskManager
TaskStatus = _task_module.TaskStatus
ChapterProgress = _task_module.ChapterProgress


# Initialize the FastAPI application
app = FastAPI(
    title=t("api.title"),
    description=t("api.description"),
    version="1.0.0",
    debug=config.API_DEBUG
)

# Configure CORS
if config.API_CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.API_CORS_ORIGINS,
        # The API has no cookie/session auth, and "*" is not valid with
        # credentialed CORS requests.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize managers
task_manager = TaskManager()


# ============================================
# Request/Response models
# ============================================

class ParseRequest(BaseModel):
    """Parse request"""
    task_id: str  # Task ID
    language: Optional[str] = None  # UI language (en_US, zh_CN)


class GenerateRequest(BaseModel):
    """Generate request"""
    task_id: str  # Task ID
    voice: Optional[str] = None  # Voice timbre (overrides config)
    output_path: Optional[str] = None  # Output root (source filename is appended)
    enable_llm: Optional[bool] = None  # None uses ENABLE_LLM from config
    rate: Optional[float] = None  # Speech rate (0.5-2.0)
    prosody_mode: Optional[str] = None  # off / pause / prosody
    language: Optional[str] = None  # UI language (en_US, zh_CN)
    chapter_indexes: Optional[List[int]] = None  # Generate only these chapters; None means all


class TaskResponse(BaseModel):
    """Task response"""
    task_id: str
    status: str
    message: str


# ============================================
# API routes
# ============================================

@app.get("/")
async def root():
    """Serve the packaged GUI at the site root"""
    return _get_gui_index_response()


@app.get("/api/status")
async def api_status():
    """API health status"""
    return {
        "name": t("api.service_name"),
        "version": "1.0.0",
        "status": "running",
        "defaults": {
            "voice": config.TTS_VOICE,
            "rate": config.TTS_RATE,
            "enable_llm": config.ENABLE_LLM,
            "prosody_mode": normalize_prosody_mode(),
            "language": config.LANGUAGE,
        },
    }


@app.get("/index.html")
async def gui_index():
    """Serve the packaged GUI entry file"""
    return _get_gui_index_response()


@app.get("/policy/{full_path:path}")
async def gui_policy_route(full_path: str):
    """Serve the GUI for browser history routes"""
    return _get_gui_index_response()


def _get_gui_index_response():
    """Build the GUI index file response"""
    index_path = Path(__file__).resolve().parents[1] / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail=t("api.gui_not_built"))
    return FileResponse(
        index_path,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"}
    )


def _validate_input_file(file_path: Path) -> None:
    """Reject files that the chapter loader cannot read."""
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_INPUT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=t("api.unsupported_file_format", suffix=suffix)
        )


@app.post("/upload", response_model=TaskResponse)
async def upload_file(
    file: Optional[UploadFile] = File(None),
    path: Optional[str] = None,
    output_path: Optional[str] = None,
    language: Optional[str] = None
):
    """
    Upload a text file or specify a local path.

    Args:
        file: The uploaded file object
        path: Local file path (takes priority)
        output_path: Custom output root; the source filename is appended
        language: UI language (en_US, zh_CN)

    Returns:
        Task information
    """
    if language:
        _i18n_module.set_locale(language)

    try:
        # Prefer the local path
        if path:
            file_path = Path(path)
            if not file_path.is_file():
                raise HTTPException(
                    status_code=404,
                    detail=t("api.file_not_found", path=path)
                )
            _validate_input_file(file_path)
            source_name = file_path.name
        elif file:
            # Never trust the client-provided name for the on-disk path.
            original_name = os.path.basename((file.filename or "").replace("\\", "/"))
            if not original_name:
                raise HTTPException(status_code=400, detail=t("api.file_name_required"))
            source_name = original_name

            upload_dir = Path(config.API_UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)
            # A unique prefix prevents two uploads from overwriting each other.
            file_path = upload_dir / f"{uuid4().hex}_{original_name}"
            _validate_input_file(file_path)

            max_bytes = config.API_MAX_UPLOAD_SIZE * 1024 * 1024
            written = 0
            try:
                with open(file_path, "wb") as handle:
                    while True:
                        chunk = await file.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if max_bytes > 0 and written > max_bytes:
                            raise HTTPException(
                                status_code=413,
                                detail=t(
                                    "api.file_too_large",
                                    limit=config.API_MAX_UPLOAD_SIZE
                                )
                            )
                        handle.write(chunk)
            except HTTPException:
                file_path.unlink(missing_ok=True)
                raise
            except Exception as error:
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=500,
                    detail=t("api.file_upload_failed", error=error)
                )

            logger.info(t("api.file_upload_success", path=str(file_path)))
        else:
            raise HTTPException(status_code=400, detail=t("api.file_or_path_required"))

        task_id = task_manager.create_task(
            metadata={
                "file_path": str(file_path),
                "output_path": output_path,
                "filename": file_path.name,
                "source_name": source_name,
            }
        )

        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=t("api.upload_task_created", task_id=task_id)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(t("api.file_upload_failed", error=e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse", response_model=TaskResponse)
async def parse_text(request: ParseRequest):
    """
    Parse text and split into chapters

    Args:
        request: Parse request

    Returns:
        Task information
    """
    # Set language
    if request.language:
        _i18n_module.set_locale(request.language)

    task = task_manager.get_task(request.task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=t("api.task_not_found", task_id=request.task_id)
        )

    # Re-parsing while a job is running, or after audio has been produced,
    # would silently reset chapter progress and orphan existing files.
    if task_manager.is_running(request.task_id) or task.status == TaskStatus.GENERATING:
        raise HTTPException(status_code=409, detail=t("api.task_generating_no_parse"))
    if task.status == TaskStatus.PARSING:
        raise HTTPException(status_code=409, detail=t("api.task_already_parsing"))
    if any(chapter.audio_path for chapter in task.chapters):
        raise HTTPException(status_code=409, detail=t("api.task_has_audio_no_parse"))

    file_path = task.metadata.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail=t("api.task_no_file_path"))

    file_path_obj = Path(file_path)
    if not file_path_obj.is_file():
        raise HTTPException(
            status_code=404,
            detail=t("api.file_not_found", path=file_path)
        )
    _validate_input_file(file_path_obj)

    # Drop the previous parse result so a failed re-parse cannot leave stale
    # chapters behind.
    task.total_chapters = 0
    task.completed_chapters = 0
    task.chapters = []
    task.error = None
    task.metadata.pop("chapters", None)
    task.metadata.pop("generation", None)
    task_manager.update_task_status(request.task_id, TaskStatus.PARSING)

    try:
        chapters = load_chapters(str(file_path_obj))

        task.total_chapters = len(chapters)
        task.chapters = [
            ChapterProgress(index=ch.index, title=ch.title)
            for ch in chapters
        ]
        task.metadata["chapters"] = [
            {
                "index": ch.index,
                "title": ch.title,
                "content": ch.content
            }
            for ch in chapters
        ]

        task_manager.update_task_status(request.task_id, TaskStatus.PARSED)
        logger.info(t("api.parse_complete", task_id=request.task_id, count=len(chapters)))

        return TaskResponse(
            task_id=request.task_id,
            status="parsed",
            message=t("api.parse_complete", task_id=request.task_id, count=len(chapters))
        )
    except Exception as e:
        logger.error(t("api.parse_failed", error=e))
        task.error = str(e)
        task_manager.update_task_status(request.task_id, TaskStatus.FAILED)
        status_code = 404 if isinstance(e, FileNotFoundError) else 400 if isinstance(e, ValueError) else 500
        raise HTTPException(status_code=status_code, detail=str(e))


def _launch_generation(
    task,
    voice: Optional[str],
    output_path: Optional[str],
    enable_llm: bool,
    rate: Optional[float],
    prosody_mode: Optional[str],
    chapter_indexes: Optional[List[int]]
) -> None:
    """Start a managed background generation job for a task."""
    task.pause_requested = False
    task_manager.update_task_status(task.task_id, TaskStatus.GENERATING)
    job = asyncio.create_task(
        _generate_audio_task(
            task_id=task.task_id,
            voice=voice,
            output_path=output_path,
            enable_llm=enable_llm,
            rate=rate,
            prosody_mode=prosody_mode,
            chapter_indexes=chapter_indexes,
        )
    )
    task_manager.running_tasks[task.task_id] = job


@app.post("/generate", response_model=TaskResponse)
async def generate_audio(request: GenerateRequest):
    """
    Start audio generation (asynchronous).

    Args:
        request: Generate request; chapter_indexes limits generation to selected chapters

    Returns:
        Task information
    """
    if request.language:
        _i18n_module.set_locale(request.language)

    task = task_manager.get_task(request.task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=t("api.task_not_found", task_id=request.task_id)
        )

    if task_manager.is_running(request.task_id) or task.status == TaskStatus.GENERATING:
        raise HTTPException(status_code=409, detail=t("api.task_already_generating"))
    if task.status == TaskStatus.PARSING:
        raise HTTPException(status_code=409, detail=t("api.task_already_parsing"))

    chapters = task.metadata.get("chapters") or []
    if not chapters:
        raise HTTPException(status_code=400, detail=t("api.task_no_chapters"))

    if request.chapter_indexes is not None:
        if not request.chapter_indexes:
            raise HTTPException(status_code=400, detail=t("api.chapter_indexes_empty"))
        available = {item["index"] for item in chapters}
        invalid = sorted({index for index in request.chapter_indexes if index not in available})
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=t("api.chapter_indexes_invalid", indexes=invalid)
            )

    if request.rate is not None and not 0.5 <= request.rate <= 2.0:
        raise HTTPException(status_code=400, detail=t("api.invalid_rate"))

    if request.prosody_mode is not None:
        requested_mode = request.prosody_mode.strip().lower()
        if requested_mode not in PROSODY_MODES:
            raise HTTPException(
                status_code=400,
                detail=t("api.invalid_prosody_mode", modes=", ".join(PROSODY_MODES))
            )
    prosody_mode = normalize_prosody_mode(request.prosody_mode)

    enable_llm = config.ENABLE_LLM if request.enable_llm is None else request.enable_llm

    # Remember the options so resume can reuse the same scope and parameters.
    task.metadata["generation"] = {
        "voice": request.voice,
        "output_path": request.output_path,
        "enable_llm": enable_llm,
        "rate": request.rate,
        "prosody_mode": prosody_mode,
        "chapter_indexes": request.chapter_indexes,
    }

    _launch_generation(
        task=task,
        voice=request.voice,
        output_path=request.output_path,
        enable_llm=enable_llm,
        rate=request.rate,
        prosody_mode=prosody_mode,
        chapter_indexes=request.chapter_indexes,
    )

    return TaskResponse(
        task_id=request.task_id,
        status="generating",
        message=t("api.generate_started")
    )


@app.post("/task/{task_id}/pause", response_model=TaskResponse)
async def pause_generation(task_id: str):
    """Pause a running generation after the current chapter finishes."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=t("api.task_not_found", task_id=task_id))

    if task.status != TaskStatus.GENERATING or not task_manager.is_running(task_id):
        raise HTTPException(status_code=409, detail=t("api.task_not_generating"))

    task_manager.request_pause(task_id)
    return TaskResponse(task_id=task_id, status="pausing", message=t("api.pause_requested"))


@app.post("/task/{task_id}/resume", response_model=TaskResponse)
async def resume_generation(task_id: str):
    """Resume a paused generation from the next unfinished chapter."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=t("api.task_not_found", task_id=task_id))

    if task.status != TaskStatus.PAUSED:
        raise HTTPException(status_code=409, detail=t("api.task_not_paused"))
    if task_manager.is_running(task_id):
        raise HTTPException(status_code=409, detail=t("api.task_already_generating"))

    options = task.metadata.get("generation", {})
    _launch_generation(
        task=task,
        voice=options.get("voice"),
        output_path=options.get("output_path"),
        enable_llm=options.get("enable_llm", config.ENABLE_LLM),
        rate=options.get("rate"),
        prosody_mode=normalize_prosody_mode(options.get("prosody_mode")),
        chapter_indexes=options.get("chapter_indexes"),
    )
    return TaskResponse(task_id=task_id, status="generating", message=t("api.resume_started"))


@app.delete("/task/{task_id}", response_model=TaskResponse)
async def delete_task(task_id: str):
    """Clear a task, its parsed chapters, generated audio, and record."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=t("api.task_not_found", task_id=task_id))

    if task_manager.is_running(task_id) or task.status == TaskStatus.GENERATING:
        raise HTTPException(status_code=409, detail=t("api.task_generating_no_delete"))
    if task.status == TaskStatus.PARSING:
        raise HTTPException(status_code=409, detail=t("api.task_already_parsing"))

    if not task_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail=t("api.task_not_found", task_id=task_id))

    return TaskResponse(
        task_id=task_id,
        status="deleted",
        message=t("api.task_deleted", task_id=task_id),
    )


@app.delete("/task/{task_id}/chapter/{chapter_index}")
async def delete_chapter_audio(task_id: str, chapter_index: int):
    """Delete a chapter's generated audio file and reset it to pending."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=t("api.task_not_found", task_id=task_id))

    if task_manager.is_running(task_id) or task.status == TaskStatus.GENERATING:
        raise HTTPException(status_code=409, detail=t("api.task_generating_no_delete"))

    if not task_manager.delete_chapter_audio(task_id, chapter_index):
        raise HTTPException(
            status_code=404,
            detail=t("api.chapter_not_found", chapter_index=chapter_index)
        )

    return {"task_id": task_id, "chapter_index": chapter_index, "status": "pending"}


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str, response: Response):
    """
    Query task status

    Args:
        task_id: Task ID

    Returns:
        Task progress information
    """
    progress = task_manager.get_task_progress(task_id)
    if not progress:
        raise HTTPException(
            status_code=404,
            detail=t("api.task_not_found", task_id=task_id)
        )

    # Progress changes after every chapter; never let a stale cached response
    # restore a list that the user just deleted.
    response.headers["Cache-Control"] = "no-store"
    return progress


@app.get("/task/{task_id}/chapter/{chapter_index}")
async def get_chapter_audio(task_id: str, chapter_index: int):
    """
    Get a single chapter's audio file

    Args:
        task_id: Task ID
        chapter_index: Chapter index

    Returns:
        Audio file
    """
    audio_path = task_manager.get_chapter_audio(task_id, chapter_index)
    if not audio_path:
        raise HTTPException(
            status_code=404,
            detail=t("api.audio_not_found", chapter_index=chapter_index)
        )

    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=404,
            detail=t("api.audio_path_not_found", path=audio_path)
        )

    if os.path.getsize(audio_path) == 0:
        raise HTTPException(status_code=409, detail=t("api.audio_file_empty", path=audio_path))

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=os.path.basename(audio_path),
        headers={"Cache-Control": "no-cache"}
    )


# ============================================
# Background task functions
# ============================================

async def _generate_audio_task(
    task_id: str,
    voice: Optional[str] = None,
    output_path: Optional[str] = None,
    enable_llm: bool = True,
    rate: Optional[float] = None,
    prosody_mode: Optional[str] = None,
    chapter_indexes: Optional[List[int]] = None
):
    """
    Background audio generation task.

    Args:
        task_id: Task ID
        voice: Voice timbre
        output_path: Output root (source filename is appended)
        enable_llm: Whether to enable LLM
        rate: Speech rate (0.5-2.0)
        prosody_mode: Punctuation pause/tone mode (off/pause/prosody)
        chapter_indexes: Generate only these chapters; None means all chapters
    """
    paused = False
    failed_in_run = False
    try:
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(t("api.task_not_found", task_id=task_id))
            return

        llm_manager = None
        if enable_llm:
            try:
                llm_manager = LLMManager()
            except Exception as error:
                logger.error(t("api.llm_init_failed", error=error))

        tts_manager = TTSManager()
        audio_exporter = AudioExporter()
        source_name = task.metadata.get("source_name") or task.metadata.get("filename")
        output_path = output_path or task.metadata.get("output_path")

        chapters_data = task.metadata.get("chapters", [])
        if chapter_indexes is not None:
            wanted = set(chapter_indexes)
            chapters_data = [
                item for item in chapters_data if item["index"] in wanted
            ]

        for chapter_data in chapters_data:
            if task_manager.get_task(task_id) is None:
                logger.warning(t("api.task_not_found", task_id=task_id))
                return

            # Between-chapter pause: stop before starting the next chapter.
            if task.pause_requested:
                paused = True
                break

            chapter_index = chapter_data["index"]
            chapter_title = chapter_data["title"]
            chapter_content = chapter_data["content"]

            if task_manager.get_chapter_status(task_id, chapter_index) == TaskStatus.COMPLETED:
                logger.info(t("api.chapter_skip_completed", index=chapter_index))
                continue

            logger.info(t("api.generating_chapter", index=chapter_index, title=chapter_title))
            task_manager.update_chapter_status(
                task_id,
                chapter_index,
                TaskStatus.GENERATING
            )

            try:
                result = await generate_single_voice_chapter(
                    chapter_index=chapter_index,
                    chapter_title=chapter_title,
                    content=chapter_content,
                    output_dir=output_path,
                    voice=voice,
                    rate=rate,
                    enable_llm=enable_llm,
                    llm_manager=llm_manager,
                    tts_manager=tts_manager,
                    audio_exporter=audio_exporter,
                    prosody_mode=prosody_mode,
                    source_name=source_name,
                )
                task_manager.update_chapter_status(
                    task_id,
                    chapter_index,
                    TaskStatus.COMPLETED,
                    audio_path=str(result.audio_path)
                )
                if result.skipped:
                    logger.info(t("api.chapter_skip_completed", index=chapter_index))
            except Exception as e:
                failed_in_run = True
                logger.error(t("api.chapter_failed", index=chapter_index, error=e))
                task_manager.update_chapter_status(
                    task_id,
                    chapter_index,
                    TaskStatus.FAILED,
                    error=str(e)
                )

        if paused:
            task_manager.mark_chapters_paused(task_id, chapter_indexes)
            task_manager.update_task_status(task_id, TaskStatus.PAUSED)
            logger.info(t("api.task_paused", task_id=task_id))
            return

        completed_chapters = [
            chapter for chapter in task.chapters
            if chapter.status == TaskStatus.COMPLETED
        ]

        if len(completed_chapters) == task.total_chapters:
            task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            logger.info(t("api.task_all_complete", task_id=task_id))
        elif failed_in_run:
            task.error = t("api.task_partial_failed", task_id=task_id)
            task_manager.update_task_status(task_id, TaskStatus.FAILED)
            logger.error(task.error)
        else:
            # Some chapters are still pending; return to the parsed state.
            task_manager.update_task_status(task_id, TaskStatus.PARSED)
            logger.info(t("api.task_partial_complete", task_id=task_id))

    except asyncio.CancelledError:
        logger.info(t("api.task_job_cancelled", task_id=task_id))
        # Do not let an old, cancelled job overwrite the state of a newer one.
        task = task_manager.get_task(task_id)
        if (
            task
            and task.status == TaskStatus.GENERATING
            and task_manager.running_tasks.get(task_id) is asyncio.current_task()
        ):
            task_manager.update_task_status(task_id, TaskStatus.CANCELLED)
        raise
    except Exception as e:
        logger.error(t("api.task_failed", task_id=task_id, error=e))
        task = task_manager.get_task(task_id)
        if task:
            task.error = str(e)
        task_manager.update_task_status(task_id, TaskStatus.FAILED)
    finally:
        if task_manager.running_tasks.get(task_id) is asyncio.current_task():
            task_manager.running_tasks.pop(task_id, None)


# ============================================
# Startup configuration
# ============================================

if __name__ == "__main__":
    import uvicorn

    # Configure logging (using config settings)
    if config.LOG_FILE:
        logger.add(
            config.LOG_FILE,
            rotation=f"{config.LOG_MAX_FILE_SIZE} MB",
            retention=config.LOG_BACKUP_COUNT,
            level=config.LOG_LEVEL,
            format=config.LOG_FORMAT
        )

    # Start the service
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower()
    )
