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

        logger.info(f"检测到文件编码: {encoding} (置信度: {confidence:.2f})")

        # If confidence is too low, default to utf-8
        if confidence < 0.7:
            logger.warning(f"编码检测置信度较低，使用默认编码 utf-8")
            return "utf-8"
        
        return encoding
    except Exception as e:
        logger.error(f"编码检测失败: {e}，使用默认编码 utf-8")
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
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        if encoding is None:
            encoding = detect_encoding(file_path)

        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        logger.info(f"成功读取文件: {file_path} ({len(content)} 字符)")
        return content
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, 错误: {e}")
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
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = path.suffix.lower()

    if suffix == '.txt':
        content = read_text_file(file_path)
    elif suffix == '.pdf':
        content = extract_pdf_text(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")

    if not content or not content.strip():
        raise ValueError("文件内容为空")

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
            logger.debug(f"提取第 {page_num} 页，字符数: {len(text)}")
        
        full_text = "\n".join(text_parts)
        logger.info(f"成功提取 PDF 文本: {file_path} ({len(full_text)} 字符)")
        
        return full_text
    except Exception as e:
        logger.error(f"提取 PDF 文本失败: {file_path}, 错误: {e}")
        raise


def preprocess_text(
    text: str,
    remove_extra_newlines: bool = True,
    remove_headers_footers: bool = True,
    fix_pdf_linebreaks: bool = True
) -> str:
    """
    Text preprocessing

    Args:
        text: original text
        remove_extra_newlines: whether to remove extra newlines
        remove_headers_footers: whether to remove headers and footers
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
        import re
        processed = re.sub(r'\n{3,}', '\n\n', processed)

    # Remove headers and footers (simple strategy: remove short lines at the start and end of each page)
    if remove_headers_footers:
        # This strategy can be adjusted based on actual conditions
        pass
    
    logger.info(f"文本预处理完成，处理前: {len(text)} 字符，处理后: {len(processed)} 字符")

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
            logger.debug(f"文本只包含标点，跳过: {repr(text)}")
            return ""

    return cleaned

