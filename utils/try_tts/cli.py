#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge TTS 配音试听工具 - 命令行接口
获取可用音色列表并生成试听音频
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.try_tts.voice_fetcher import VoiceFetcher
from utils.try_tts.sample_generator import SampleGenerator
from utils.try_tts.doc_exporter import DocExporter


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Edge TTS 配音试听工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 列出所有音色
  python utils/try_tts/cli.py list
  
  # 列出中文音色
  python utils/try_tts/cli.py list --language zh-CN
  
  # 列出中文男声
  python utils/try_tts/cli.py list --language zh-CN --gender male
  
  # 生成所有中文音色的试听音频
  python utils/try_tts/cli.py generate --language zh-CN
  
  # 生成指定音色的试听音频
  python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural
  
  # 导出音色列表为文档
  python utils/try_tts/cli.py list --language zh-CN --save-doc voices.md
        """
    )
    
    parser.add_argument(
        'action',
        choices=['list', 'generate'],
        help='操作类型: list(列出音色), generate(生成试听音频)'
    )
    
    parser.add_argument(
        '--language',
        help='语言代码（如 zh-CN, en-US），默认全部'
    )
    
    parser.add_argument(
        '--gender',
        choices=['male', 'female', '1', '0'],
        help='性别筛选: male/1(男), female/0(女)，默认全部'
    )
    
    parser.add_argument(
        '--voice',
        help='指定音色名称（仅用于 generate 操作）'
    )
    
    parser.add_argument(
        '--text',
        help='试听文本（默认使用内置文本）'
    )
    
    parser.add_argument(
        '--output',
        default='./output/tts_samples',
        help='输出目录（默认 ./output/tts_samples）'
    )
    
    parser.add_argument(
        '--save-doc',
        metavar='FILE',
        help='保存音色列表为 Markdown 文档'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    print("=" * 100)
    print("Edge TTS 配音试听工具")
    print("=" * 100)
    
    fetcher = VoiceFetcher()
    
    print("\n📡 正在获取音色列表...")
    fetcher.get_voices_sync()
    print(f"✓ 获取成功，共 {len(fetcher.voices)} 个音色")
    
    language_display = args.language or "全部"
    gender_display = args.gender or "全部"
    
    filtered_voices = fetcher.filter_voices(
        language=args.language,
        gender=args.gender
    )
    
    if args.action == 'list':
        print(f"\n📋 筛选条件: 语言={language_display}, 性别={gender_display}")
        print()
        print(VoiceFetcher.format_voice_list(filtered_voices))
        
        if args.save_doc:
            print(f"\n💾 正在保存文档...")
            doc_path = DocExporter.export_to_markdown(
                filtered_voices,
                args.save_doc,
                language=language_display,
                gender=gender_display
            )
            print(f"✓ 文档已保存: {doc_path}")
    
    elif args.action == 'generate':
        if args.voice:
            print(f"\n🎵 生成单个音色试听: {args.voice}")
            generator = SampleGenerator(args.output)
            output_file = generator.generate_sample_sync(args.voice, args.text)
            print(f"✓ 试听音频已生成: {output_file}")
        else:
            if not filtered_voices:
                print("\n❌ 错误: 未找到匹配的音色")
                sys.exit(1)

            print(f"\n🎵 批量生成试听音频")
            print(f"   筛选条件: 语言={language_display}, 性别={gender_display}")
            print(f"   音色数量: {len(filtered_voices)}")
            print(f"   输出目录: {args.output}")
            print()

            generator = SampleGenerator(args.output)
            result = generator.generate_batch_sync(
                filtered_voices,
                args.text,
                show_progress=True,
                language=language_display,
                gender=gender_display
            )

            print()
            print(f"✓ 批量生成完成")
            print(f"  状态: {result['msg']}")
            print(f"  成功: {result['data']['success']} 个")
            print(f"  失败: {result['data']['failed']} 个")
            print(f"✓ 输出目录: {args.output}")
            print(f"✓ 结果已保存: {args.output}/voices.json, {args.output}/voices.md")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()

