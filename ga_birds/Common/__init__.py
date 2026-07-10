"""
GA Sprite Birds - Common base module
Provides infrastructure shared by the CLI and API

Includes:
- ConfigManager: configuration manager (wraps the config module)
- ParamManager: parameter manager (CLI/API parameter merging and validation)
- ChapterTextSaver: chapter text saver (single-character / multi-character text saving)
- ChapterProcessor: chapter processor (intro/outro handling)
- i18n: multilingual support (t, set_locale, get_i18n)
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

