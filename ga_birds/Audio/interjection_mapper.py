"""
Interjection mapper
Converts pure punctuation into pronounceable interjections to avoid TTS generation failures

Version: v1.0
Dev team: Tiger
"""

import re
from typing import Dict
from loguru import logger


class InterjectionMapper:
    """Interjection mapper - converts punctuation into pronounceable interjections"""

    # Mapping dictionary from punctuation to interjections
    PUNCTUATION_MAP: Dict[str, str] = {
        # Ellipsis series (prolonged sound effect)
        "……": "嗯......",
        "...": "额......",
        "。。。": "那个......",
        "、、、": "这个......",

        # Question mark series (prolonged interrogative sound)
        "？": "啊？",
        "??": "啊......？",
        "？？": "啊......？",
        "???": "啊......？",
        "？？？": "啊......？",

        # Exclamation mark series (prolonged exclamatory sound)
        "！": "哎！",
        "!!": "哎......！",
        "！！": "哎......！",
        "!!!": "哎......！",
        "！！！": "哎......！",

        # Mixed punctuation
        "？！": "啊......！",
        "！？": "哎......？",
        "?!": "啊......！",
        "!?": "哎......？",

        # Em dash (prolonged pause)
        "——": "嗯......",
        "--": "嗯......",
        "—": "嗯......",

        # Comma series (short pause)
        "，，": "嗯...嗯...",
        ",,": "嗯...嗯...",

        # Period series (short pause)
        "。": "嗯。",
        ".": "嗯。",
        "。。": "嗯...嗯...",
        "..": "嗯...嗯...",
    }
    
    @classmethod
    def convert_punctuation_to_interjection(cls, text: str) -> tuple[str, bool]:
        """
        Convert pure-punctuation text into an interjection

        Args:
            text: original text

        Returns:
            (converted text, whether a conversion was performed)
        """
        if not text:
            return text, False

        # Remove quotes at both ends
        stripped_text = text.strip()
        quotes = ['"', '"', '"', "'", ''', ''', '「', '」', '『', '』', '《', '》']

        # Record original quotes
        leading_quotes = ""
        trailing_quotes = ""

        # Remove leading quotes
        while stripped_text and any(stripped_text.startswith(q) for q in quotes):
            for q in quotes:
                if stripped_text.startswith(q):
                    leading_quotes += q
                    stripped_text = stripped_text[len(q):]
                    break

        # Remove trailing quotes
        while stripped_text and any(stripped_text.endswith(q) for q in quotes):
            for q in quotes:
                if stripped_text.endswith(q):
                    trailing_quotes = q + trailing_quotes
                    stripped_text = stripped_text[:-len(q)]
                    break

        # Remove whitespace
        stripped_text = stripped_text.strip()

        # Check whether it contains only punctuation
        text_without_punctuation = re.sub(
            r'[，。！？；：、,.!?;:\s…—\-\.\*]+',
            '',
            stripped_text
        )

        # If not pure punctuation, return the original text directly
        if text_without_punctuation:
            return text, False

        # It is pure punctuation; try to map it
        interjection = cls.PUNCTUATION_MAP.get(stripped_text)

        # If no exact match, try fuzzy matching
        if not interjection:
            # Check whether it contains an ellipsis (prolonged sound effect)
            if '…' in stripped_text or '.' in stripped_text:
                interjection = "嗯......"
            # Check whether it contains a question mark (prolonged interrogative sound)
            elif '？' in stripped_text or '?' in stripped_text:
                interjection = "啊......？"
            # Check whether it contains an exclamation mark (prolonged exclamatory sound)
            elif '！' in stripped_text or '!' in stripped_text:
                interjection = "哎......！"
            # Default to the prolonged sound "嗯"
            else:
                interjection = "嗯......"

        # Preserve original quotes
        converted_text = f"{leading_quotes}{interjection}{trailing_quotes}"

        logger.debug(f"Punctuation conversion: {repr(text)} → {repr(converted_text)}")

        return converted_text, True

    @classmethod
    def process_text_for_tts(cls, text: str) -> str:
        """
        Process text for TTS generation
        If it is pure punctuation, convert it to an interjection; otherwise return the original

        Args:
            text: original text

        Returns:
            processed text
        """
        converted_text, was_converted = cls.convert_punctuation_to_interjection(text)
        return converted_text

