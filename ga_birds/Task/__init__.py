"""
Task management module
Responsible for async task creation, execution, and status management
"""

from .task_manager import TaskManager, Task, TaskStatus, ChapterProgress

__all__ = ["TaskManager", "Task", "TaskStatus", "ChapterProgress"]

