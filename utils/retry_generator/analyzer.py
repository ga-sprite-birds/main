#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志分析器 - 分析 TTS 生成日志，识别失败章节
"""

import re
from typing import List, Dict, Set
from pathlib import Path


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_file: str):
        """
        初始化日志分析器
        
        Args:
            log_file: 日志文件路径
        """
        self.log_file = Path(log_file)
        
        # 错误模式匹配
        self.error_patterns = {
            'network': r'Cannot connect to host|getaddrinfo failed|Connection refused',
            'timeout': r'timeout|timed out',
            'tts_failed': r'TTS 生成失败|✗ 生成失败',
        }
        
        # 章节序号提取模式
        self.chapter_pattern = r'\[(\d+)/\d+\]'
    
    def analyze(self, error_filter: str = 'all') -> List[int]:
        """
        分析日志文件，提取失败章节
        
        Args:
            error_filter: 错误类型过滤 ('network', 'timeout', 'all')
        
        Returns:
            失败章节序号列表（已排序去重）
        """
        failed_chapters: Set[int] = set()
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            # 检查是否包含错误信息
            if not self._is_error_line(line, error_filter):
                continue
            
            # 向前查找章节信息（通常在错误前几行）
            chapter_num = self._find_chapter_number(lines, i)
            if chapter_num:
                failed_chapters.add(chapter_num)
        
        return sorted(list(failed_chapters))
    
    def _is_error_line(self, line: str, error_filter: str) -> bool:
        """
        判断是否为错误行
        
        Args:
            line: 日志行
            error_filter: 错误类型过滤
        
        Returns:
            是否为错误行
        """
        if error_filter == 'all':
            # 检查所有错误模式
            for pattern in self.error_patterns.values():
                if re.search(pattern, line, re.IGNORECASE):
                    return True
            return False
        else:
            # 检查特定错误模式
            pattern = self.error_patterns.get(error_filter, '')
            return bool(re.search(pattern, line, re.IGNORECASE))
    
    def _find_chapter_number(self, lines: List[str], error_index: int) -> int:
        """
        从错误行向前查找章节序号
        
        Args:
            lines: 所有日志行
            error_index: 错误行索引
        
        Returns:
            章节序号，未找到返回 None
        """
        # 向前查找最多 10 行
        start = max(0, error_index - 10)
        
        for i in range(error_index, start - 1, -1):
            match = re.search(self.chapter_pattern, lines[i])
            if match:
                return int(match.group(1))
        
        return None
    
    def get_statistics(self) -> Dict[str, int]:
        """
        获取日志统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_chapters': 0,
            'success_chapters': 0,
            'failed_chapters': 0,
        }
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取总结信息
        total_match = re.search(r'总计:\s*(\d+)\s*章', content)
        success_match = re.search(r'成功:\s*(\d+)\s*章', content)
        failed_match = re.search(r'失败:\s*(\d+)\s*章', content)
        
        if total_match:
            stats['total_chapters'] = int(total_match.group(1))
        if success_match:
            stats['success_chapters'] = int(success_match.group(1))
        if failed_match:
            stats['failed_chapters'] = int(failed_match.group(1))
        
        return stats

