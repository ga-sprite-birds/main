"""
GA Sprite Birds - 章节处理器
处理片头片尾、文本组合等公共逻辑

版本: v1.0
开发团队: Tiger
"""

from typing import Tuple, Optional, List, Dict
from loguru import logger

from .config_manager import ConfigManager


class ChapterProcessor:
    """章节处理器 - 处理片头片尾逻辑"""

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

    @staticmethod
    def add_intro_outro_to_segments(
        segments: List[Dict],
        intro: Optional[str],
        outro: Optional[str]
    ) -> List[Dict]:
        """
        为对话片段添加片头片尾（多角色配音模式）

        Args:
            segments: 对话片段列表
            intro: 片头文本
            outro: 片尾文本

        Returns:
            添加片头片尾后的片段列表
        """
        if not intro or not outro:
            logger.debug("  → 未添加片头片尾（intro 或 outro 为空）")
            return segments

        original_count = len(segments)
        enhanced_segments = []

        # 片头使用旁白
        enhanced_segments.append({
            "text": f"{intro}。",
            "speaker": "narrator",
        })

        # 正文对话
        enhanced_segments.extend(segments)

        # 片尾使用旁白
        enhanced_segments.append({
            "text": f"{outro}。",
            "speaker": "narrator",
        })

        logger.debug(f"  → 片段总数（添加前）: {original_count}")
        logger.debug(f"  → 片段总数（添加后）: {len(enhanced_segments)}")
        logger.debug(f"  → 第一个片段: {enhanced_segments[0]}")
        logger.debug(f"  → 最后一个片段: {enhanced_segments[-1]}")

        return enhanced_segments

