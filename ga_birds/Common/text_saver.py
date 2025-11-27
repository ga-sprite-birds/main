"""
GA Sprite Birds - 章节文本保存器
统一处理单人配音和多角色配音的文本保存逻辑

版本: v1.0
开发团队: Tiger
"""

from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger

from .config_manager import ConfigManager


class ChapterTextSaver:
    """章节文本保存器"""

    @staticmethod
    def save_single_voice_text(
        audio_path: Path,
        final_content: str,
        original_content: Optional[str] = None,
        llm_content: Optional[str] = None,
        enable_llm: bool = False
    ) -> None:
        """
        保存单人配音模式的文本

        Args:
            audio_path: 音频文件路径
            final_content: 最终文本（包含片头片尾）
            original_content: 原始文本
            llm_content: LLM 处理后的文本
            enable_llm: 是否启用了 LLM
        """
        if not ConfigManager.is_save_chapter_text_enabled():
            return

        encoding = ConfigManager.get_chapter_text_encoding()

        # 保存最终文本
        text_path = audio_path.with_suffix('.txt')
        try:
            with open(text_path, 'w', encoding=encoding) as f:
                f.write(final_content)
            logger.info(f"  ✓ 章节文本已保存: {text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存章节文本失败: {e}")

        # 如果启用了 LLM，额外保存原文和 LLM 文本
        if enable_llm and llm_content:
            ChapterTextSaver._save_llm_texts(
                audio_path, original_content, llm_content, encoding
            )

    @staticmethod
    def save_multi_voice_text(
        audio_path: Path,
        segments: List[Dict],
        original_content: Optional[str] = None,
        llm_content: Optional[str] = None,
        enable_llm: bool = False
    ) -> None:
        """
        保存多角色配音模式的文本

        Args:
            audio_path: 音频文件路径
            segments: 对话片段列表 [{"text": "...", "speaker": "..."}]
            original_content: 原始文本
            llm_content: LLM 处理后的文本
            enable_llm: 是否启用了 LLM
        """
        if not ConfigManager.is_save_chapter_text_enabled():
            return

        encoding = ConfigManager.get_chapter_text_encoding()

        # 1. 保存带说话人标注的文本
        text_path = audio_path.with_suffix('.txt')
        try:
            with open(text_path, 'w', encoding=encoding) as f:
                for segment in segments:
                    speaker = segment.get('speaker', 'narrator')
                    text = segment.get('text', '')
                    # 格式：【说话人】文本内容
                    f.write(f"【{speaker}】{text}\n\n")
            logger.info(f"  ✓ 章节文本已保存（带说话人）: {text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存章节文本失败: {e}")

        # 2. 保存纯文本版本（不带说话人标注）
        plain_text_path = audio_path.with_name(
            audio_path.stem + '-raw.txt'
        )
        try:
            with open(plain_text_path, 'w', encoding=encoding) as f:
                for segment in segments:
                    text = segment.get('text', '')
                    f.write(f"{text}\n\n")
            logger.info(f"  ✓ 章节文本已保存（纯文本）: {plain_text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存纯文本失败: {e}")

        # 3. 如果启用了 LLM，额外保存原文和 LLM 文本
        if enable_llm and llm_content:
            ChapterTextSaver._save_llm_texts(
                audio_path, original_content, llm_content, encoding
            )

    @staticmethod
    def _save_llm_texts(
        audio_path: Path,
        original_content: Optional[str],
        llm_content: str,
        encoding: str
    ) -> None:
        """
        保存 LLM 相关的文本文件

        Args:
            audio_path: 音频文件路径
            original_content: 原始文本
            llm_content: LLM 处理后的文本
            encoding: 文件编码
        """
        # 保存原文
        if original_content:
            original_text_path = audio_path.with_name(
                audio_path.stem + '-原文.txt'
            )
            try:
                with open(original_text_path, 'w', encoding=encoding) as f:
                    f.write(original_content)
                logger.info(f"  ✓ 原文已保存: {original_text_path.name}")
            except Exception as e:
                logger.warning(f"  ⚠ 保存原文失败: {e}")

        # 保存 LLM 文本
        llm_text_path = audio_path.with_name(
            audio_path.stem + '-LLM.txt'
        )
        try:
            with open(llm_text_path, 'w', encoding=encoding) as f:
                f.write(llm_content)
            logger.info(f"  ✓ LLM文本已保存: {llm_text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存LLM文本失败: {e}")

