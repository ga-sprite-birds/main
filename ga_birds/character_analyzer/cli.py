#!/usr/bin/env python3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from ga_birds.Utils.file_utils import extract_pdf_text
from ga_birds.Parser.chapter_parser import ChapterParser
from ga_birds.LLM.manager import LLMManager
from ga_birds.character_analyzer.analyzer import CharacterAnalyzer


def main():
    if len(sys.argv) < 2:
        print("用法: python ga_birds/character_analyzer/cli.py <小说文件> [选项]")
        print("")
        print("选项:")
        print("  --start N        起始章节（默认: 1）")
        print("  --end N          结束章节（默认: 全部）")
        print("  --output PATH    输出文件路径（默认: cache/role/<文件名>_characters.json）")
        print("")
        print("示例:")
        print("  python ga_birds/character_analyzer/cli.py debug/ga.pdf")
        print("  python ga_birds/character_analyzer/cli.py debug/择天记.txt --start 1 --end 10")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"❌ 错误: 文件不存在: {input_file}")
        sys.exit(1)
    
    start_chapter = 1
    end_chapter = None
    output_path = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--start' and i + 1 < len(sys.argv):
            start_chapter = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--end' and i + 1 < len(sys.argv):
            end_chapter = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_path = Path(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    if output_path is None:
        output_dir = Path('cache/role')
        output_path = output_dir / f"{input_file.stem}_characters.json"
    
    print(f"[*] 读取文件: {input_file}")
    
    if input_file.suffix.lower() == '.pdf':
        text = extract_pdf_text(str(input_file))
    else:
        with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    
    print(f"[+] 文件大小: {len(text)} 字符")
    
    print("\n[*] 解析章节...")
    chapter_parser = ChapterParser(
        regex_patterns=config.CHAPTER_REGEX_PATTERNS,
        min_length=config.CHAPTER_MIN_LENGTH,
        keep_title=config.CHAPTER_KEEP_TITLE
    )
    chapters = chapter_parser.parse(text)
    print(f"[+] 总章节数: {len(chapters)}")
    
    if end_chapter is None:
        end_chapter = len(chapters)
    
    if start_chapter < 1 or start_chapter > len(chapters):
        print(f"❌ 错误: 起始章节 {start_chapter} 超出范围 (1-{len(chapters)})")
        sys.exit(1)
    
    if end_chapter < start_chapter or end_chapter > len(chapters):
        print(f"❌ 错误: 结束章节 {end_chapter} 超出范围 ({start_chapter}-{len(chapters)})")
        sys.exit(1)
    
    test_chapters = chapters[start_chapter - 1:end_chapter]
    print(f"\n[*] 分析章节 {start_chapter}-{end_chapter}（共 {len(test_chapters)} 章）")
    
    print("\n[*] 初始化 LLM...")
    llm_manager = LLMManager()
    
    print("[*] 开始分析角色...")
    analyzer = CharacterAnalyzer(llm_manager)
    
    for chapter in test_chapters:
        print(f"\n[*] 分析章节 {chapter.index}: {chapter.title}")
        
        characters = analyzer.analyze_chapter(chapter.content, chapter.index)
        
        if characters:
            print(f"  - 识别到 {len(characters)} 个角色: {', '.join([c['name'] for c in characters])}")
            analyzer.merge_characters(characters, chapter.index)
        else:
            print(f"  - 未识别到角色")
    
    print(f"\n[*] 保存角色数据...")
    analyzer.save_to_json(output_path, input_file.stem, input_file.stem)
    
    print(f"\n[+] 完成！")
    print(f"\n角色统计:")
    print(f"  - 总角色数: {len(analyzer.all_characters)}")
    
    all_chars = analyzer.get_all_characters()
    for char in all_chars[:10]:
        print(f"  - {char['name']}: 出现 {char['appearance_count']} 次（章节 {char['first_chapter']}-{char['last_chapter']}）")
    
    if len(all_chars) > 10:
        print(f"  ... 还有 {len(all_chars) - 10} 个角色")


if __name__ == "__main__":
    main()

