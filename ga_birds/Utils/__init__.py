"""
Utility module
Provides common functionality such as file handling, encoding detection, and model management
"""

from .file_utils import (
    SUPPORTED_INPUT_EXTENSIONS,
    detect_encoding,
    read_text_file,
    read_file,
    extract_pdf_text,
    preprocess_text,
    clean_text_for_tts,
    get_unique_filename
)
from .text_normalizer import normalize_chapter_headings
from .model_manager import ModelManager

__all__ = [
    "SUPPORTED_INPUT_EXTENSIONS",
    "detect_encoding",
    "read_text_file",
    "read_file",
    "extract_pdf_text",
    "preprocess_text",
    "clean_text_for_tts",
    "get_unique_filename",
    "normalize_chapter_headings",
    "ModelManager",
]
