"""
GA Sprite Birds - Chapter loader
Shared text loading, preprocessing, heading normalization, and chapter parsing.

This is the single entry point used by both the CLI and the API so that a
chapter is always parsed exactly the same way.
"""

from typing import List

from loguru import logger

import config
from ga_birds.Common.i18n import t
from ga_birds.Parser import Chapter, ChapterParser
from ga_birds.Utils.file_utils import preprocess_text, read_file
from ga_birds.Utils.text_normalizer import normalize_chapter_headings


def load_chapters(file_path: str) -> List[Chapter]:
    """
    Read a file and split it into chapters.

    Args:
        file_path: path to a .txt, .md, or .pdf file

    Returns:
        parsed chapter list
    """
    text = read_file(file_path)

    if config.TEXT_PREPROCESSING_ENABLED:
        # PDF extraction inserts hard line breaks inside paragraphs; text and
        # Markdown already preserve their own line structure.
        is_pdf = str(file_path).lower().endswith(".pdf")
        text = preprocess_text(
            text,
            remove_extra_newlines=True,
            fix_pdf_linebreaks=is_pdf
        )

    if config.CHAPTER_NORMALIZE_ENABLED:
        text = normalize_chapter_headings(text)

    parser = ChapterParser(
        regex_patterns=config.CHAPTER_REGEX_PATTERNS,
        min_length=config.CHAPTER_MIN_LENGTH,
        keep_title=config.CHAPTER_KEEP_TITLE
    )
    chapters = parser.parse(text)
    logger.info(t("chapter.loaded", count=len(chapters)))
    return chapters
