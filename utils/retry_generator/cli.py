#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失败章节重试生成器 - 命令行接口
分析 TTS 生成日志，自动识别失败章节，生成重试命令
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.retry_generator.analyzer import LogAnalyzer
from utils.retry_generator.generator import CommandGenerator
from utils.retry_generator.executor import CommandExecutor


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='失败章节重试生成器 - 分析日志并生成重试命令',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成 Shell 脚本
  python utils/retry_generator/cli.py logs/app.log sh output/retry.sh
  
  # 生成纯文本
  python utils/retry_generator/cli.py logs/app.log txt output/retry.txt
  
  # 直接执行重试
  python utils/retry_generator/cli.py logs/app.log exec
  
可选参数:
  --batch-size 20          每批次章节数（默认20）
  --input debug/ga.pdf     输入文件路径（默认从日志推断）
  --filter network         仅包含特定错误类型
        """
    )
    
    parser.add_argument('log_file', help='日志文件路径')
    parser.add_argument('output_type', choices=['sh', 'txt', 'exec'], 
                       help='输出类型: sh(Shell脚本), txt(纯文本), exec(直接执行)')
    parser.add_argument('output_path', nargs='?', default=None,
                       help='输出文件路径（exec模式可省略）')
    
    parser.add_argument('--batch-size', type=int, default=20,
                       help='每批次章节数（默认20）')
    parser.add_argument('--input', default='debug/ga.pdf',
                       help='输入文件路径（默认 debug/ga.pdf）')
    parser.add_argument('--filter', choices=['network', 'timeout', 'all'], default='all',
                       help='错误类型过滤（默认 all）')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 验证参数
    if args.output_type in ['sh', 'txt'] and not args.output_path:
        print(f"❌ 错误: {args.output_type} 模式需要指定输出路径")
        sys.exit(1)
    
    if not os.path.exists(args.log_file):
        print(f"❌ 错误: 日志文件不存在: {args.log_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("失败章节重试生成器")
    print("=" * 60)
    
    # 分析日志
    print(f"\n📖 正在分析日志: {args.log_file}")
    analyzer = LogAnalyzer(args.log_file)
    failed_chapters = analyzer.analyze(error_filter=args.filter)
    
    if not failed_chapters:
        print("✅ 没有发现失败的章节！")
        return
    
    print(f"📊 分析完成:")
    print(f"   - 失败章节总数: {len(failed_chapters)}")
    print(f"   - 章节范围: {failed_chapters[0]} - {failed_chapters[-1]}")
    
    # 生成命令
    generator = CommandGenerator(
        failed_chapters=failed_chapters,
        batch_size=args.batch_size,
        input_file=args.input
    )
    
    batches = generator.generate_batches()
    print(f"   - 批次总数: {len(batches)}")
    
    # 根据输出类型处理
    if args.output_type == 'sh':
        output = generator.generate_shell_script(batches)
        with open(args.output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n✅ Shell 脚本已生成: {args.output_path}")
        print(f"   执行方式: bash {args.output_path}")
        
    elif args.output_type == 'txt':
        output = generator.generate_text(batches)
        with open(args.output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n✅ 文本文件已生成: {args.output_path}")
        
    elif args.output_type == 'exec':
        executor = CommandExecutor(batches, args.input)
        executor.execute()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

