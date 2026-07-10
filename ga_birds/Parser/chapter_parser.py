"""
GA Sprite Birds - Chapter parser
Uses regular expressions to detect and split chapters

Version: v1.0
Dev team: Tiger
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from loguru import logger

from ga_birds.Common.i18n import t


@dataclass
class Chapter:
    """Chapter data class"""
    index: int  # chapter number (starting from 1)
    title: str  # chapter title
    content: str  # chapter content
    start_pos: int  # start position in the original text
    end_pos: int  # end position in the original text


class ChapterParser:
    """Chapter parser"""
    
    def __init__(
        self,
        regex_patterns: Optional[List[str]] = None,
        min_length: int = 100,
        keep_title: bool = True
    ):
        """
        Initialize the chapter parser

        Args:
            regex_patterns: list of chapter title regular expressions
            min_length: minimum chapter length (to avoid false detection)
            keep_title: whether to keep the chapter title in the content
        """
        self.regex_patterns = regex_patterns or [
            r'^第[零一二三四五六七八九十百千万0-9]+章',
            r'^Chapter\s+\d+',
            r'^第[零一二三四五六七八九十百千万0-9]+回'
        ]
        self.min_length = min_length
        self.keep_title = keep_title

        # Compile the regular expressions
        self.compiled_patterns = [
            re.compile(pattern, re.MULTILINE) for pattern in self.regex_patterns
        ]
        
        logger.info(t("parser.initialized", count=len(self.regex_patterns)))
    
    def parse(self, text: str) -> List[Chapter]:
        """
        Parse the text and split into chapters

        Args:
            text: original text

        Returns:
            chapter list
        """
        # Find all chapter title positions
        chapter_positions = []

        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                # Get the matched line
                line_start = text.rfind('\n', 0, match.start()) + 1
                line_end = text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(text)

                title = text[line_start:line_end].strip()
                chapter_positions.append((line_start, title))

        # Sort by position and deduplicate
        chapter_positions = sorted(set(chapter_positions), key=lambda x: x[0])

        if not chapter_positions:
            logger.warning(t("parser.no_chapters"))
            return [Chapter(
                index=1,
                title=t("parser.full_text_title"),
                content=text,
                start_pos=0,
                end_pos=len(text)
            )]

        logger.info(t("parser.chapters_found", count=len(chapter_positions)))

        # Split chapters
        chapters = []
        for i, (pos, title) in enumerate(chapter_positions):
            # Determine the chapter content range
            start_pos = pos
            if i + 1 < len(chapter_positions):
                end_pos = chapter_positions[i + 1][0]
            else:
                end_pos = len(text)

            # Extract chapter content
            content = text[start_pos:end_pos].strip()

            # If the title is not kept, remove the first line
            if not self.keep_title:
                first_newline = content.find('\n')
                if first_newline != -1:
                    content = content[first_newline + 1:].strip()

            # Check chapter length
            if len(content) < self.min_length:
                logger.warning(t("parser.chapter_too_short", title=title, length=len(content)))
                continue

            chapter = Chapter(
                index=len(chapters) + 1,
                title=title,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos
            )
            chapters.append(chapter)

            logger.debug(t("parser.chapter_parsed", index=chapter.index, title=title, length=len(content)))

        logger.info(t("parser.parse_complete", count=len(chapters)))
        return chapters

    def get_chapter_by_index(self, chapters: List[Chapter], index: int) -> Optional[Chapter]:
        """
        Get a chapter by its number

        Args:
            chapters: chapter list
            index: chapter number (starting from 1)

        Returns:
            chapter object, or None if it does not exist
        """
        for chapter in chapters:
            if chapter.index == index:
                return chapter
        return None

