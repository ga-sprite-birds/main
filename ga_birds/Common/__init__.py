"""
GA Sprite Birds - 公共模块
提供 CLI 和 API 共用的核心业务逻辑

包含：
- ConfigManager: 配置管理器
- ParamManager: 参数管理器
- ChapterTextSaver: 章节文本保存器
- ChapterProcessor: 章节处理器（片头片尾）
"""

from .config_manager import ConfigManager
from .param_manager import ParamManager
from .text_saver import ChapterTextSaver
from .chapter_processor import ChapterProcessor

__all__ = [
    "ConfigManager",
    "ParamManager",
    "ChapterTextSaver",
    "ChapterProcessor",
]

