"""
GA Sprite Birds - 公共基础模块
提供 CLI 和 API 共用的基础设施

包含：
- ConfigManager: 配置管理器（封装 config 模块）
- ParamManager: 参数管理器（CLI/API 参数合并与验证）
- ChapterTextSaver: 章节文本保存器（单角色/多角色文本保存）
- ChapterProcessor: 章节处理器（片头片尾处理）
- i18n: 多语言支持（t, set_locale, get_i18n）
"""

from .config_manager import ConfigManager
from .param_manager import ParamManager
from .text_saver import ChapterTextSaver
from .chapter_processor import ChapterProcessor
from .i18n import t, set_locale, get_i18n

__all__ = [
    "ConfigManager",
    "ParamManager",
    "ChapterTextSaver",
    "ChapterProcessor",
    "t",
    "set_locale",
    "get_i18n",
]

