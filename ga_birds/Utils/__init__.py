"""
Utility module
Provides common functionality such as file handling, encoding detection, and model management
"""

from .file_utils import (
    detect_encoding,
    read_text_file,
    read_file,
    extract_pdf_text,
    preprocess_text,
    clean_text_for_tts,
    get_unique_filename
)
from .model_manager import ModelManager

__all__ = [
    "detect_encoding",
    "read_text_file",
    "read_file",
    "extract_pdf_text",
    "preprocess_text",
    "clean_text_for_tts",
    "get_unique_filename",
    "ModelManager",
]
