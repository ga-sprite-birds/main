"""
GA Sprite Birds - File handling utilities
Supports text file reading, encoding detection, PDF extraction, etc.

Version: v1.0
Dev team: Tiger
"""

from pathlib import Path
from typing import Optional
import re

import chardet
from pypdf import PdfReader
from loguru import logger
from ga_birds.Common.i18n import t


# File extensions accepted by the loader and the upload endpoint
SUPPORTED_INPUT_EXTENSIONS = {".txt", ".md", ".pdf"}


def get_unique_filename(path: Path) -> Path:
    """
    If the file already exists, generate a unique file name (similar to Windows renaming)

    Args:
        path: original file path

    Returns:
        unique file path
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding

    Args:
        file_path: file path

    Returns:
        encoding name (e.g. utf-8, gbk, ascii)
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()

        result = chardet.detect(raw_data)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0)

        logger.info(t("file.encoding_detected", encoding=encoding, confidence=confidence))

        # If confidence is too low, default to utf-8
        if confidence < 0.7:
            logger.warning(t("file.encoding_low_confidence"))
            return "utf-8"

        return encoding
    except Exception as e:
        logger.error(t("file.encoding_detect_failed", error=e))
        return "utf-8"


def read_text_file(file_path: str, encoding: Optional[str] = None) -> str:
    """
    Read a text file (supports automatic encoding detection)

    Args:
        file_path: file path
        encoding: encoding (auto-detected if None)

    Returns:
        file content
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(t("file.file_not_found", path=file_path))

    try:
        if encoding is None:
            encoding = detect_encoding(file_path)

        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        logger.info(t("file.read_success", path=file_path, size=len(content)))
        return content
    except Exception as e:
        logger.error(t("file.read_failed", path=file_path, error=e))
        raise


def read_file(file_path: str) -> str:
    """
    Smart file reading (automatically selects the reading method by extension)

    Args:
        file_path: file path

    Returns:
        file content

    Raises:
        FileNotFoundError: file does not exist
        ValueError: unsupported file format
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(t("file.file_not_found", path=file_path))

    suffix = path.suffix.lower()

    if suffix in ('.txt', '.md'):
        content = read_text_file(file_path)
    elif suffix == '.pdf':
        content = extract_pdf_text(file_path)
    else:
        raise ValueError(t("file.unsupported_format", suffix=suffix))

    if not content or not content.strip():
        raise ValueError(t("file.empty_content"))

    return content


def extract_pdf_text(file_path: str) -> str:
    """
    Extract text from a PDF file

    Args:
        file_path: PDF file path

    Returns:
        extracted text content
    """
    try:
        reader = PdfReader(file_path)
        text_parts = []

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text:
                text_parts.append(text)
            logger.debug(t("file.pdf_page_extracted", page=page_num, length=len(text)))

        full_text = "\n".join(text_parts)
        logger.info(t("file.pdf_extract_success", path=file_path, size=len(full_text)))

        return full_text
    except Exception as e:
        logger.error(t("file.pdf_extract_failed", path=file_path, error=e))
        raise


def preprocess_text(
    text: str,
    remove_extra_newlines: bool = True,
    fix_pdf_linebreaks: bool = True
) -> str:
    """
    Text preprocessing

    Args:
        text: original text
        remove_extra_newlines: whether to remove extra newlines
        fix_pdf_linebreaks: whether to fix PDF line breaks

    Returns:
        processed text
    """
    processed = text

    # Fix PDF line breaks (remove line breaks in the middle of paragraphs)
    if fix_pdf_linebreaks:
        # Simple strategy: if a line does not end with a period, question mark, or exclamation mark, merge it with the next line
        lines = processed.split("\n")
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line:
                # If the current line does not end with punctuation and the next line exists, merge them
                if i + 1 < len(lines) and not line.endswith(("。", "！", "？", ".", "!", "?")):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line[0].isupper():
                        line = line + next_line
                        i += 1
                fixed_lines.append(line)
            i += 1
        processed = "\n".join(fixed_lines)

    # Remove extra newlines (keep only one of consecutive blank lines)
    if remove_extra_newlines:
        processed = re.sub(r'\n{3,}', '\n\n', processed)

    logger.info(t("file.preprocess_done", before=len(text), after=len(processed)))

    return processed


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS generation

    Handles the following:
    1. Remove quotes at both ends of the text (Chinese and English quotes)
    2. If the text contains only quotes and punctuation, return an empty string
    3. Keep quotes and punctuation in the middle of the text

    Args:
        text: original text

    Returns:
        cleaned text
    """
    if not text:
        return ""

    # Define various quote characters
    quotes = [
        '"', '"', '"',      # English double quotes, Chinese left/right double quotes
        "'", ''', ''',      # English single quotes, Chinese left/right single quotes
        '「', '」',         # Japanese corner brackets
        '『', '』',         # Japanese double corner brackets (book title marks)
        '《', '》',         # Chinese book title marks
    ]

    # Remove quotes and whitespace at both ends of the text
    cleaned = text.strip()

    # Repeatedly remove quotes at both ends until none remain
    while cleaned:
        stripped = False
        for quote in quotes:
            if cleaned.startswith(quote):
                cleaned = cleaned[len(quote):].lstrip()
                stripped = True
            if cleaned.endswith(quote):
                cleaned = cleaned[:-len(quote)].rstrip()
                stripped = True
        if not stripped:
            break

    # Check whether the cleaned text contains only punctuation
    # If it is only punctuation (e.g. "……", "。。。"), return an empty string
    if cleaned:
        # Remove all punctuation and check whether any content remains
        text_without_punctuation = re.sub(r'[，。！？；：、,.!?;:\s…—\-\.\*]+', '', cleaned)
        if not text_without_punctuation:
            logger.debug(t("file.text_only_punctuation", text=repr(text)))
            return ""

    return cleaned

