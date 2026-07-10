#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command executor - directly executes retry commands
"""

import subprocess
import sys
from typing import List, Tuple
from pathlib import Path


class CommandExecutor:
    """Command executor"""
    
    def __init__(self, batches: List[Tuple[int, int]], input_file: str):
        """
        Initialize the command executor
        
        Args:
            batches: list of batches
            input_file: path to the input file
        """
        self.batches = batches
        self.input_file = input_file
        self.project_root = Path(__file__).parent.parent.parent
    
    def execute(self):
        """Execute all batches"""
        print("\n" + "=" * 60)
        print("⚠️  直接执行模式")
        print("=" * 60)
        print(f"\n📊 即将执行:")
        print(f"   - 批次总数: {len(self.batches)}")
        print(f"   - 输入文件: {self.input_file}")
        print("\n📋 批次列表:")
        
        for i, (start, end) in enumerate(self.batches, 1):
            count = end - start + 1
            print(f"   {i}. 第{start}-{end}章（{count}章）")
        
        print("\n⚠️  警告: 将直接执行重试，无法撤销！")
        response = input("是否继续？(yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("❌ 用户取消执行")
            return
        
        print("\n" + "=" * 60)
        print("开始执行批次...")
        print("=" * 60 + "\n")
        
        success_count = 0
        failed_count = 0
        
        for i, (start, end) in enumerate(self.batches, 1):
            count = end - start + 1
            print(f"\n{'='*60}")
            print(f"执行批次 {i}/{len(self.batches)}: 第{start}-{end}章（{count}章）")
            print(f"{'='*60}\n")
            
            cmd = [
                'bash', 'cli.sh',
                '-i', self.input_file,
                '--start', str(start),
                '--end', str(end)
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self.project_root),
                    check=False,
                    capture_output=False
                )
                
                if result.returncode == 0:
                    print(f"\n✅ 批次{i}执行成功")
                    success_count += 1
                else:
                    print(f"\n❌ 批次{i}执行失败（返回码: {result.returncode}）")
                    failed_count += 1
                    
                    response = input("是否继续执行下一批次？(y/n): ").strip().lower()
                    if response not in ['y', 'yes']:
                        print("用户取消执行")
                        break
                        
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断执行")
                break
            except Exception as e:
                print(f"\n❌ 批次{i}执行异常: {e}")
                failed_count += 1
                
                response = input("是否继续执行下一批次？(y/n): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("用户取消执行")
                    break
        
        # Output summary
        print("\n" + "=" * 60)
        print("执行完成")
        print("=" * 60)
        print(f"✅ 成功: {success_count} 批次")
        print(f"❌ 失败: {failed_count} 批次")
        print(f"📊 总计: {len(self.batches)} 批次")
        print("=" * 60 + "\n")

