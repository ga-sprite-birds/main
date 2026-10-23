"""
GA Sprite Birds - Common base module
Provides infrastructure shared by the CLI and API

Includes:
- ConfigManager: configuration manager (wraps the config module)
- ParamManager: parameter manager (CLI/API parameter merging and validation)
- ChapterTextSaver: chapter text saver (single-character / multi-character text saving)
- ChapterProcessor: chapter processor (intro/outro handling)
- chapter_loader: shared file reading and chapter parsing
- i18n: multilingual support (t, set_locale, get_i18n)
"""

from .config_manager import ConfigManager
from .param_manager import ParamManager
from .text_saver import ChapterTextSaver
from .chapter_processor import ChapterProcessor
from .i18n import t, set_locale, get_i18n


def load_chapters(file_path: str):
    """Load and parse chapters (imported lazily to avoid a Utils/Common cycle)."""
    from .chapter_loader import load_chapters as _load_chapters

    return _load_chapters(file_path)


__all__ = [
    "ConfigManager",
    "ParamManager",
    "ChapterTextSaver",
    "ChapterProcessor",
    "load_chapters",
    "t",
    "set_locale",
    "get_i18n",
]
