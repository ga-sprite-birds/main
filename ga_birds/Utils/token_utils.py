"""
Token 计数和文本分段工具

提供统一的 token 计数和智能文本分段功能，
支持 API 和 Ollama 模式。
"""

import re
from typing import List, Tuple
from loguru import logger

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken 未安装，将使用字符数估算 token（不够精确）")


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    统一的 token 计数方法
    
    Args:
        text: 要计数的文本
        model: 模型名称（用于选择编码器）
    
    Returns:
        token 数量
    
    注意：
        - API 模式：使用对应模型的编码
        - Ollama 模式：使用通用编码（cl100k_base）作为近似
        - 如果 tiktoken 未安装：中文按 1.5 倍字符数估算
    """
    if not TIKTOKEN_AVAILABLE:
        # 降级方案：估算（中文字符 ≈ 1.5 tokens）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    try:
        # 尝试获取模型对应的编码器
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # 模型不存在，使用通用编码（适用于大多数现代 LLM）
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def split_text_by_sentences(text: str) -> List[str]:
    """
    按句子分割文本
    
    支持中文句号、问号、感叹号等标点
    
    Args:
        text: 要分割的文本
    
    Returns:
        句子列表
    """
    # 中文句子分隔符
    sentence_endings = r'[。！？!?;；]'
    
    # 分割句子，保留分隔符
    sentences = re.split(f'({sentence_endings})', text)
    
    # 合并句子和分隔符
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        if sentence.strip():
            result.append(sentence)
    
    # 处理最后一个句子（如果没有分隔符）
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1])
    
    return result


def split_text_by_paragraphs(text: str) -> List[str]:
    """
    按段落分割文本
    
    Args:
        text: 要分割的文本
    
    Returns:
        段落列表
    """
    # 按双换行符分割
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def merge_segments_smart(segments: List[str], max_tokens: int, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    智能合并小段落，避免过度分割
    
    Args:
        segments: 段落列表
        max_tokens: 每段最大 token 数
        model: 模型名称
    
    Returns:
        合并后的段落列表
    """
    if not segments:
        return []
    
    merged = []
    current_segment = segments[0]
    current_tokens = count_tokens(current_segment, model)
    
    for segment in segments[1:]:
        segment_tokens = count_tokens(segment, model)
        
        # 如果合并后不超过限制，则合并
        if current_tokens + segment_tokens <= max_tokens:
            current_segment += "\n" + segment
            current_tokens += segment_tokens
        else:
            # 否则保存当前段，开始新段
            merged.append(current_segment)
            current_segment = segment
            current_tokens = segment_tokens
    
    # 添加最后一段
    if current_segment:
        merged.append(current_segment)
    
    return merged


def split_text_smart(text: str, max_tokens: int, model: str = "gpt-3.5-turbo", overlap_ratio: float = 0.1) -> List[str]:
    """
    智能分段：按段落/句子边界分割，保持语义完整
    
    策略：
    1. 优先按段落分割（\n\n）
    2. 如果段落过长，按句子分割
    3. 如果句子过长，强制按 token 分割
    4. 保留一定重叠，避免上下文丢失
    
    Args:
        text: 要分割的文本
        max_tokens: 每段最大 token 数
        model: 模型名称
        overlap_ratio: 重叠比例（0-1），默认 0.1（10%）
    
    Returns:
        分段后的文本列表
    """
    total_tokens = count_tokens(text, model)
    
    # 如果不超过限制，直接返回
    if total_tokens <= max_tokens:
        return [text]
    
    logger.debug(f"文本需要分段：总 tokens={total_tokens}, 限制={max_tokens}")
    
    # 步骤 1：按段落分割
    paragraphs = split_text_by_paragraphs(text)
    logger.debug(f"按段落分割：共 {len(paragraphs)} 段")
    
    # 步骤 2：合并小段落
    segments = merge_segments_smart(paragraphs, max_tokens, model)
    logger.debug(f"合并后：共 {len(segments)} 段")
    
    # 步骤 3：检查是否有超长段落，需要进一步分割
    final_segments = []
    for segment in segments:
        segment_tokens = count_tokens(segment, model)
        
        if segment_tokens <= max_tokens:
            final_segments.append(segment)
        else:
            # 段落过长，按句子分割
            logger.debug(f"段落过长（{segment_tokens} tokens），按句子分割")
            sentences = split_text_by_sentences(segment)
            sub_segments = merge_segments_smart(sentences, max_tokens, model)
            
            # 检查是否还有超长句子
            for sub_segment in sub_segments:
                sub_tokens = count_tokens(sub_segment, model)
                if sub_tokens <= max_tokens:
                    final_segments.append(sub_segment)
                else:
                    # 句子过长，强制按 token 分割
                    logger.warning(f"句子过长（{sub_tokens} tokens），强制分割")
                    final_segments.extend(_force_split_by_tokens(sub_segment, max_tokens, model))
    
    # 步骤 4：添加重叠（可选）
    if overlap_ratio > 0 and len(final_segments) > 1:
        final_segments = _add_overlap(final_segments, overlap_ratio, max_tokens, model)
    
    logger.info(f"✓ 文本分段完成：{len(final_segments)} 段")
    return final_segments


def _force_split_by_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    强制按 token 数分割文本（最后的手段）
    
    Args:
        text: 要分割的文本
        max_tokens: 每段最大 token 数
        model: 模型名称
    
    Returns:
        分段后的文本列表
    """
    if not TIKTOKEN_AVAILABLE:
        # 降级方案：按字符数分割
        chars_per_segment = int(max_tokens / 1.5)  # 估算
        segments = []
        for i in range(0, len(text), chars_per_segment):
            segments.append(text[i:i + chars_per_segment])
        return segments
    
    # 使用 tiktoken 精确分割
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
    在段落之间添加重叠，保持上下文连贯性
    
    Args:
        segments: 段落列表
        overlap_ratio: 重叠比例
        max_tokens: 每段最大 token 数
        model: 模型名称
    
    Returns:
        添加重叠后的段落列表
    """
    if len(segments) <= 1:
        return segments
    
    overlap_tokens = int(max_tokens * overlap_ratio)
    result = [segments[0]]
    
    for i in range(1, len(segments)):
        prev_segment = segments[i - 1]
        current_segment = segments[i]
        
        # 从前一段取最后几句作为重叠
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
        
        # 添加重叠
        if overlap_text:
            current_segment = overlap_text + current_segment
        
        result.append(current_segment)
    
    return result


def estimate_processing_time(text: str, tokens_per_second: float = 50) -> float:
    """
    估算 LLM 处理时间
    
    Args:
        text: 文本
        tokens_per_second: 每秒处理的 token 数（默认 50）
    
    Returns:
        预估时间（秒）
    """
    tokens = count_tokens(text)
    return tokens / tokens_per_second

