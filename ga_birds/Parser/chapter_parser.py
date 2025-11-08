"""
GA Sprite Birds - 章节解析器
使用正则表达式识别和拆分章节

版本: v1.0
开发团队: Tiger
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from loguru import logger


@dataclass
class Chapter:
    """章节数据类"""
    index: int  # 章节序号（从 1 开始）
    title: str  # 章节标题
    content: str  # 章节内容
    start_pos: int  # 在原文中的起始位置
    end_pos: int  # 在原文中的结束位置


class ChapterParser:
    """章节解析器"""
    
    def __init__(
        self,
        regex_patterns: Optional[List[str]] = None,
        min_length: int = 100,
        keep_title: bool = True
    ):
        """
        初始化章节解析器
        
        Args:
            regex_patterns: 章节标题正则表达式列表
            min_length: 最小章节长度（避免误识别）
            keep_title: 是否在内容中保留章节标题
        """
        self.regex_patterns = regex_patterns or [
            r'^第[零一二三四五六七八九十百千万0-9]+章',
            r'^Chapter\s+\d+',
            r'^第[零一二三四五六七八九十百千万0-9]+回'
        ]
        self.min_length = min_length
        self.keep_title = keep_title
        
        # 编译正则表达式
        self.compiled_patterns = [
            re.compile(pattern, re.MULTILINE) for pattern in self.regex_patterns
        ]
        
        logger.info(f"章节解析器初始化完成，正则模式数: {len(self.regex_patterns)}")
    
    def parse(self, text: str) -> List[Chapter]:
        """
        解析文本，拆分章节
        
        Args:
            text: 原始文本
            
        Returns:
            章节列表
        """
        # 查找所有章节标题位置
        chapter_positions = []
        
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                # 获取匹配的行
                line_start = text.rfind('\n', 0, match.start()) + 1
                line_end = text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(text)
                
                title = text[line_start:line_end].strip()
                chapter_positions.append((line_start, title))
        
        # 按位置排序并去重
        chapter_positions = sorted(set(chapter_positions), key=lambda x: x[0])
        
        if not chapter_positions:
            logger.warning("未找到章节标题，将整个文本作为单章处理")
            return [Chapter(
                index=1,
                title="全文",
                content=text,
                start_pos=0,
                end_pos=len(text)
            )]
        
        logger.info(f"找到 {len(chapter_positions)} 个章节标题")
        
        # 拆分章节
        chapters = []
        for i, (pos, title) in enumerate(chapter_positions):
            # 确定章节内容范围
            start_pos = pos
            if i + 1 < len(chapter_positions):
                end_pos = chapter_positions[i + 1][0]
            else:
                end_pos = len(text)
            
            # 提取章节内容
            content = text[start_pos:end_pos].strip()
            
            # 如果不保留标题，则去除第一行
            if not self.keep_title:
                first_newline = content.find('\n')
                if first_newline != -1:
                    content = content[first_newline + 1:].strip()
            
            # 检查章节长度
            if len(content) < self.min_length:
                logger.warning(f"章节 '{title}' 长度过短 ({len(content)} 字符)，跳过")
                continue
            
            chapter = Chapter(
                index=len(chapters) + 1,
                title=title,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos
            )
            chapters.append(chapter)
            
            logger.debug(f"解析章节 {chapter.index}: {title} ({len(content)} 字符)")
        
        logger.info(f"章节解析完成，共 {len(chapters)} 章")
        return chapters
    
    def get_chapter_by_index(self, chapters: List[Chapter], index: int) -> Optional[Chapter]:
        """
        根据序号获取章节
        
        Args:
            chapters: 章节列表
            index: 章节序号（从 1 开始）
            
        Returns:
            章节对象，如果不存在则返回 None
        """
        for chapter in chapters:
            if chapter.index == index:
                return chapter
        return None

