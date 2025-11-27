"""
GA Sprite Birds - 文件处理工具
支持文本文件读取、编码检测、PDF 提取等

版本: v1.0
开发团队: Tiger
"""

from pathlib import Path
from typing import Optional
import re

import chardet
from pypdf import PdfReader
from loguru import logger


def detect_encoding(file_path: str) -> str:
    """
    检测文件编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        编码名称（如 utf-8, gbk, ascii）
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
        
        result = chardet.detect(raw_data)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0)
        
        logger.info(f"检测到文件编码: {encoding} (置信度: {confidence:.2f})")
        
        # 如果置信度太低，默认使用 utf-8
        if confidence < 0.7:
            logger.warning(f"编码检测置信度较低，使用默认编码 utf-8")
            return "utf-8"
        
        return encoding
    except Exception as e:
        logger.error(f"编码检测失败: {e}，使用默认编码 utf-8")
        return "utf-8"


def read_text_file(file_path: str, encoding: Optional[str] = None) -> str:
    """
    读取文本文件（支持自动编码检测）

    Args:
        file_path: 文件路径
        encoding: 编码（如果为 None，则自动检测）

    Returns:
        文件内容
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
    智能读取文件（根据扩展名自动选择读取方式）

    Args:
        file_path: 文件路径

    Returns:
        文件内容

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件格式
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
    从 PDF 文件提取文本
    
    Args:
        file_path: PDF 文件路径
        
    Returns:
        提取的文本内容
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
    文本预处理
    
    Args:
        text: 原始文本
        remove_extra_newlines: 是否去除多余换行
        remove_headers_footers: 是否去除页眉页脚
        fix_pdf_linebreaks: 是否修复 PDF 换行
        
    Returns:
        处理后的文本
    """
    processed = text
    
    # 修复 PDF 换行（将段落中间的换行符去除）
    if fix_pdf_linebreaks:
        # 简单策略：如果一行不是以句号、问号、感叹号结尾，则与下一行合并
        lines = processed.split("\n")
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line:
                # 如果当前行不是以标点结尾，且下一行存在，则合并
                if i + 1 < len(lines) and not line.endswith(("。", "！", "？", ".", "!", "?")):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line[0].isupper():
                        line = line + next_line
                        i += 1
                fixed_lines.append(line)
            i += 1
        processed = "\n".join(fixed_lines)
    
    # 去除多余换行（连续的空行只保留一个）
    if remove_extra_newlines:
        import re
        processed = re.sub(r'\n{3,}', '\n\n', processed)
    
    # 去除页眉页脚（简单策略：去除每页开头和结尾的短行）
    if remove_headers_footers:
        # 这里可以根据实际情况调整策略
        pass
    
    logger.info(f"文本预处理完成，处理前: {len(text)} 字符，处理后: {len(processed)} 字符")

    return processed


def clean_text_for_tts(text: str) -> str:
    """
    清理文本用于 TTS 生成

    处理以下问题：
    1. 移除文本两端的引号（中英文引号）
    2. 如果文本只包含引号和标点，返回空字符串
    3. 保留文本中间的引号和标点

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 定义各种引号
    quotes = [
        '"', '"', '"',      # 英文双引号、中文左右双引号
        "'", ''', ''',      # 英文单引号、中文左右单引号
        '「', '」',         # 日文引号
        '『', '』',         # 日文书名号
        '《', '》',         # 中文书名号
    ]

    # 移除文本两端的引号和空白
    cleaned = text.strip()

    # 循环移除两端的引号，直到没有引号为止
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

    # 检查清理后的文本是否只包含标点符号
    # 如果只有标点（如 "……"、"。。。"），返回空字符串
    if cleaned:
        # 移除所有标点后检查是否还有内容
        text_without_punctuation = re.sub(r'[，。！？；：、,.!?;:\s…—\-\.\*]+', '', cleaned)
        if not text_without_punctuation:
            logger.debug(f"文本只包含标点，跳过: {repr(text)}")
            return ""

    return cleaned

