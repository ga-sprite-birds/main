"""
感叹词映射器
将纯标点符号转换为可发音的感叹词，避免 TTS 生成失败

版本: v1.0
开发团队: Tiger
"""

import re
from typing import Dict
from loguru import logger


class InterjectionMapper:
    """感叹词映射器 - 将标点符号转换为可发音的感叹词"""
    
    # 标点符号到感叹词的映射字典
    PUNCTUATION_MAP: Dict[str, str] = {
        # 省略号系列（拉长音效果）
        "……": "嗯......",
        "...": "额......",
        "。。。": "那个......",
        "、、、": "这个......",

        # 问号系列（疑问拉长音）
        "？": "啊？",
        "??": "啊......？",
        "？？": "啊......？",
        "???": "啊......？",
        "？？？": "啊......？",

        # 感叹号系列（感叹拉长音）
        "！": "哎！",
        "!!": "哎......！",
        "！！": "哎......！",
        "!!!": "哎......！",
        "！！！": "哎......！",

        # 混合标点
        "？！": "啊......！",
        "！？": "哎......？",
        "?!": "啊......！",
        "!?": "哎......？",

        # 破折号（拉长停顿）
        "——": "嗯......",
        "--": "嗯......",
        "—": "嗯......",

        # 逗号系列（短停顿）
        "，，": "嗯...嗯...",
        ",,": "嗯...嗯...",

        # 句号系列（短停顿）
        "。": "嗯。",
        ".": "嗯。",
        "。。": "嗯...嗯...",
        "..": "嗯...嗯...",
    }
    
    @classmethod
    def convert_punctuation_to_interjection(cls, text: str) -> tuple[str, bool]:
        """
        将纯标点文本转换为感叹词
        
        Args:
            text: 原始文本
            
        Returns:
            (转换后的文本, 是否进行了转换)
        """
        if not text:
            return text, False
        
        # 移除两端的引号
        stripped_text = text.strip()
        quotes = ['"', '"', '"', "'", ''', ''', '「', '」', '『', '』', '《', '》']
        
        # 记录原始引号
        leading_quotes = ""
        trailing_quotes = ""
        
        # 移除前导引号
        while stripped_text and any(stripped_text.startswith(q) for q in quotes):
            for q in quotes:
                if stripped_text.startswith(q):
                    leading_quotes += q
                    stripped_text = stripped_text[len(q):]
                    break
        
        # 移除尾部引号
        while stripped_text and any(stripped_text.endswith(q) for q in quotes):
            for q in quotes:
                if stripped_text.endswith(q):
                    trailing_quotes = q + trailing_quotes
                    stripped_text = stripped_text[:-len(q)]
                    break
        
        # 去除空白
        stripped_text = stripped_text.strip()
        
        # 检查是否只包含标点符号
        text_without_punctuation = re.sub(
            r'[，。！？；：、,.!?;:\s…—\-\.\*]+', 
            '', 
            stripped_text
        )
        
        # 如果不是纯标点，直接返回原文
        if text_without_punctuation:
            return text, False
        
        # 是纯标点，尝试映射
        interjection = cls.PUNCTUATION_MAP.get(stripped_text)
        
        # 如果没有精确匹配，尝试模糊匹配
        if not interjection:
            # 检查是否包含省略号（拉长音效果）
            if '…' in stripped_text or '.' in stripped_text:
                interjection = "嗯......"
            # 检查是否包含问号（疑问拉长音）
            elif '？' in stripped_text or '?' in stripped_text:
                interjection = "啊......？"
            # 检查是否包含感叹号（感叹拉长音）
            elif '！' in stripped_text or '!' in stripped_text:
                interjection = "哎......！"
            # 默认使用拉长音"嗯"
            else:
                interjection = "嗯......"
        
        # 保留原始引号
        converted_text = f"{leading_quotes}{interjection}{trailing_quotes}"
        
        logger.debug(f"标点转换: {repr(text)} → {repr(converted_text)}")
        
        return converted_text, True
    
    @classmethod
    def process_text_for_tts(cls, text: str) -> str:
        """
        处理文本用于 TTS 生成
        如果是纯标点，转换为感叹词；否则返回原文
        
        Args:
            text: 原始文本
            
        Returns:
            处理后的文本
        """
        converted_text, was_converted = cls.convert_punctuation_to_interjection(text)
        return converted_text

