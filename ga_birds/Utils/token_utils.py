"""
Token counting and text segmentation utilities

Provides unified token counting and smart text segmentation,
supporting both API and Ollama modes.
"""

import re
from typing import List, Tuple
from loguru import logger
from ga_birds.Common.i18n import t

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning(t("token.tiktoken_not_installed"))


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Unified token counting method

    Args:
        text: text to count
        model: model name (used to select the encoder)

    Returns:
        token count

    Notes:
        - API mode: uses the encoder for the corresponding model
        - Ollama mode: uses the generic encoder (cl100k_base) as an approximation
        - If tiktoken is not installed: Chinese is estimated at 1.5x the character count
    """
    if not TIKTOKEN_AVAILABLE:
        # Fallback: estimate (Chinese character ≈ 1.5 tokens)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    try:
        # Try to get the encoder for the model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Model does not exist, use the generic encoder (works for most modern LLMs)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def split_text_by_sentences(text: str) -> List[str]:
    """
    Split text by sentence

    Supports punctuation such as Chinese periods, question marks, and exclamation marks

    Args:
        text: text to split

    Returns:
        sentence list
    """
    # Chinese sentence delimiters
    sentence_endings = r'[。！？!?;；]'

    # Split sentences, keeping the delimiters
    sentences = re.split(f'({sentence_endings})', text)

    # Merge sentences and delimiters
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        if sentence.strip():
            result.append(sentence)
    
    # Handle the last sentence (if there is no delimiter)
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1])
    
    return result


def split_text_by_paragraphs(text: str) -> List[str]:
    """
    Split text by paragraph

    Args:
        text: text to split

    Returns:
        paragraph list
    """
    # Split by double newline
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def merge_segments_smart(segments: List[str], max_tokens: int, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    Smart-merge small paragraphs to avoid over-segmentation

    Args:
        segments: paragraph list
        max_tokens: max tokens per segment
        model: model name

    Returns:
        merged paragraph list
    """
    if not segments:
        return []

    merged = []
    current_segment = segments[0]
    current_tokens = count_tokens(current_segment, model)

    for segment in segments[1:]:
        segment_tokens = count_tokens(segment, model)

        # Merge if it stays within the limit after merging
        if current_tokens + segment_tokens <= max_tokens:
            current_segment += "\n" + segment
            current_tokens += segment_tokens
        else:
            # Otherwise save the current segment and start a new one
            merged.append(current_segment)
            current_segment = segment
            current_tokens = segment_tokens

    # Add the last segment
    if current_segment:
        merged.append(current_segment)

    return merged


def split_text_smart(text: str, max_tokens: int, model: str = "gpt-3.5-turbo", overlap_ratio: float = 0.1) -> List[str]:
    """
    Smart segmentation: split by paragraph/sentence boundaries, preserving semantic integrity

    Strategy:
    1. Prefer splitting by paragraph (\n\n)
    2. If a paragraph is too long, split by sentence
    3. If a sentence is too long, force split by token
    4. Keep some overlap to avoid losing context

    Args:
        text: text to split
        max_tokens: max tokens per segment
        model: model name
        overlap_ratio: overlap ratio (0-1), default 0.1 (10%)

    Returns:
        segmented text list
    """
    total_tokens = count_tokens(text, model)

    # Return directly if within the limit
    if total_tokens <= max_tokens:
        return [text]

    logger.debug(t("token.text_needs_splitting", total=total_tokens, max=max_tokens))

    # Step 1: split by paragraph
    paragraphs = split_text_by_paragraphs(text)
    logger.debug(t("token.split_by_paragraph", count=len(paragraphs)))

    # Step 2: merge small paragraphs
    segments = merge_segments_smart(paragraphs, max_tokens, model)
    logger.debug(t("token.merged_segments", count=len(segments)))

    # Step 3: check for over-long paragraphs needing further splitting
    final_segments = []
    for segment in segments:
        segment_tokens = count_tokens(segment, model)

        if segment_tokens <= max_tokens:
            final_segments.append(segment)
        else:
            # Paragraph too long, split by sentence
            logger.debug(t("token.paragraph_too_long", tokens=segment_tokens))
            sentences = split_text_by_sentences(segment)
            sub_segments = merge_segments_smart(sentences, max_tokens, model)

            # Check for remaining over-long sentences
            for sub_segment in sub_segments:
                sub_tokens = count_tokens(sub_segment, model)
                if sub_tokens <= max_tokens:
                    final_segments.append(sub_segment)
                else:
                    # Sentence too long, force split by token
                    logger.warning(t("token.sentence_too_long", tokens=sub_tokens))
                    final_segments.extend(_force_split_by_tokens(sub_segment, max_tokens, model))

    # Step 4: add overlap (optional)
    if overlap_ratio > 0 and len(final_segments) > 1:
        final_segments = _add_overlap(final_segments, overlap_ratio, max_tokens, model)

    logger.info(t("token.split_complete", count=len(final_segments)))
    return final_segments


def _force_split_by_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    Force split text by token count (last resort)

    Args:
        text: text to split
        max_tokens: max tokens per segment
        model: model name

    Returns:
        segmented text list
    """
    if not TIKTOKEN_AVAILABLE:
        # Fallback: split by character count
        chars_per_segment = int(max_tokens / 1.5)  # estimate
        segments = []
        for i in range(0, len(text), chars_per_segment):
            segments.append(text[i:i + chars_per_segment])
        return segments
    
    # Use tiktoken for precise splitting
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = encoding.encode(text)
    segments = []
    
    for i in range(0, len(tokens), max_tokens):
        segment_tokens = tokens[i:i + max_tokens]
        segment_text = encoding.decode(segment_tokens)
        segments.append(segment_text)
    
    return segments


def _add_overlap(segments: List[str], overlap_ratio: float, max_tokens: int, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    Add overlap between paragraphs to keep context coherent

    Args:
        segments: paragraph list
        overlap_ratio: overlap ratio
        max_tokens: max tokens per segment
        model: model name

    Returns:
        paragraph list with overlap added
    """
    if len(segments) <= 1:
        return segments

    overlap_tokens = int(max_tokens * overlap_ratio)
    result = [segments[0]]

    for i in range(1, len(segments)):
        prev_segment = segments[i - 1]
        current_segment = segments[i]

        # Take the last few sentences from the previous segment as overlap
        prev_sentences = split_text_by_sentences(prev_segment)
        overlap_text = ""
        overlap_token_count = 0

        for sentence in reversed(prev_sentences):
            sentence_tokens = count_tokens(sentence, model)
            if overlap_token_count + sentence_tokens <= overlap_tokens:
                overlap_text = sentence + overlap_text
                overlap_token_count += sentence_tokens
            else:
                break

        # Add the overlap
        if overlap_text:
            current_segment = overlap_text + current_segment

        result.append(current_segment)

    return result


def estimate_processing_time(text: str, tokens_per_second: float = 50) -> float:
    """
    Estimate LLM processing time

    Args:
        text: text
        tokens_per_second: tokens processed per second (default 50)

    Returns:
        estimated time (seconds)
    """
    tokens = count_tokens(text)
    return tokens / tokens_per_second

