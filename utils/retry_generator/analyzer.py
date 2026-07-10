#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log analyzer - analyzes TTS generation logs and detects failed chapters
"""

import re
from typing import List, Dict, Set
from pathlib import Path


class LogAnalyzer:
    """Log analyzer"""
    
    def __init__(self, log_file: str):
        """
        Initialize the log analyzer
        
        Args:
            log_file: path to the log file
        """
        self.log_file = Path(log_file)
        
        # Error pattern matching
        self.error_patterns = {
            'network': r'Cannot connect to host|getaddrinfo failed|Connection refused',
            'timeout': r'timeout|timed out',
            'tts_failed': r'TTS 生成失败|✗ 生成失败',
        }
        
        # Pattern for extracting chapter numbers
        self.chapter_pattern = r'\[(\d+)/\d+\]'
    
    def analyze(self, error_filter: str = 'all') -> List[int]:
        """
        Analyze the log file and extract failed chapters
        
        Args:
            error_filter: error type filter ('network', 'timeout', 'all')
        
        Returns:
            list of failed chapter numbers (sorted and deduplicated)
        """
        failed_chapters: Set[int] = set()
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            # Check whether the line contains an error message
            if not self._is_error_line(line, error_filter):
                continue
            
            # Look backward for chapter info (usually in the lines before the error)
            chapter_num = self._find_chapter_number(lines, i)
            if chapter_num:
                failed_chapters.add(chapter_num)
        
        return sorted(list(failed_chapters))
    
    def _is_error_line(self, line: str, error_filter: str) -> bool:
        """
        Determine whether a line is an error line
        
        Args:
            line: a log line
            error_filter: error type filter
        
        Returns:
            whether the line is an error line
        """
        if error_filter == 'all':
            # Check all error patterns
            for pattern in self.error_patterns.values():
                if re.search(pattern, line, re.IGNORECASE):
                    return True
            return False
        else:
            # Check a specific error pattern
            pattern = self.error_patterns.get(error_filter, '')
            return bool(re.search(pattern, line, re.IGNORECASE))
    
    def _find_chapter_number(self, lines: List[str], error_index: int) -> int:
        """
        Look backward from the error line for the chapter number
        
        Args:
            lines: all log lines
            error_index: index of the error line
        
        Returns:
            chapter number, or None if not found
        """
        # Look backward at most 10 lines
        start = max(0, error_index - 10)
        
        for i in range(error_index, start - 1, -1):
            match = re.search(self.chapter_pattern, lines[i])
            if match:
                return int(match.group(1))
        
        return None
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get log statistics
        
        Returns:
            statistics dictionary
        """
        stats = {
            'total_chapters': 0,
            'success_chapters': 0,
            'failed_chapters': 0,
        }
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract summary information
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

