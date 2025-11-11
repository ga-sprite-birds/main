#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令生成器 - 生成重试命令（Shell脚本或纯文本）
"""

from typing import List, Tuple
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config


class CommandGenerator:
    """命令生成器"""
    
    def __init__(self, failed_chapters: List[int], batch_size: int = 20, input_file: str = None):
        """
        初始化命令生成器
        
        Args:
            failed_chapters: 失败章节序号列表
            batch_size: 每批次章节数
            input_file: 输入文件路径
        """
        self.failed_chapters = failed_chapters
        self.batch_size = batch_size
        self.input_file = input_file or 'debug/ga.pdf'
    
    def generate_batches(self) -> List[Tuple[int, int]]:
        """
        将失败章节分组为批次
        
        Returns:
            批次列表，每个批次为 (start, end) 元组
        """
        if not self.failed_chapters:
            return []
        
        batches = []
        chapters = sorted(self.failed_chapters)
        
        i = 0
        while i < len(chapters):
            start = chapters[i]
            
            # 查找连续的章节范围
            end = start
            count = 1
            
            while count < self.batch_size and i + count < len(chapters):
                next_chapter = chapters[i + count]
                # 如果章节连续或间隔不大，继续合并
                if next_chapter - end <= 3:
                    end = next_chapter
                    count += 1
                else:
                    break
            
            batches.append((start, end))
            i += count
        
        return batches
    
    def generate_shell_script(self, batches: List[Tuple[int, int]]) -> str:
        """
        生成 Shell 脚本
        
        Args:
            batches: 批次列表
        
        Returns:
            Shell 脚本内容
        """
        lines = [
            "#!/bin/bash",
            "# 自动生成的重试脚本",
            f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 失败章节总数: {len(self.failed_chapters)}",
            f"# 批次总数: {len(batches)}",
            "",
            "echo '开始重试失败章节...'",
            "echo ''",
            ""
        ]
        
        for i, (start, end) in enumerate(batches, 1):
            count = end - start + 1
            lines.extend([
                f"# 批次{i}：第{start}-{end}章（{count}章）",
                f"echo '执行批次 {i}/{len(batches)}...'",
                f"bash cli.sh -i {self.input_file} --start {start} --end {end}",
                "if [ $? -ne 0 ]; then",
                f"    echo '❌ 批次{i}失败，是否继续？(y/n)'",
                "    read -r response",
                "    if [ \"$response\" != \"y\" ]; then",
                "        echo '用户取消执行'",
                "        exit 1",
                "    fi",
                "fi",
                "echo ''",
                ""
            ])
        
        lines.extend([
            "echo '✅ 所有批次执行完成！'",
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_text(self, batches: List[Tuple[int, int]]) -> str:
        """
        生成纯文本命令列表
        
        Args:
            batches: 批次列表
        
        Returns:
            纯文本内容
        """
        lines = [
            "失败章节重试命令列表",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"失败章节总数: {len(self.failed_chapters)}",
            f"批次总数: {len(batches)}",
            "",
            "=" * 60,
            ""
        ]
        
        for i, (start, end) in enumerate(batches, 1):
            count = end - start + 1
            lines.extend([
                f"批次{i}：第{start}-{end}章（{count}章）",
                f"bash cli.sh -i {self.input_file} --start {start} --end {end}",
                ""
            ])
        
        lines.extend([
            "=" * 60,
            "",
            "使用说明:",
            "1. 复制上述命令到终端执行",
            "2. 或者保存为 .sh 文件后执行: bash retry.sh",
            "3. 建议每次执行一个批次，观察结果后再继续",
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_summary(self, batches: List[Tuple[int, int]]) -> str:
        """
        生成摘要信息
        
        Args:
            batches: 批次列表
        
        Returns:
            摘要文本
        """
        lines = [
            "📊 分析结果:",
            f"   - 失败章节总数: {len(self.failed_chapters)}",
            f"   - 批次总数: {len(batches)}",
            f"   - 输入文件: {self.input_file}",
            "",
            "📋 批次列表:"
        ]
        
        for i, (start, end) in enumerate(batches, 1):
            count = end - start + 1
            lines.append(f"   {i}. 第{start}-{end}章（{count}章）")
        
        return "\n".join(lines)

