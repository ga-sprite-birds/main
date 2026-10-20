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
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, HTTPException
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
_parser_module = importlib.import_module(f'{_core_module_name}.Parser')
_llm_module = importlib.import_module(f'{_core_module_name}.LLM')
_audio_module = importlib.import_module(f'{_core_module_name}.Audio')
_sprite_module = importlib.import_module(f'{_core_module_name}.Sprite')
_task_module = importlib.import_module(f'{_core_module_name}.Task')

# Import required classes and functions
read_text_file = _utils_module.read_text_file
extract_pdf_text = _utils_module.extract_pdf_text
preprocess_text = _utils_module.preprocess_text
normalize_chapter_headings = _utils_module.normalize_chapter_headings
get_unique_filename = _utils_module.get_unique_filename
ChapterParser = _parser_module.ChapterParser
LLMManager = _llm_module.LLMManager
TTSManager = _audio_module.TTSManager
AudioExporter = _audio_module.AudioExporter
SpriteManager = _sprite_module.SpriteManager
TaskManager = _task_module.TaskManager
TaskStatus = _task_module.TaskStatus
ChapterProgress = _task_module.ChapterProgress


# Initialize the FastAPI application
app = FastAPI(
    title="音频朗读系统 API",
    description="将文本转换为音频的 API 服务",
    version="1.0.0",
    debug=config.API_DEBUG
)

# Configure CORS
if config.API_CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.API_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize managers
task_manager = TaskManager()
sprite_manager = SpriteManager()


# ============================================
# Request/Response models
# ============================================

class UploadRequest(BaseModel):
    """Upload request"""
    path: Optional[str] = None  # Local file path
    output_path: Optional[str] = None  # Custom output path
    language: Optional[str] = None  # UI language (en_US, zh_CN)


class ParseRequest(BaseModel):
    """Parse request"""
    task_id: str  # Task ID
    language: Optional[str] = None  # UI language (en_US, zh_CN)


class GenerateRequest(BaseModel):
    """Generate request"""
    task_id: str  # Task ID
    voice: Optional[str] = None  # Voice timbre (overrides config)
    output_path: Optional[str] = None  # Output path (overrides config)
    enable_llm: bool = True  # Whether to enable LLM colloquialization
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
        "name": "音频朗读系统 API",
        "version": "1.0.0",
        "status": "running"
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
        raise HTTPException(status_code=404, detail="GUI 文件不存在，请先在 gui 目录执行 npm run build")
    return FileResponse(
        index_path,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"}
    )


@app.post("/upload", response_model=TaskResponse)
async def upload_file(
    file: Optional[UploadFile] = File(None),
    path: Optional[str] = None,
    output_path: Optional[str] = None,
    language: Optional[str] = None
):
    """
    Upload a text file or specify a local path

    Args:
        file: The uploaded file object
        path: Local file path (takes priority)
        output_path: Custom output path
        language: UI language (en_US, zh_CN)

    Returns:
        Task information
    """
    # Set language
    if language:
        _i18n_module.set_locale(language)

    try:
        # Prefer the local path
        if path:
            file_path = path
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        elif file:
            # Save the uploaded file (using the configured upload directory)
            upload_dir = Path(config.API_UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            logger.info(t("api.file_upload_success", path=str(file_path)))
        else:
            raise HTTPException(status_code=400, detail="必须提供文件或路径")
        
        # Create the task
        task_id = task_manager.create_task(
            metadata={
                "file_path": str(file_path),
                "output_path": output_path,
                "filename": os.path.basename(file_path)
            }
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"文件上传成功，任务 ID: {task_id}"
        )
    
    except HTTPException:
        # Re-raise HTTPException, preserving the original status code
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

    try:
        task = task_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {request.task_id}")
        
        # Update task status
        task_manager.update_task_status(request.task_id, TaskStatus.PARSING)
        
        # Read the file
        file_path = task.metadata.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="任务中未找到文件路径")
        
        # Read content based on file type
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".pdf":
            text = extract_pdf_text(file_path)
        else:
            text = read_text_file(file_path)
        
        # Text preprocessing
        if config.TEXT_PREPROCESSING_ENABLED:
            text = preprocess_text(
                text,
                remove_extra_newlines=True,
                remove_headers_footers=True,
                fix_pdf_linebreaks=True
            )

        # Normalize irregular chapter headings (Markdown bold/heading, etc.)
        if config.CHAPTER_NORMALIZE_ENABLED:
            text = normalize_chapter_headings(text)

        # Chapter splitting
        parser = ChapterParser(
            regex_patterns=config.CHAPTER_REGEX_PATTERNS,
            min_length=config.CHAPTER_MIN_LENGTH,
            keep_title=config.CHAPTER_KEEP_TITLE
        )
        chapters = parser.parse(text)
        
        # Update task chapter information
        task.total_chapters = len(chapters)
        task.chapters = [
            ChapterProgress(index=ch.index, title=ch.title)
            for ch in chapters
        ]
        
        # Save chapter data to task metadata
        task.metadata["chapters"] = [
            {
                "index": ch.index,
                "title": ch.title,
                "content": ch.content
            }
            for ch in chapters
        ]

        # Update task status to parsed
        task_manager.update_task_status(request.task_id, TaskStatus.PARSED)

        logger.info(t("api.parse_complete", task_id=request.task_id, count=len(chapters)))

        return TaskResponse(
            task_id=request.task_id,
            status="parsed",
            message=f"解析完成，共 {len(chapters)} 章"
        )
    
    except HTTPException:
        # Re-raise HTTPException, preserving the original status code
        raise
    except Exception as e:
        logger.error(t("api.parse_failed", error=e))
        task_manager.update_task_status(request.task_id, TaskStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


def _launch_generation(
    task,
    voice: Optional[str],
    output_path: Optional[str],
    enable_llm: bool,
    chapter_indexes: Optional[List[int]]
) -> None:
    """Start a managed background generation job for a task."""
    task.pause_requested = False

    # Stop any job that is still winding down so it cannot clobber the new one
    existing = task_manager.running_tasks.get(task.task_id)
    if existing and not existing.done():
        existing.cancel()

    task_manager.update_task_status(task.task_id, TaskStatus.GENERATING)
    job = asyncio.create_task(
        _generate_audio_task(
            task_id=task.task_id,
            voice=voice,
            output_path=output_path,
            enable_llm=enable_llm,
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
    # Set language
    if request.language:
        _i18n_module.set_locale(request.language)

    try:
        task = task_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {request.task_id}")

        if task.status == TaskStatus.GENERATING:
            raise HTTPException(status_code=409, detail=t("api.task_already_generating"))

        # Check whether the task has been parsed
        if not task.metadata.get("chapters"):
            raise HTTPException(status_code=400, detail="任务尚未解析，请先调用 /parse")

        # Remember the options so resume can reuse them
        task.metadata["generation"] = {
            "voice": request.voice,
            "output_path": request.output_path,
            "enable_llm": request.enable_llm,
        }

        _launch_generation(
            task=task,
            voice=request.voice,
            output_path=request.output_path,
            enable_llm=request.enable_llm,
            chapter_indexes=request.chapter_indexes,
        )

        return TaskResponse(
            task_id=request.task_id,
            status="generating",
            message="音频生成已开始，请通过 /task/{id}/status 查询进度"
        )
    
    except HTTPException:
        # Re-raise HTTPException, preserving the original status code
        raise
    except Exception as e:
        logger.error(t("api.generate_failed", error=e))
        raise HTTPException(status_code=500, detail=str(e))


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

    options = task.metadata.get("generation", {})
    _launch_generation(
        task=task,
        voice=options.get("voice"),
        output_path=options.get("output_path"),
        enable_llm=options.get("enable_llm", True),
        chapter_indexes=None,
    )
    return TaskResponse(task_id=task_id, status="generating", message=t("api.resume_started"))


@app.delete("/task/{task_id}/chapter/{chapter_index}")
async def delete_chapter_audio(task_id: str, chapter_index: int):
    """Delete a chapter's generated audio file and reset it to pending."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=t("api.task_not_found", task_id=task_id))

    if task.status == TaskStatus.GENERATING:
        raise HTTPException(status_code=409, detail=t("api.task_generating_no_delete"))

    if not task_manager.delete_chapter_audio(task_id, chapter_index):
        raise HTTPException(status_code=404, detail=f"章节不存在: {chapter_index}")

    return {"task_id": task_id, "chapter_index": chapter_index, "status": "pending"}


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Query task status

    Args:
        task_id: Task ID

    Returns:
        Task progress information
    """
    progress = task_manager.get_task_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
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
        raise HTTPException(status_code=404, detail=f"章节音频不存在: {chapter_index}")
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"音频文件不存在: {audio_path}")

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
    chapter_indexes: Optional[List[int]] = None
):
    """
    Background audio generation task

    Args:
        task_id: Task ID
        voice: Voice timbre
        output_path: Output path
        enable_llm: Whether to enable LLM
        chapter_indexes: Generate only these chapters; None means all chapters
    """
    paused = False
    try:
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(t("api.task_not_found", task_id=task_id))
            return
        
        # Initialize managers (no need to pass settings; managers use config internally)
        llm_manager = LLMManager() if enable_llm else None
        tts_manager = TTSManager()
        audio_exporter = AudioExporter()
        
        # Get chapter data
        chapters_data = task.metadata.get("chapters", [])
        if chapter_indexes:
            wanted = set(chapter_indexes)
            chapters_data = [
                item for item in chapters_data if item["index"] in wanted
            ]
        
        # Generate audio chapter by chapter
        for chapter_data in chapters_data:
            # Stop when the task was removed while generating
            if task_manager.get_task(task_id) is None:
                logger.warning(t("api.task_not_found", task_id=task_id))
                return

            # Between-chapter pause: stop before starting the next chapter
            if task.pause_requested:
                paused = True
                break

            chapter_index = chapter_data["index"]
            chapter_title = chapter_data["title"]
            chapter_content = chapter_data["content"]

            # Skip chapters that already have audio
            if task_manager.get_chapter_status(task_id, chapter_index) == TaskStatus.COMPLETED:
                logger.info(t("api.chapter_skip_completed", index=chapter_index))
                continue

            logger.info(t("api.generating_chapter", index=chapter_index, title=chapter_title))
            
            # Update chapter status
            task_manager.update_chapter_status(
                task_id,
                chapter_index,
                TaskStatus.GENERATING
            )
            
            try:
                # LLM colloquialization (optional)
                if enable_llm and llm_manager:
                    logger.info(t("api.chapter_llm_start", index=chapter_index))
                    try:
                        chapter_content = llm_manager.colloquialize_text(chapter_content)
                    except Exception as llm_error:
                        logger.error(t("api.chapter_llm_failed", index=chapter_index, error=llm_error))
                        logger.warning(t("api.chapter_llm_fallback", index=chapter_index))
                
                # Generate the audio file path
                audio_path = audio_exporter.get_output_path(
                    index=chapter_index,
                    title=chapter_title,
                    role="default",
                    custom_base_path=output_path
                )

                if audio_path.exists():
                    if config.OUTPUT_DUPLICATE_HANDLING == "skip" and audio_path.stat().st_size > 0:
                        logger.info(t("api.file_exists_skip", path=audio_path))
                        task_manager.update_chapter_status(
                            task_id,
                            chapter_index,
                            TaskStatus.COMPLETED,
                            audio_path=str(audio_path)
                        )
                        continue
                    if config.OUTPUT_DUPLICATE_HANDLING == "rename":
                        audio_path = get_unique_filename(audio_path)
                        logger.info(t("api.file_exists_rename", path=audio_path))
                    elif audio_path.stat().st_size == 0:
                        audio_path.unlink()
                        logger.info(t("api.empty_file_removed", path=audio_path))

                # TTS generate audio
                logger.info(t("api.chapter_tts_start", index=chapter_index))
                await tts_manager.generate_audio(
                    text=chapter_content,
                    output_path=str(audio_path),
                    voice=voice
                )
                
                # Update chapter status to completed
                task_manager.update_chapter_status(
                    task_id,
                    chapter_index,
                    TaskStatus.COMPLETED,
                    audio_path=str(audio_path)
                )
                
                logger.info(t("api.chapter_complete", index=chapter_index, path=str(audio_path)))
            
            except Exception as e:
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
        failed_chapters = [
            chapter for chapter in task.chapters
            if chapter.status == TaskStatus.FAILED
        ]

        if len(completed_chapters) == task.total_chapters:
            task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            logger.info(t("api.task_all_complete", task_id=task_id))
        elif failed_chapters:
            task.error = t("api.task_partial_failed", task_id=task_id)
            task_manager.update_task_status(task_id, TaskStatus.FAILED)
            logger.error(task.error)
        else:
            # Some chapters are still pending; return to the parsed state
            task_manager.update_task_status(task_id, TaskStatus.PARSED)
            logger.info(t("api.task_partial_complete", task_id=task_id))

    except asyncio.CancelledError:
        logger.info(t("api.task_job_cancelled", task_id=task_id))
        task_manager.update_task_status(task_id, TaskStatus.CANCELLED)
        raise
    except Exception as e:
        logger.error(t("api.task_failed", task_id=task_id, error=e))
        task_manager.update_task_status(task_id, TaskStatus.FAILED)
    finally:
        # Only clear the registration if it still points at this job
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
