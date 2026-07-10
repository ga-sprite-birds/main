"""
Dialogue parser
Uses an LLM to identify the speaker of each sentence in a chapter (for multi-character voice casting)
"""

import re
import json
from typing import List, Dict, Optional
from loguru import logger

import config
from ga_birds.Common.i18n import t
from .segment_utils import SegmentUtils


class DialogueParser:
    """Dialogue parser (multi-character voice casting module)"""

    # Chunk size (in characters), using the configured value
    CHUNK_SIZE = config.DIALOGUE_CHUNK_SIZE
    # Chunk overlap (in characters), to keep context coherent
    CHUNK_OVERLAP = config.DIALOGUE_CHUNK_OVERLAP

    def __init__(self, llm_manager, characters: List[Dict]):
        """
        Initialize the dialogue parser

        Args:
            llm_manager: LLM manager
            characters: character list (loaded from the character template)
        """
        self.llm_manager = llm_manager
        self.characters = characters
        self.fallback_language = (
            SegmentUtils.extract_language_from_locale(config.TTS_VOICE) or "en"
        )

        # Build the character name list (including aliases)
        self.character_names = set()
        for char in characters:
            self.character_names.add(char['name'])
            for alias in char.get('aliases', []):
                self.character_names.add(alias)

        logger.info(t("character.analyzer_initialized", count=len(characters)))

    @staticmethod
    def add_intro_outro_to_segments(
        segments: List[Dict],
        intro: Optional[str],
        outro: Optional[str]
    ) -> List[Dict]:
        """
        Add intro and outro to dialogue segments (for multi-character voice casting)

        Args:
            segments: dialogue segment list
            intro: intro text
            outro: outro text

        Returns:
            segment list with intro and outro added
        """
        if not intro or not outro:
            logger.debug(t("character.analyzer_no_intro"))
            return segments

        original_count = len(segments)
        enhanced_segments = []
        intro_text = f"{intro}。"
        outro_text = f"{outro}。"

        # Intro/outro are personal config text; mark them so TTS uses TTS_VOICE
        # instead of the content-language narrator voice.
        enhanced_segments.append({
            "text": intro_text,
            "speaker": "narrator",
            "segment_type": "intro",
            "language": SegmentUtils.detect_language(intro_text, fallback_language="en"),
            "emotion": "neutral",
            "tone": "narration",
            "tts_params": SegmentUtils.normalize_tts_params({}, emotion="neutral", tone="narration"),
            "voice_override": "",
        })

        # Main dialogue
        enhanced_segments.extend(segments)

        enhanced_segments.append({
            "text": outro_text,
            "speaker": "narrator",
            "segment_type": "outro",
            "language": SegmentUtils.detect_language(outro_text, fallback_language="en"),
            "emotion": "neutral",
            "tone": "narration",
            "tts_params": SegmentUtils.normalize_tts_params({}, emotion="neutral", tone="narration"),
            "voice_override": "",
        })

        logger.debug(t("character.analyzer_before_count", count=original_count))
        logger.debug(t("character.analyzer_after_count", count=len(enhanced_segments)))
        logger.debug(t("character.analyzer_first_segment", segment=enhanced_segments[0]))
        logger.debug(t("character.analyzer_last_segment", segment=enhanced_segments[-1]))

        return enhanced_segments
    
    def parse_chapter(self, chapter_content: str, chapter_index: int) -> List[Dict]:
        """
        Parse chapter content and identify the speaker of each sentence

        Args:
            chapter_content: chapter content
            chapter_index: chapter index

        Returns:
            dialogue segment list, format:
            [
                {"text": "二叔走了过来，说：", "speaker": "narrator"},
                {"text": "你去哪里？", "speaker": "二叔"},
                ...
            ]
        """
        content_length = len(chapter_content)
        logger.debug(t("character.chapter_content_length", index=chapter_index, length=content_length))

        # If the content is short, parse directly
        if content_length <= self.CHUNK_SIZE:
            return self._parse_chunk(chapter_content, chapter_index, 1, 1)

        # Long chapters need to be split into chunks
        chunks = self._split_into_chunks(chapter_content)
        logger.info(t("character.chapter_split_into_chunks", count=len(chunks)))

        all_segments = []
        for i, chunk in enumerate(chunks):
            chunk_num = i + 1
            logger.debug(t("character.processing_chunk", current=chunk_num, total=len(chunks)))
            segments = self._parse_chunk(chunk, chapter_index, chunk_num, len(chunks))
            all_segments.extend(segments)

        logger.info(t("character.parsed_segments", count=len(all_segments), chunks=len(chunks)))
        return all_segments

    def _split_into_chunks(self, content: str) -> List[str]:
        """
        Split long content into multiple chunks

        Args:
            content: original content

        Returns:
            list of content chunks
        """
        chunks = []
        start = 0
        content_length = len(content)

        while start < content_length:
            end = start + self.CHUNK_SIZE

            # If not the last chunk, try to split at a paragraph boundary
            if end < content_length:
                # Look for a paragraph boundary near the split point (newline)
                search_start = max(start + self.CHUNK_SIZE - 200, start)
                search_end = min(start + self.CHUNK_SIZE + 200, content_length)
                search_range = content[search_start:search_end]

                # Find the nearest paragraph boundary
                last_newline = search_range.rfind('\n')
                if last_newline != -1:
                    end = search_start + last_newline + 1

            chunk = content[start:end]
            chunks.append(chunk)

            # Starting position of the next chunk (with overlap)
            start = end - self.CHUNK_OVERLAP if end < content_length else end

        return chunks

    def _parse_chunk(
        self,
        chunk_content: str,
        chapter_index: int,
        chunk_num: int,
        total_chunks: int
    ) -> List[Dict]:
        """
        Parse a single content chunk

        Args:
            chunk_content: content chunk
            chapter_index: chapter index
            chunk_num: current chunk number
            total_chunks: total number of chunks

        Returns:
            dialogue segment list
        """
        # Build the character name string
        character_names_str = "、".join([c['name'] for c in self.characters])

        prompt = f"""请分析以下小说章节，将内容拆分为对话片段，并识别每个片段的说话人。

已知角色：{character_names_str}

要求：
1. 将内容拆分为多个片段（对话、旁白、描述等）
2. 识别每个片段的说话人（角色名或 "narrator" 表示旁白）
3. 为每个片段标注主语言 language，使用简短语言码，如 en / zh / ja / de / fr / es / pt / it
4. 为每个片段标注情绪 emotion，只能从 neutral / calm / happy / excited / sad / angry / nervous / serious 中选择
5. 为每个片段标注语气 tone，只能从 narration / dialogue / gentle / firm / whisper / shout / sarcastic 中选择
6. 为每个片段提供温和的 TTS 建议参数 tts_params：
   - rate: 0.80 - 1.25
   - pitch: -8 - 8
   - volume: 0.85 - 1.15
7. 保持原文内容完整，不要修改文字
8. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{chunk_content}

返回格式（必须是有效的 JSON）：
{{
  "segments": [
    {{
      "text": "二叔走了过来，说：",
      "speaker": "narrator",
      "segment_type": "narration",
      "language": "zh",
      "emotion": "neutral",
      "tone": "narration",
      "tts_params": {{"rate": 1.0, "pitch": 0, "volume": 1.0}}
    }},
    {{
      "text": "你去哪里？",
      "speaker": "二叔",
      "segment_type": "dialogue",
      "language": "zh",
      "emotion": "serious",
      "tone": "firm",
      "tts_params": {{"rate": 1.02, "pitch": -1, "volume": 1.02}}
    }},
    {{
      "text": "老爸回答：",
      "speaker": "narrator",
      "segment_type": "narration",
      "language": "zh",
      "emotion": "neutral",
      "tone": "narration",
      "tts_params": {{"rate": 1.0, "pitch": 0, "volume": 1.0}}
    }},
    {{
      "text": "我去买菜。",
      "speaker": "老爸",
      "segment_type": "dialogue",
      "language": "zh",
      "emotion": "calm",
      "tone": "dialogue",
      "tts_params": {{"rate": 0.96, "pitch": 0, "volume": 1.0}}
    }},
    {{
      "text": "他们一起离开了。",
      "speaker": "narrator",
      "segment_type": "narration",
      "language": "zh",
      "emotion": "neutral",
      "tone": "narration",
      "tts_params": {{"rate": 1.0, "pitch": 0, "volume": 1.0}}
    }}
  ]
}}"""

        chunk_desc = f"章节{chapter_index}"
        if total_chunks > 1:
            chunk_desc += f"-块{chunk_num}/{total_chunks}"

        # Dialogue parsing with segment metadata needs more output space.
        input_len = len(chunk_content)
        dialogue_max_tokens = max(4096, input_len * 2)
        logger.debug(t("character.chunk_input_length", desc=chunk_desc, input=input_len, max_tokens=dialogue_max_tokens))

        try:
            result = self.llm_manager.generate(prompt, max_tokens=dialogue_max_tokens)
            logger.debug(t("character.chunk_llm_result_length", desc=chunk_desc, length=len(result)))

            return self._parse_llm_response(result, chapter_index, chunk_num)

        except Exception as e:
            logger.error(t("character.chunk_parse_failed", desc=chunk_desc, error=e))
            raise

    def _parse_llm_response(
        self,
        result: str,
        chapter_index: int,
        chunk_num: int
    ) -> List[Dict]:
        """
        Parse the JSON response returned by the LLM

        Args:
            result: raw text returned by the LLM
            chapter_index: chapter index
            chunk_num: chunk number

        Returns:
            dialogue segment list
        """
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if not json_match:
            logger.warning(t("character.chunk_format_error", chapter=chapter_index, chunk=chunk_num))
            return []

        json_str = json_match.group(0)

        # Clean the JSON
        json_str = self._clean_json_string(json_str)

        try:
            data = self._parse_json_with_fix(json_str, chapter_index, chunk_num)
            segments = [
                self._normalize_segment(segment)
                for segment in data.get('segments', [])
                if isinstance(segment, dict) and str(segment.get("text", "")).strip()
            ]
            return segments

        except json.JSONDecodeError as e:
            logger.error(t("character.chunk_json_parse_failed", chapter=chapter_index, chunk=chunk_num, error=e))
            self._save_debug_info(result, json_str, e, chapter_index, chunk_num)
            raise

    def _clean_json_string(self, json_str: str) -> str:
        """Clean the JSON string"""
        # Remove newlines
        json_str = json_str.replace('\n', ' ').replace('\r', '')

        # Fix various quote issues
        json_str = json_str.replace('\u201c', '\\"')  # " left double quote
        json_str = json_str.replace('\u201d', '\\"')  # " right double quote
        json_str = json_str.replace('\u2018', "'")    # ' left single quote
        json_str = json_str.replace('\u2019', "'")    # ' right single quote
        json_str = json_str.replace('\u300c', '\\"')  # 「
        json_str = json_str.replace('\u300d', '\\"')  # 」
        json_str = json_str.replace('\u300e', '\\"')  # 『
        json_str = json_str.replace('\u300f', '\\"')  # 』

        # Fix control characters in the JSON
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)

        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)

        return json_str

    def _parse_json_with_fix(
        self,
        json_str: str,
        chapter_index: int,
        chunk_num: int
    ) -> Dict:
        """Try to parse the JSON, auto-fixing if necessary"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try to auto-complete the ending
            fixed = json_str.rstrip()
            if '"segments"' in fixed and not fixed.endswith(']}'):
                if not fixed.endswith(']'):
                    fixed += ']'
                if not fixed.endswith(']}'):
                    fixed += '}'
                try:
                    data = json.loads(fixed)
                    logger.warning(t("character.chunk_json_auto_fixed", chapter=chapter_index, chunk=chunk_num))
                    return data
                except json.JSONDecodeError:
                    pass
            raise e

    def _save_debug_info(
        self,
        result: str,
        json_str: str,
        error: json.JSONDecodeError,
        chapter_index: int,
        chunk_num: int
    ):
        """Save debug info to a file"""
        debug_file = f"cache/debug_json_chapter_{chapter_index}_chunk_{chunk_num}.txt"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=== 原始 LLM 返回 ===\n")
                f.write(result)
                f.write("\n\n=== 清理后的 JSON ===\n")
                f.write(json_str)
                f.write("\n\n=== 错误位置附近 ===\n")
                start = max(0, error.pos - 200)
                end = min(len(json_str), error.pos + 200)
                f.write(f"...{json_str[start:end]}...")
            logger.error(t("common.save_debug_info", path=debug_file))
        except Exception as write_error:
            logger.error(t("common.save_debug_info_failed", error=write_error))

    def _normalize_segment(self, segment: Dict) -> Dict:
        raw_speaker = str(segment.get("speaker", "narrator")).strip() or "narrator"
        text = str(segment.get("text", ""))
        segment_type = SegmentUtils.normalize_segment_type(segment.get("segment_type"), raw_speaker)

        if config.SEGMENT_ENABLE_LANGUAGE_ANALYSIS:
            language = SegmentUtils.normalize_language_code(
                segment.get("language"),
                fallback=SegmentUtils.detect_language(text, fallback_language=self.fallback_language),
            )
        else:
            language = self.fallback_language

        if config.SEGMENT_ENABLE_EMOTION_ANALYSIS:
            emotion = SegmentUtils.normalize_emotion(segment.get("emotion"))
            tone = SegmentUtils.normalize_tone(segment.get("tone"), segment_type=segment_type)
        else:
            emotion = "neutral"
            tone = "narration" if segment_type == "narration" else "dialogue"

        raw_tts_params = segment.get("tts_params")
        if not isinstance(raw_tts_params, dict):
            raw_tts_params = {
                "rate": segment.get("rate"),
                "pitch": segment.get("pitch"),
                "volume": segment.get("volume"),
            }

        tts_params = SegmentUtils.normalize_tts_params(
            raw_tts_params,
            emotion=emotion,
            tone=tone,
        )

        voice_override = str(segment.get("voice_override", "")).strip()

        return {
            "text": text,
            "speaker": raw_speaker,
            "segment_type": segment_type,
            "language": language,
            "emotion": emotion,
            "tone": tone,
            "tts_params": tts_params,
            "voice_override": voice_override,
        }

    def normalize_speaker(self, speaker: str) -> str:
        """
        Normalize the speaker name (map alias to the primary name)

        Args:
            speaker: speaker name

        Returns:
            normalized name
        """
        if speaker == "narrator":
            return "narrator"

        # Look up the character
        for char in self.characters:
            if speaker == char['name']:
                return char['name']
            if speaker in char.get('aliases', []):
                return char['name']
        
        # Not found, return the original name
        logger.warning(t("character.unknown_speaker", speaker=speaker))
        return "narrator"

