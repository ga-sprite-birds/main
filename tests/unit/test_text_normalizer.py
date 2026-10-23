"""
Test the chapter heading normalizer
"""

import sys
from pathlib import Path
import pytest

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ga_birds.Utils.text_normalizer import normalize_chapter_headings
from ga_birds.Parser.chapter_parser import ChapterParser

BODY = "这是一段用于测试章节拆分的正文内容。" * 10


@pytest.mark.unit
def test_normalize_markdown_bold_heading():
    """Bold Markdown headings become canonical headings"""
    text = f"**第一章** **示例标题**\n\n{BODY}\n\n**第二章** **示例标题二**\n\n{BODY}"
    result = normalize_chapter_headings(text)
    assert result.startswith("第一章 示例标题")
    assert "第二章 示例标题二" in result
    assert "**" not in result


@pytest.mark.unit
def test_normalize_markdown_hash_heading():
    """Markdown heading marks are removed"""
    text = f"## 第一章 开始\n\n{BODY}\n\n### 第一节 小节\n\n{BODY}"
    result = normalize_chapter_headings(text)
    assert result.startswith("第一章 开始")
    assert "第一节 小节" in result
    assert "##" not in result


@pytest.mark.unit
def test_normalize_keeps_plain_heading():
    """Canonical headings stay unchanged"""
    text = f"第一章 开始\n\n{BODY}"
    assert normalize_chapter_headings(text) == text


@pytest.mark.unit
def test_normalize_ignores_body_text():
    """Body text like '第三回合的比赛' is not treated as a chapter heading"""
    text = f"第三回合的比赛开始了。\n\n{BODY}"
    assert normalize_chapter_headings(text) == text


@pytest.mark.unit
def test_normalize_removes_title_separator():
    """A separator between marker and title is normalized to a single space"""
    text = f"## 第一章：示例标题\n\n{BODY}"
    assert normalize_chapter_headings(text).startswith("第一章 示例标题")


@pytest.mark.unit
def test_normalize_is_idempotent():
    """Normalizing twice yields the same result"""
    text = f"## 第一章 开始\n\n{BODY}\n\n## 第二章 继续\n\n{BODY}"
    once = normalize_chapter_headings(text)
    assert normalize_chapter_headings(once) == once


@pytest.mark.unit
def test_normalized_text_is_parsable():
    """Normalized text is recognized by the generic chapter parser"""
    text = f"**第一章** **示例标题**\n\n{BODY}\n\n**第二章** **示例标题二**\n\n{BODY}"
    parser = ChapterParser(min_length=100)
    chapters = parser.parse(normalize_chapter_headings(text))
    assert len(chapters) == 2
    assert chapters[0].title == "第一章 示例标题"
    assert chapters[1].title == "第二章 示例标题二"
