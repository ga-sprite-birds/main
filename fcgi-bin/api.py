"""
GA Sprite Birds - FastAPI 统一路由入口
提供文本上传、解析、生成、任务查询等 API

版本: v1.0
开发团队: Tiger
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

# 初始化多语言（默认使用配置文件）
_core_module_name = config.CORE_DIR.replace('-', '_')
_i18n_module = importlib.import_module(f'{_core_module_name}.Common.i18n')
_i18n_module.set_locale(config.LANGUAGE)

# 动态导入核心模块（根据 config.CORE_DIR）
_utils_module = importlib.import_module(f'{_core_module_name}.Utils')
_parser_module = importlib.import_module(f'{_core_module_name}.Parser')
_llm_module = importlib.import_module(f'{_core_module_name}.LLM')
_audio_module = importlib.import_module(f'{_core_module_name}.Audio')
_sprite_module = importlib.import_module(f'{_core_module_name}.Sprite')
_task_module = importlib.import_module(f'{_core_module_name}.Task')

# 导入需要的类和函数
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


# 初始化 FastAPI 应用
app = FastAPI(
    title="音频朗读系统 API",
    description="将文本转换为音频的 API 服务",
    version="1.0.0",
    debug=config.API_DEBUG
)

# 配置 CORS
if config.API_CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.API_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 初始化管理器
task_manager = TaskManager()
sprite_manager = SpriteManager()


# ============================================
# 请求/响应模型
# ============================================

class UploadRequest(BaseModel):
    """上传请求"""
    path: Optional[str] = None  # 本地文件路径
    output_path: Optional[str] = None  # 自定义输出路径
    language: Optional[str] = None  # 界面语言（en_US, zh_CN）


class ParseRequest(BaseModel):
    """解析请求"""
    task_id: str  # 任务 ID
    language: Optional[str] = None  # 界面语言（en_US, zh_CN）


class GenerateRequest(BaseModel):
    """生成请求"""
    task_id: str  # 任务 ID
    voice: Optional[str] = None  # 音色（覆盖配置）
    output_path: Optional[str] = None  # 输出路径（覆盖配置）
    enable_llm: bool = True  # 是否启用 LLM 口语化
    language: Optional[str] = None  # 界面语言（en_US, zh_CN）


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str


# ============================================
# API 路由
# ============================================

@app.get("/")
async def root():
    """根路径"""
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
    上传文本文件或指定本地路径

    Args:
        file: 上传的文件对象
        path: 本地文件路径（优先使用）
        output_path: 自定义输出路径
        language: 界面语言（en_US, zh_CN）

    Returns:
        任务信息
    """
    # 设置语言
    if language:
        _i18n_module.set_locale(language)

    try:
        # 优先使用本地路径
        if path:
            file_path = path
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        elif file:
            # 保存上传的文件
            upload_dir = Path("./uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            logger.info(f"文件上传成功: {file_path}")
        else:
            raise HTTPException(status_code=400, detail="必须提供文件或路径")
        
        # 创建任务
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
    
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse", response_model=TaskResponse)
async def parse_text(request: ParseRequest):
    """
    解析文本，拆分章节

    Args:
        request: 解析请求

    Returns:
        任务信息
    """
    # 设置语言
    if request.language:
        _i18n_module.set_locale(request.language)

    try:
        task = task_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {request.task_id}")
        
        # 更新任务状态
        task_manager.update_task_status(request.task_id, TaskStatus.PARSING)
        
        # 读取文件
        file_path = task.metadata.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="任务中未找到文件路径")
        
        # 根据文件类型读取内容
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".pdf":
            text = extract_pdf_text(file_path)
        else:
            text = read_text_file(file_path)
        
        # 文本预处理
        if settings.text_preprocessing.enabled:
            text = preprocess_text(
                text,
                remove_extra_newlines=settings.text_preprocessing.remove_extra_newlines,
                remove_headers_footers=settings.text_preprocessing.remove_headers_footers,
                fix_pdf_linebreaks=settings.text_preprocessing.fix_pdf_linebreaks
            )
        
        # 章节拆分
        parser = ChapterParser(
            regex_patterns=settings.chapter.regex_patterns,
            min_length=settings.chapter.min_length,
            keep_title=settings.chapter.keep_title
        )
        chapters = parser.parse(text)
        
        # 更新任务章节信息
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
        
        # 保存章节数据到任务元数据
        task.metadata["chapters"] = [
            {
                "index": ch.index,
                "title": ch.title,
                "content": ch.content
            }
            for ch in chapters
        ]
        
        logger.info(f"任务 {request.task_id} 解析完成，共 {len(chapters)} 章")
        
        return TaskResponse(
            task_id=request.task_id,
            status="parsed",
            message=f"解析完成，共 {len(chapters)} 章"
        )
    
    except Exception as e:
        logger.error(f"文本解析失败: {e}")
        task_manager.update_task_status(request.task_id, TaskStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_model=TaskResponse)
async def generate_audio(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    开始生成音频（异步）

    Args:
        request: 生成请求
        background_tasks: 后台任务

    Returns:
        任务信息
    """
    # 设置语言
    if request.language:
        _i18n_module.set_locale(request.language)

    try:
        task = task_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {request.task_id}")
        
        # 检查任务是否已解析
        if not task.metadata.get("chapters"):
            raise HTTPException(status_code=400, detail="任务尚未解析，请先调用 /parse")
        
        # 添加后台任务
        background_tasks.add_task(
            _generate_audio_task,
            task_id=request.task_id,
            voice=request.voice,
            output_path=request.output_path,
            enable_llm=request.enable_llm
        )
        
        # 更新任务状态
        task_manager.update_task_status(request.task_id, TaskStatus.GENERATING)
        
        return TaskResponse(
            task_id=request.task_id,
            status="generating",
            message="音频生成已开始，请通过 /task/{id}/status 查询进度"
        )
    
    except Exception as e:
        logger.error(f"生成音频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务进度信息
    """
    progress = task_manager.get_task_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return progress


@app.get("/task/{task_id}/chapter/{chapter_index}")
async def get_chapter_audio(task_id: str, chapter_index: int):
    """
    获取单章音频文件
    
    Args:
        task_id: 任务 ID
        chapter_index: 章节序号
        
    Returns:
        音频文件
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
# 后台任务函数
# ============================================

async def _generate_audio_task(
    task_id: str,
    voice: Optional[str] = None,
    output_path: Optional[str] = None,
    enable_llm: bool = True
):
    """
    后台生成音频任务
    
    Args:
        task_id: 任务 ID
        voice: 音色
        output_path: 输出路径
        enable_llm: 是否启用 LLM
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        # 初始化管理器
        llm_manager = LLMManager(settings) if enable_llm else None
        tts_manager = TTSManager(settings)
        audio_exporter = AudioExporter(settings)
        
        # 获取章节数据
        chapters_data = task.metadata.get("chapters", [])
        
        # 逐章生成音频
        for chapter_data in chapters_data:
            chapter_index = chapter_data["index"]
            chapter_title = chapter_data["title"]
            chapter_content = chapter_data["content"]
            
            logger.info(f"开始生成章节 {chapter_index}: {chapter_title}")
            
            # 更新章节状态
            task_manager.update_chapter_status(
                task_id,
                chapter_index,
                TaskStatus.GENERATING
            )
            
            try:
                # LLM 口语化（可选）
                if enable_llm and llm_manager:
                    logger.info(f"章节 {chapter_index} 开始 LLM 口语化")
                    chapter_content = llm_manager.colloquialize_text(chapter_content)
                
                # 生成音频文件路径
                audio_path = audio_exporter.get_output_path(
                    index=chapter_index,
                    title=chapter_title,
                    role="default",
                    custom_base_path=output_path
                )
                
                # TTS 生成音频
                logger.info(f"章节 {chapter_index} 开始 TTS 生成")
                await tts_manager.generate_audio(
                    text=chapter_content,
                    output_path=str(audio_path),
                    voice=voice
                )
                
                # 更新章节状态为完成
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
        
        # 更新任务状态为完成
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
        logger.info(f"任务 {task_id} 全部完成")
    
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}")
        task_manager.update_task_status(task_id, TaskStatus.FAILED)


# ============================================
# 启动配置
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    # 配置日志
    from loguru import logger
    logger.add(
        settings.logging.file,
        rotation=f"{settings.logging.max_file_size} MB",
        retention=settings.logging.backup_count,
        level=settings.logging.level,
        format=settings.logging.format
    )
    
    # 启动服务
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.logging.level.lower()
    )

