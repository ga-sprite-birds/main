"""
GA Sprite Birds - Chapter processor
Handles intro/outro and other common logic (shared by single-character / multi-character modes)

Version: v1.0
Dev team: Tiger
"""

from typing import Tuple, Optional
from loguru import logger

from .config_manager import ConfigManager


class ChapterProcessor:
    """Chapter processor - handles intro/outro logic (common infrastructure)"""

    @staticmethod
    def prepare_intro_outro(
        chapter_index: int,
        chapter_title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Prepare the intro and outro text

        Args:
            chapter_index: chapter number
            chapter_title: chapter title

        Returns:
            (intro, outro) tuple, or (None, None) if not enabled
        """
        if not ConfigManager.is_chapter_intro_outro_enabled():
            logger.debug("  → 片头片尾未启用")
            return None, None

        intro = ConfigManager.get_chapter_intro_template().format(
            index=chapter_index,
            title=chapter_title
        )
        outro = ConfigManager.get_chapter_outro_template()

        logger.debug(f"  → 片头: {intro}")
        logger.debug(f"  → 片尾: {outro}")

        return intro, outro

    @staticmethod
    def combine_content_with_intro_outro(
        content: str,
        intro: Optional[str],
        outro: Optional[str]
    ) -> str:
        """
        Combine content with intro and outro (single-character voice mode)

        Args:
            content: main body content
            intro: intro text
            outro: outro text

        Returns:
            combined full text
        """
        if intro and outro:
            return f"{intro}。\n\n{content}\n\n{outro}。"
        return content

