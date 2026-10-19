"""
GA Sprite Birds - Chapter heading normalizer

Normalizes irregular chapter-heading formats into a canonical form so that
ChapterParser can rely on a single, stable chapter format instead of adding
per-article regular expressions.

Supported input formats (examples):
    **第一章** **世界新秩序**   ->  第一章 世界新秩序
    ## 第一章 世界新秩序         ->  第一章 世界新秩序
    ### 第一节 小节              ->  第一节 小节
    第一章 世界新秩序            ->  第一章 世界新秩序 (unchanged)

Body text that merely starts with a chapter marker, e.g. "第三回合谈判...",
is left untouched.

Version: v1.0
Dev team: Tiger
"""

import re

from loguru import logger

from ga_birds.Common.i18n import t

# Chapter marker: 第一章 / 第3回 / 第二节 / 第三卷
_CHAPTER_MARKER = r'第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节]'

# A chapter heading must not be followed directly by a Chinese character,
# otherwise text like "第三回合谈判" would be misdetected as a chapter.
_CHAPTER_HEAD = re.compile(rf'^{_CHAPTER_MARKER}(?![\u4e00-\u9fff])')

# Markdown heading marks (# ## ...) at the beginning of a line
_HEADING_MARK = re.compile(r'^\s*#{1,6}\s*')

# Bold / italic / code marks
_EMPHASIS_MARK = re.compile(r'[*_`]+')

# Consecutive whitespace left after removing marks
_EXTRA_SPACE = re.compile(r'[ \t]{2,}')

# Separators sometimes placed between the marker and the title, e.g. "第一章：标题"
_TITLE_SEPARATOR = re.compile(r'^[：:\-—–－、.。·\s]+')


def _normalize_line(line: str) -> str:
    """
    Normalize a single line if it is a chapter heading.

    Args:
        line: original line

    Returns:
        canonical heading line, or the original line when it is not a heading
    """
    candidate = _EMPHASIS_MARK.sub('', line).strip()
    candidate = _HEADING_MARK.sub('', candidate).strip()
    candidate = _EXTRA_SPACE.sub(' ', candidate)

    match = _CHAPTER_HEAD.match(candidate)
    if not match:
        return line

    marker = match.group(0)
    title = _TITLE_SEPARATOR.sub('', candidate[match.end():])
    return f"{marker} {title}".strip()


def normalize_chapter_headings(text: str) -> str:
    """
    Normalize chapter-heading lines in the text.

    Args:
        text: original text

    Returns:
        text with chapter headings in canonical form
    """
    lines = text.split('\n')
    normalized = [_normalize_line(line) for line in lines]

    changed = sum(1 for old, new in zip(lines, normalized) if old != new)
    if changed:
        logger.info(t("file.normalize_done", count=changed))

    return '\n'.join(normalized)
