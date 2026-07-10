"""
GA Sprite Birds - FastAPI unified routing entry point
Provides APIs for text upload, parsing, generation, and task query

Version: v1.0
Dev team: Tiger
"""

import os
import importlib
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

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
ChapterParser = _parser_module.ChapterParser
LLMManager = _llm_module.LLMManager
TTSManager = _audio_module.TTSManager
AudioExporter = _audio_module.AudioExporter
SpriteManager = _sprite_module.SpriteManager
TaskManager = _task_module.TaskManager
TaskStatus = _task_module.TaskStatus


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
    """Root path"""
    return {
        "name": "音频朗读系统 API",
        "version": "1.0.0",
        "status": "running"
    }


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

            logger.info(f"文件上传成功: {file_path}")
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
        logger.error(f"文件上传失败: {e}")
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
            {
                "index": ch.index,
                "title": ch.title,
                "status": TaskStatus.PENDING,
                "audio_path": None
            }
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

        logger.info(f"任务 {request.task_id} 解析完成，共 {len(chapters)} 章")

        return TaskResponse(
            task_id=request.task_id,
            status="parsed",
            message=f"解析完成，共 {len(chapters)} 章"
        )
    
    except HTTPException:
        # Re-raise HTTPException, preserving the original status code
        raise
    except Exception as e:
        logger.error(f"文本解析失败: {e}")
        task_manager.update_task_status(request.task_id, TaskStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_model=TaskResponse)
async def generate_audio(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Start audio generation (asynchronous)

    Args:
        request: Generate request
        background_tasks: Background tasks

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
        
        # Check whether the task has been parsed
        if not task.metadata.get("chapters"):
            raise HTTPException(status_code=400, detail="任务尚未解析，请先调用 /parse")
        
        # Add a background task
        background_tasks.add_task(
            _generate_audio_task,
            task_id=request.task_id,
            voice=request.voice,
            output_path=request.output_path,
            enable_llm=request.enable_llm
        )
        
        # Update task status
        task_manager.update_task_status(request.task_id, TaskStatus.GENERATING)
        
        return TaskResponse(
            task_id=request.task_id,
            status="generating",
            message="音频生成已开始，请通过 /task/{id}/status 查询进度"
        )
    
    except HTTPException:
        # Re-raise HTTPException, preserving the original status code
        raise
    except Exception as e:
        logger.error(f"生成音频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=os.path.basename(audio_path)
    )


# ============================================
# Background task functions
# ============================================

async def _generate_audio_task(
    task_id: str,
    voice: Optional[str] = None,
    output_path: Optional[str] = None,
    enable_llm: bool = True
):
    """
    Background audio generation task

    Args:
        task_id: Task ID
        voice: Voice timbre
        output_path: Output path
        enable_llm: Whether to enable LLM
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        # Initialize managers (no need to pass settings; managers use config internally)
        llm_manager = LLMManager() if enable_llm else None
        tts_manager = TTSManager()
        audio_exporter = AudioExporter()
        
        # Get chapter data
        chapters_data = task.metadata.get("chapters", [])
        
        # Generate audio chapter by chapter
        for chapter_data in chapters_data:
            chapter_index = chapter_data["index"]
            chapter_title = chapter_data["title"]
            chapter_content = chapter_data["content"]
            
            logger.info(f"开始生成章节 {chapter_index}: {chapter_title}")
            
            # Update chapter status
            task_manager.update_chapter_status(
                task_id,
                chapter_index,
                TaskStatus.GENERATING
            )
            
            try:
                # LLM colloquialization (optional)
                if enable_llm and llm_manager:
                    logger.info(f"章节 {chapter_index} 开始 LLM 口语化")
                    chapter_content = llm_manager.colloquialize_text(chapter_content)
                
                # Generate the audio file path
                audio_path = audio_exporter.get_output_path(
                    index=chapter_index,
                    title=chapter_title,
                    role="default",
                    custom_base_path=output_path
                )
                
                # TTS generate audio
                logger.info(f"章节 {chapter_index} 开始 TTS 生成")
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
                
                logger.info(f"章节 {chapter_index} 生成完成: {audio_path}")
            
            except Exception as e:
                logger.error(f"章节 {chapter_index} 生成失败: {e}")
                task_manager.update_chapter_status(
                    task_id,
                    chapter_index,
                    TaskStatus.FAILED,
                    error=str(e)
                )
        
        # Update task status to completed
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
        logger.info(f"任务 {task_id} 全部完成")
    
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}")
        task_manager.update_task_status(task_id, TaskStatus.FAILED)


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

