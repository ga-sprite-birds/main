"""
GA Sprite Birds - Chapter text saver
Unified text saving logic for single-character and multi-character voice modes

Version: v1.0
Dev team: Tiger
"""

from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger

from .config_manager import ConfigManager


class ChapterTextSaver:
    """Chapter text saver"""

    @staticmethod
    def save_single_voice_text(
        audio_path: Path,
        final_content: str,
        original_content: Optional[str] = None,
        llm_content: Optional[str] = None,
        enable_llm: bool = False
    ) -> None:
        """
        Save text for single-character voice mode

        Args:
            audio_path: audio file path
            final_content: final text (including intro/outro)
            original_content: original text
            llm_content: text processed by the LLM
            enable_llm: whether LLM is enabled
        """
        if not ConfigManager.is_save_chapter_text_enabled():
            return

        encoding = ConfigManager.get_chapter_text_encoding()

        # Save the final text
        text_path = audio_path.with_suffix('.txt')
        try:
            with open(text_path, 'w', encoding=encoding) as f:
                f.write(final_content)
            logger.info(f"  ✓ 章节文本已保存: {text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存章节文本失败: {e}")

        # If LLM is enabled, also save the original and LLM texts
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
        Save text for multi-character voice mode

        Args:
            audio_path: audio file path
            segments: dialogue segment list [{"text": "...", "speaker": "..."}]
            original_content: original text
            llm_content: text processed by the LLM
            enable_llm: whether LLM is enabled
        """
        if not ConfigManager.is_save_chapter_text_enabled():
            return

        encoding = ConfigManager.get_chapter_text_encoding()

        # 1. Save text with speaker labels
        text_path = audio_path.with_suffix('.txt')
        try:
            with open(text_path, 'w', encoding=encoding) as f:
                for segment in segments:
                    speaker = segment.get('speaker', 'narrator')
                    text = segment.get('text', '')
                    # Format: 【speaker】text content
                    f.write(f"【{speaker}】{text}\n\n")
            logger.info(f"  ✓ 章节文本已保存（带说话人）: {text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存章节文本失败: {e}")

        # 2. Save a plain-text version (without speaker labels)
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

        # 3. If LLM is enabled, also save the original and LLM texts
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
        Save LLM-related text files

        Args:
            audio_path: audio file path
            original_content: original text
            llm_content: text processed by the LLM
            encoding: file encoding
        """
        # Save the original text
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

        # Save the LLM text
        llm_text_path = audio_path.with_name(
            audio_path.stem + '-LLM.txt'
        )
        try:
            with open(llm_text_path, 'w', encoding=encoding) as f:
                f.write(llm_content)
            logger.info(f"  ✓ LLM文本已保存: {llm_text_path.name}")
        except Exception as e:
            logger.warning(f"  ⚠ 保存LLM文本失败: {e}")

