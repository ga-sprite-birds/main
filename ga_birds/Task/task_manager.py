"""
GA Sprite Birds - 任务管理器
管理异步任务的创建、执行和状态查询

版本: v1.0
开发团队: Tiger
"""

import uuid
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime

from loguru import logger

from ga_birds.Config import Settings
from ga_birds.Parser import Chapter


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 等待中
    PARSING = "parsing"  # 解析中
    GENERATING = "generating"  # 生成中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class ChapterProgress:
    """章节进度"""
    index: int  # 章节序号
    title: str  # 章节标题
    status: TaskStatus = TaskStatus.PENDING  # 状态
    audio_path: Optional[str] = None  # 音频文件路径
    error: Optional[str] = None  # 错误信息
    started_at: Optional[datetime] = None  # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间


@dataclass
class Task:
    """任务数据类"""
    task_id: str  # 任务 ID
    status: TaskStatus = TaskStatus.PENDING  # 任务状态
    total_chapters: int = 0  # 总章节数
    completed_chapters: int = 0  # 已完成章节数
    chapters: List[ChapterProgress] = field(default_factory=list)  # 章节进度列表
    error: Optional[str] = None  # 错误信息
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    started_at: Optional[datetime] = None  # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据（文件名、配置等）


class TaskManager:
    """任务管理器"""
    
    def __init__(self, settings: Settings):
        """
        初始化任务管理器
        
        Args:
            settings: 系统配置
        """
        self.settings = settings
        self.tasks: Dict[str, Task] = {}
        self.max_concurrent_tasks = settings.task.max_concurrent_tasks
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info(f"任务管理器初始化完成，最大并发任务数: {self.max_concurrent_tasks}")
    
    def create_task(
        self,
        chapters: Optional[List[Chapter]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建新任务
        
        Args:
            chapters: 章节列表
            metadata: 元数据
            
        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        
        # 创建章节进度列表
        chapter_progress = []
        if chapters:
            for chapter in chapters:
                chapter_progress.append(ChapterProgress(
                    index=chapter.index,
                    title=chapter.title
                ))
        
        task = Task(
            task_id=task_id,
            total_chapters=len(chapter_progress),
            chapters=chapter_progress,
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        logger.info(f"创建任务: {task_id}, 章节数: {task.total_chapters}")
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务对象，如果不存在则返回 None
        """
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            status: 新状态
        """
        task = self.get_task(task_id)
        if task:
            task.status = status
            
            if status == TaskStatus.GENERATING and task.started_at is None:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
            
            logger.info(f"任务 {task_id} 状态更新: {status}")
    
    def update_chapter_status(
        self,
        task_id: str,
        chapter_index: int,
        status: TaskStatus,
        audio_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        更新章节状态
        
        Args:
            task_id: 任务 ID
            chapter_index: 章节序号
            status: 新状态
            audio_path: 音频文件路径
            error: 错误信息
        """
        task = self.get_task(task_id)
        if not task:
            return
        
        # 查找章节
        for chapter in task.chapters:
            if chapter.index == chapter_index:
                chapter.status = status
                
                if status == TaskStatus.GENERATING and chapter.started_at is None:
                    chapter.started_at = datetime.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    chapter.completed_at = datetime.now()
                
                if audio_path:
                    chapter.audio_path = audio_path
                
                if error:
                    chapter.error = error
                
                # 更新已完成章节数
                if status == TaskStatus.COMPLETED:
                    task.completed_chapters += 1
                    logger.info(f"任务 {task_id} 章节 {chapter_index} 完成: {chapter.title}")
                
                break
    
    def get_chapter_audio(self, task_id: str, chapter_index: int) -> Optional[str]:
        """
        获取章节音频路径
        
        Args:
            task_id: 任务 ID
            chapter_index: 章节序号
            
        Returns:
            音频文件路径，如果不存在则返回 None
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        for chapter in task.chapters:
            if chapter.index == chapter_index:
                return chapter.audio_path
        
        return None
    
    def list_tasks(self) -> List[Task]:
        """
        列出所有任务
        
        Returns:
            任务列表
        """
        return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功取消
        """
        task = self.get_task(task_id)
        if not task:
            return False
        
        # 取消正在运行的异步任务
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        self.update_task_status(task_id, TaskStatus.CANCELLED)
        logger.info(f"任务 {task_id} 已取消")
        
        return True
    
    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务进度
        
        Args:
            task_id: 任务 ID
            
        Returns:
            进度信息字典
        """
        task = self.get_task(task_id)
        if not task:
            return {}
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "total_chapters": task.total_chapters,
            "completed_chapters": task.completed_chapters,
            "progress": task.completed_chapters / task.total_chapters if task.total_chapters > 0 else 0,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error
        }

