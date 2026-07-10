"""
GA Sprite Birds - Task manager
Manages async task creation, execution, and status queries

Version: v1.0
Dev team: Tiger
"""

import uuid
import asyncio
import importlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime

from loguru import logger

from ga_birds.Common.i18n import t

import config

# Dynamically import the core module
_core_module_name = config.CORE_DIR.replace('-', '_')
_parser_module = importlib.import_module(f'{_core_module_name}.Parser')
Chapter = _parser_module.Chapter


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"  # waiting
    PARSING = "parsing"  # parsing
    PARSED = "parsed"  # parsed
    GENERATING = "generating"  # generating
    COMPLETED = "completed"  # completed
    FAILED = "failed"  # failed
    CANCELLED = "cancelled"  # cancelled


@dataclass
class ChapterProgress:
    """Chapter progress"""
    index: int  # chapter number
    title: str  # chapter title
    status: TaskStatus = TaskStatus.PENDING  # status
    audio_path: Optional[str] = None  # audio file path
    error: Optional[str] = None  # error message
    started_at: Optional[datetime] = None  # start time
    completed_at: Optional[datetime] = None  # completion time


@dataclass
class Task:
    """Task data class"""
    task_id: str  # task ID
    status: TaskStatus = TaskStatus.PENDING  # task status
    total_chapters: int = 0  # total chapter count
    completed_chapters: int = 0  # completed chapter count
    chapters: List[ChapterProgress] = field(default_factory=list)  # chapter progress list
    error: Optional[str] = None  # error message
    created_at: datetime = field(default_factory=datetime.now)  # creation time
    started_at: Optional[datetime] = None  # start time
    completed_at: Optional[datetime] = None  # completion time
    metadata: Dict[str, Any] = field(default_factory=dict)  # metadata (file name, config, etc.)


class TaskManager:
    """Task manager"""

    def __init__(self):
        """Initialize the task manager"""
        self.tasks: Dict[str, Task] = {}
        self.max_concurrent_tasks = config.TASK_MAX_CONCURRENT
        self.running_tasks: Dict[str, asyncio.Task] = {}

        logger.info(t("task.manager_initialized", count=self.max_concurrent_tasks))
    
    def create_task(
        self,
        chapters: Optional[List[Chapter]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new task

        Args:
            chapters: chapter list
            metadata: metadata

        Returns:
            task ID
        """
        task_id = str(uuid.uuid4())

        # Create the chapter progress list
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
        logger.info(t("task.task_created", task_id=task_id, count=task.total_chapters))
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task

        Args:
            task_id: task ID

        Returns:
            task object, or None if it does not exist
        """
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """
        Update task status

        Args:
            task_id: task ID
            status: new status
        """
        task = self.get_task(task_id)
        if task:
            task.status = status
            
            if status == TaskStatus.GENERATING and task.started_at is None:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
            
            logger.info(t("task.task_status_updated", task_id=task_id, status=status.value))
    
    def update_chapter_status(
        self,
        task_id: str,
        chapter_index: int,
        status: TaskStatus,
        audio_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update chapter status

        Args:
            task_id: task ID
            chapter_index: chapter number
            status: new status
            audio_path: audio file path
            error: error message
        """
        task = self.get_task(task_id)
        if not task:
            return

        # Find the chapter
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
                
                # Update the completed chapter count
                if status == TaskStatus.COMPLETED:
                    task.completed_chapters += 1
                    logger.info(t("task.chapter_completed", task_id=task_id, index=chapter_index, title=chapter.title))
                
                break
    
    def get_chapter_audio(self, task_id: str, chapter_index: int) -> Optional[str]:
        """
        Get the chapter audio path

        Args:
            task_id: task ID
            chapter_index: chapter number

        Returns:
            audio file path, or None if it does not exist
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
        List all tasks

        Returns:
            task list
        """
        return list(self.tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task

        Args:
            task_id: task ID

        Returns:
            whether cancellation succeeded
        """
        task = self.get_task(task_id)
        if not task:
            return False

        # Cancel the running async task
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        self.update_task_status(task_id, TaskStatus.CANCELLED)
        logger.info(t("task.task_cancelled", task_id=task_id))
        
        return True
    
    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """
        Get task progress

        Args:
            task_id: task ID

        Returns:
            progress info dictionary
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

