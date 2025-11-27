"""
GA Sprite Birds - 章节处理器
处理片头片尾等公共逻辑（单角色/多角色通用）

版本: v1.0
开发团队: Tiger
"""

from typing import Tuple, Optional
from loguru import logger

from .config_manager import ConfigManager


class ChapterProcessor:
    """章节处理器 - 处理片头片尾逻辑（公共基础设施）"""

    @staticmethod
    def prepare_intro_outro(
        chapter_index: int,
        chapter_title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        准备片头片尾文本

        Args:
            chapter_index: 章节序号
            chapter_title: 章节标题

        Returns:
            (intro, outro) 元组，如果未启用则返回 (None, None)
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
        组合内容和片头片尾（单人配音模式）

        Args:
            content: 正文内容
            intro: 片头文本
            outro: 片尾文本

        Returns:
            组合后的完整文本
        """
        if intro and outro:
            return f"{intro}。\n\n{content}\n\n{outro}。"
        return content

