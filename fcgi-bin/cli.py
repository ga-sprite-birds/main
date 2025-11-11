"""
GA Sprite Birds - CLI 命令行模式
直接从命令行生成音频，无需启动 API 服务

版本: v1.0
开发团队: Tiger
"""

import asyncio
import argparse
import importlib
from pathlib import Path
from typing import Optional

from loguru import logger

import config

# 动态导入核心模块（根据 config.CORE_DIR）
_core_module_name = config.CORE_DIR.replace('-', '_')  # 将连字符转为下划线（Python 模块名规范）
_utils_module = importlib.import_module(f'{_core_module_name}.Utils')
_parser_module = importlib.import_module(f'{_core_module_name}.Parser')
_llm_module = importlib.import_module(f'{_core_module_name}.LLM')
_audio_module = importlib.import_module(f'{_core_module_name}.Audio')

# 导入需要的类和函数
read_text_file = _utils_module.read_text_file
extract_pdf_text = _utils_module.extract_pdf_text
ChapterParser = _parser_module.ChapterParser
LLMManager = _llm_module.LLMManager
TTSManager = _audio_module.TTSManager
AudioExporter = _audio_module.AudioExporter


def get_unique_filename(path: Path) -> Path:
    """
    如果文件已存在，生成唯一的文件名（类似 Windows 重命名方式）

    Args:
        path: 原始文件路径

    Returns:
        唯一的文件路径
    """
    if not path.exists():
        return path

    # 分离文件名和扩展名
    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    # 尝试添加 (1), (2), (3) ...
    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


async def generate_from_file(
    input_file: str,
    output_dir: Optional[str] = None,
    voice: Optional[str] = None,
    rate: Optional[float] = None,
    enable_llm: Optional[bool] = None,
    start_chapter: int = 1,
    end_chapter: Optional[int] = None
):
    """
    从文件生成音频

    Args:
        input_file: 输入文件路径
        output_dir: 输出目录（可选）
        voice: 音色（可选）
        rate: 语速（可选，0.5-2.0）
        enable_llm: 是否启用 LLM 口语化
        start_chapter: 起始章节（从1开始）
        end_chapter: 结束章节（可选，None表示到最后）
    """
    # 检查输入文件
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_file}")
        return

    # 如果命令行没有指定 enable_llm，使用配置文件的值
    if enable_llm is None:
        enable_llm = config.ENABLE_LLM

    logger.info(f"输入文件: {input_file}")
    logger.info(f"LLM 模式: {config.LLM_MODE}")
    logger.info(f"TTS 模式: {config.TTS_MODE}")
    logger.info(f"启用 LLM: {enable_llm}")
    logger.info("")

    # 读取文件内容
    logger.info("正在读取文件...")
    file_ext = input_path.suffix.lower()
    if file_ext == ".pdf":
        text = extract_pdf_text(str(input_path))
    else:
        text = read_text_file(str(input_path))

    logger.info(f"文件大小: {len(text)} 字符")

    # 文本预处理
    if config.TEXT_PREPROCESSING_ENABLED:
        logger.info("正在进行文本预处理...")
        from ga_birds.Utils.file_utils import preprocess_text
        text = preprocess_text(
            text,
            remove_extra_newlines=True,
            remove_headers_footers=True,
            fix_pdf_linebreaks=True
        )

    # 章节拆分
    logger.info("正在解析章节...")
    parser = ChapterParser(
        regex_patterns=config.CHAPTER_REGEX_PATTERNS,
        min_length=config.CHAPTER_MIN_LENGTH,
        keep_title=config.CHAPTER_KEEP_TITLE
    )
    chapters = parser.parse(text)
    logger.info(f"共解析出 {len(chapters)} 个章节")
    logger.info("")
    
    # 确定要处理的章节范围
    if end_chapter is None:
        end_chapter = len(chapters)
    
    # 验证章节范围
    if start_chapter < 1 or start_chapter > len(chapters):
        logger.error(f"起始章节 {start_chapter} 超出范围 (1-{len(chapters)})")
        return
    
    if end_chapter < start_chapter or end_chapter > len(chapters):
        logger.error(f"结束章节 {end_chapter} 超出范围 ({start_chapter}-{len(chapters)})")
        return
    
    logger.info(f"将处理章节: {start_chapter} - {end_chapter}")
    logger.info("")
    
    # 初始化管理器
    llm_manager = None
    if enable_llm:
        try:
            logger.info("正在初始化 LLM 管理器...")
            llm_manager = LLMManager()
            logger.info(f"✓ LLM 管理器初始化成功")
        except Exception as e:
            logger.error(f"✗ LLM 初始化失败: {e}")
            logger.warning("将跳过 LLM 处理")
            import traceback
            logger.debug(traceback.format_exc())

    logger.info("正在初始化 TTS 管理器...")
    tts_manager = TTSManager()

    logger.info("正在初始化音频导出器...")
    audio_exporter = AudioExporter()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("开始生成音频")
    logger.info("=" * 60)
    logger.info("")
    
    # 生成音频
    success_count = 0
    failed_count = 0
    
    for chapter in chapters:
        # 检查是否在处理范围内
        if chapter.index < start_chapter or chapter.index > end_chapter:
            continue
        
        logger.info(f"[{chapter.index}/{len(chapters)}] {chapter.title}")
        logger.info(f"内容长度: {len(chapter.content)} 字符")
        
        try:
            # 保存原始内容用于对比
            original_content = chapter.content
            original_length = len(original_content)

            # 当前处理的内容
            content = original_content
            colloquialized_content = None

            # LLM 口语化（可选）
            if enable_llm:
                if llm_manager:
                    logger.info("  → LLM 口语化中...")
                    logger.debug(f"  → 原文长度: {original_length} 字符")
                    logger.debug(f"  → 原文前100字: {content[:100]}...")
                    try:
                        colloquialized_content = llm_manager.colloquialize_text(content)
                        colloquialized_length = len(colloquialized_content)
                        logger.debug(f"  → LLM 返回长度: {colloquialized_length} 字符")
                        logger.debug(f"  → LLM 返回前100字: {colloquialized_content[:100]}...")

                        # 检查 LLM 是否真的改变了文本
                        if colloquialized_content != content:
                            content = colloquialized_content
                            logger.info(f"  ✓ LLM 处理完成（{original_length} → {colloquialized_length} 字符）")
                        else:
                            logger.warning(f"  ⚠ LLM 返回文本与原文相同")
                            logger.warning(f"  → 仍会保存 LLM 输出用于调试")
                            # 不设为 None，保留 LLM 输出用于调试

                    except Exception as e:
                        logger.error(f"  ✗ LLM 处理失败: {e}")
                        logger.warning(f"  → 使用原始文本")
                        import traceback
                        logger.debug(traceback.format_exc())
                        colloquialized_content = None
                else:
                    logger.warning("  ⚠ LLM 管理器未初始化，跳过 LLM 处理")
                    logger.debug(f"  → enable_llm={enable_llm}, llm_manager={llm_manager}")

            # 添加片头片尾（如果启用）
            final_content = content
            if config.CHAPTER_INTRO_OUTRO:
                # 片头
                intro = config.CHAPTER_INTRO_TEMPLATE.format(
                    index=chapter.index,
                    title=chapter.title
                )

                # 片尾
                outro = config.CHAPTER_OUTRO_TEMPLATE

                # 组合内容（直接添加，不加停顿）
                # Edge TTS 不支持 SSML，停顿只能通过标点符号自然产生
                final_content = f"{intro}。\n\n{content}\n\n{outro}。"

            # 生成音频文件路径
            audio_path = audio_exporter.get_output_path(
                index=chapter.index,
                title=chapter.title,
                role="default",
                custom_base_path=output_dir
            )

            # 确保输出目录存在
            audio_path.parent.mkdir(parents=True, exist_ok=True)

            # 处理文件已存在的情况
            if audio_path.exists():
                if config.OUTPUT_DUPLICATE_HANDLING == "skip":
                    logger.info(f"  ⊙ 文件已存在，跳过: {audio_path}")
                    logger.info("")
                    continue
                elif config.OUTPUT_DUPLICATE_HANDLING == "rename":
                    audio_path = get_unique_filename(audio_path)
                    logger.info(f"  ⚠ 文件已存在，重命名为: {audio_path.name}")
                # overwrite 模式不需要特殊处理

            # 保存章节文本（如果启用）
            if config.OUTPUT_SAVE_CHAPTER_TEXT:
                # 保存最终文本（包含片头片尾）
                text_path = audio_path.with_suffix('.txt')
                try:
                    with open(
                        text_path,
                        'w',
                        encoding=config.OUTPUT_CHAPTER_TEXT_ENCODING
                    ) as f:
                        f.write(final_content)
                    logger.info(f"  ✓ 章节文本已保存: {text_path.name}")
                except Exception as e:
                    logger.warning(f"  ⚠ 保存章节文本失败: {e}")

                # 如果启用了 LLM，额外保存原文和 LLM 处理后的文本
                if enable_llm and colloquialized_content:
                    # 保存原文
                    original_text_path = audio_path.with_name(
                        audio_path.stem + '-原文.txt'
                    )
                    try:
                        with open(
                            original_text_path,
                            'w',
                            encoding=config.OUTPUT_CHAPTER_TEXT_ENCODING
                        ) as f:
                            f.write(original_content)
                        logger.info(f"  ✓ 原文已保存: {original_text_path.name}")
                    except Exception as e:
                        logger.warning(f"  ⚠ 保存原文失败: {e}")

                    # 保存 LLM 处理后的文本
                    llm_text_path = audio_path.with_name(
                        audio_path.stem + '-LLM.txt'
                    )
                    try:
                        with open(
                            llm_text_path,
                            'w',
                            encoding=config.OUTPUT_CHAPTER_TEXT_ENCODING
                        ) as f:
                            f.write(colloquialized_content)
                        logger.info(f"  ✓ LLM文本已保存: {llm_text_path.name}")
                    except Exception as e:
                        logger.warning(f"  ⚠ 保存LLM文本失败: {e}")

            # TTS 生成音频
            logger.info(f"  → TTS 生成中...")

            # 准备 TTS 参数
            tts_kwargs = {
                "text": final_content,
                "output_path": str(audio_path),
                "voice": voice
            }

            # 如果指定了语速，添加到参数中
            if rate is not None:
                tts_kwargs["rate"] = rate

            await tts_manager.generate_audio(**tts_kwargs)

            logger.info(f"  ✓ 生成完成: {audio_path}")
            logger.info("")
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ 生成失败: {e}")
            logger.info("")
            failed_count += 1
    
    # 总结
    logger.info("=" * 60)
    logger.info("生成完成")
    logger.info("=" * 60)
    logger.info(f"成功: {success_count} 章")
    logger.info(f"失败: {failed_count} 章")
    logger.info(f"总计: {success_count + failed_count} 章")


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="GA Sprite Birds - 音频朗读系统 CLI 模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用（使用 .env 配置）
  python cli.py -i debug/择天记_修复.txt
  
  # 指定输出目录
  python cli.py -i debug/择天记_修复.txt -o ./output/择天记
  
  # 指定音色（男声）
  python cli.py -i debug/择天记_修复.txt --voice zh-CN-YunxiNeural
  
  # 禁用 LLM 处理
  python cli.py -i debug/择天记_修复.txt --no-llm
  
  # 只生成第1-10章
  python cli.py -i debug/择天记_修复.txt --start 1 --end 10
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="输入文件路径（支持 .txt, .pdf）"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="输出目录（默认使用 config.yaml 中的配置）"
    )
    
    parser.add_argument(
        "--voice",
        help="音色（覆盖配置文件，如: zh-CN-YunxiNeural）"
    )

    parser.add_argument(
        "--rate",
        type=float,
        help="语速（0.5-2.0，1.0为正常，默认使用配置文件）"
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="禁用 LLM 口语化处理"
    )
    
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="起始章节（从1开始，默认: 1）"
    )
    
    parser.add_argument(
        "--end",
        type=int,
        help="结束章节（默认: 最后一章）"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别（默认: INFO）"
    )
    
    args = parser.parse_args()

    # 配置日志
    logger.remove()

    if config.LOG_CONSOLE:
        logger.add(
            lambda msg: print(msg, end=""),
            level=args.log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
        )

    if config.LOG_FILE:
        from pathlib import Path
        log_path = Path(config.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            config.LOG_FILE,
            rotation=f"{config.LOG_MAX_FILE_SIZE} MB",
            retention=config.LOG_BACKUP_COUNT,
            level=args.log_level,
            format=config.LOG_FORMAT
        )
    
    # 运行生成任务
    # 如果指定了 --no-llm，则禁用 LLM；否则使用配置文件的值
    enable_llm_arg = False if args.no_llm else None

    asyncio.run(generate_from_file(
        input_file=args.input,
        output_dir=args.output,
        voice=args.voice,
        rate=args.rate,
        enable_llm=enable_llm_arg,
        start_chapter=args.start,
        end_chapter=args.end
    ))


if __name__ == "__main__":
    main()

