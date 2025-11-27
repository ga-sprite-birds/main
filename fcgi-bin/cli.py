"""
GA Sprite Birds - CLI 命令行模式
直接从命令行生成音频，无需启动 API 服务

版本: v1.0
开发团队: Tiger
"""

import asyncio
import argparse
import importlib
import json
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
_character_module = importlib.import_module(f'{_core_module_name}.character_analyzer')

# 导入需要的类和函数
read_text_file = _utils_module.read_text_file
extract_pdf_text = _utils_module.extract_pdf_text
ParamManager = _utils_module.ParamManager
ChapterParser = _parser_module.ChapterParser
LLMManager = _llm_module.LLMManager
TTSManager = _audio_module.TTSManager
AudioExporter = _audio_module.AudioExporter
AudioMerger = _audio_module.AudioMerger
CharacterAnalyzer = _character_module.CharacterAnalyzer
DialogueParser = _character_module.DialogueParser
VoiceAssigner = _character_module.VoiceAssigner
CharacterListParser = _character_module.CharacterListParser
CharacterMerger = _character_module.CharacterMerger


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
    end_chapter: Optional[int] = None,
    analyze_characters: bool = False,
    multi_voice: Optional[bool] = None,
    character_template: Optional[str] = None,
    character_list: Optional[str] = None,
    analysis_mode: Optional[str] = None
):
    """
    从文件生成音频

    Args:
        input_file: 输入文件路径
        output_dir: 输出目录（可选）
        voice: 音色（可选）
        rate: 语速（可选，0.5-2.0）
        enable_llm: 是否启用 LLM 口语化（None=使用配置文件）
        start_chapter: 起始章节（从1开始）
        end_chapter: 结束章节（可选，None表示到最后）
        analyze_characters: 角色分析模式（生成模板后退出）
        multi_voice: 多角色配音模式（None=使用配置文件）
        character_template: 角色配音模板文件路径（可选）
        character_list: 角色列表文件路径（混合模式，可选）
        analysis_mode: 角色分析模式（None=使用配置文件，auto=智能分析，hybrid=混合模式）
    """
    # 检查输入文件
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_file}")
        return

    # ========== 参数合并：命令行/API 参数 > 配置文件 ==========
    enable_llm = ParamManager.merge_enable_llm(enable_llm)
    multi_voice = ParamManager.merge_multi_voice(multi_voice)

    logger.info(f"输入文件: {input_file}")
    logger.info(f"LLM 模式: {config.LLM_MODE}")
    logger.info(f"TTS 模式: {config.TTS_MODE}")
    logger.info(f"启用 LLM: {enable_llm}")
    logger.info(f"多角色配音: {multi_voice}")
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

    # ========== 角色分析模式 ==========
    if analyze_characters:
        logger.info("")
        logger.info("=" * 60)

        # 判断分析模式（优先级：命令行参数 > character_list > 配置文件）
        if analysis_mode is None:
            # 未指定 --analysis-mode 参数
            if character_list:
                # 有 --character-list 参数，使用混合模式
                analysis_mode = "hybrid"
            else:
                # 使用配置文件的值
                analysis_mode = config.CHARACTER_ANALYSIS_MODE

        # 验证混合模式必须有角色列表文件
        if analysis_mode == "hybrid" and not character_list:
            logger.error("✗ 混合模式需要指定角色列表文件")
            logger.error("请使用 --character-list 参数指定角色列表文件")
            logger.error("")
            logger.error("示例:")
            logger.error("  bash cli.sh -i input.txt --analyze-characters --analysis-mode hybrid --character-list characters.txt")
            logger.error("")
            logger.error("或者使用智能分析模式:")
            logger.error("  bash cli.sh -i input.txt --analyze-characters")
            return

        # 显示分析模式
        if analysis_mode == "hybrid":
            logger.info("角色分析模式：混合模式")
        else:
            logger.info("角色分析模式：智能分析")

        logger.info("=" * 60)
        logger.info("")

        # 初始化 LLM
        logger.info("正在初始化 LLM 管理器...")
        try:
            llm_manager = LLMManager()
            logger.info("✓ LLM 管理器初始化成功")
        except Exception as e:
            logger.error(f"✗ LLM 初始化失败: {e}")
            logger.error("角色分析需要 LLM，无法继续")
            return

        logger.info("")

        # ========== 混合模式：用户指定角色列表 ==========
        if analysis_mode == "hybrid":
            logger.info("读取用户指定的角色列表...")

            # 解析角色列表文件
            user_characters = CharacterListParser.parse_file(character_list)

            if not user_characters:
                logger.error("✗ 角色列表为空或解析失败")
                return

            if not CharacterListParser.validate_characters(user_characters):
                logger.error("✗ 角色列表验证失败")
                return

            logger.info(f"✓ 用户指定了 {len(user_characters)} 个角色:")
            for char in user_characters:
                logger.info(f"  - {char['name']} ({char['gender']})")

            logger.info("")
            logger.info("开始为指定角色分析别名和性格...")

            # 为每个指定角色找别名和性格
            analyzer = CharacterAnalyzer(llm_manager)
            character_names = [char['name'] for char in user_characters]

            # 合并所有章节的分析结果
            character_info = {char['name']: {
                'aliases': set(),
                'personality': set(),
                'appearance_count': 0,
                'first_chapter': None,
                'last_chapter': None
            } for char in user_characters}

            for chapter in chapters:
                if chapter.index < start_chapter or chapter.index > end_chapter:
                    continue

                logger.info(f"分析章节 {chapter.index}: {chapter.title}")
                chapter_data = analyzer.analyze_chapter_for_characters(
                    chapter.content,
                    chapter.index,
                    character_names
                )

                # 合并结果
                for char_name, info in chapter_data.items():
                    if char_name in character_info:
                        # 合并别名
                        character_info[char_name]['aliases'].update(info.get('aliases', []))
                        # 合并性格标签
                        character_info[char_name]['personality'].update(info.get('personality', []))
                        # 更新出现次数
                        character_info[char_name]['appearance_count'] += 1
                        # 更新首次出现章节
                        if character_info[char_name]['first_chapter'] is None:
                            character_info[char_name]['first_chapter'] = chapter.index
                        # 更新最后出现章节
                        character_info[char_name]['last_chapter'] = chapter.index

                        logger.info(f"  → {char_name}: 别名 {list(info.get('aliases', []))}")

            # 转换为最终格式
            all_characters = []
            for char in user_characters:
                char_name = char['name']
                info = character_info[char_name]

                all_characters.append({
                    'name': char_name,
                    'aliases': list(info['aliases']),
                    'gender': char['gender'],
                    'personality': list(info['personality']),
                    'appearance_count': info['appearance_count'],
                    'first_chapter': info['first_chapter'] or 0,
                    'last_chapter': info['last_chapter'] or 0
                })

            logger.info("")
            logger.info("✓ 混合模式分析完成")

        # ========== 智能分析模式：LLM 自动发现角色 ==========
        else:
            logger.info("开始分析角色...")

            # 分析角色
            analyzer = CharacterAnalyzer(llm_manager)

            for chapter in chapters:
                if chapter.index < start_chapter or chapter.index > end_chapter:
                    continue

                logger.info(f"分析章节 {chapter.index}: {chapter.title}")
                characters = analyzer.analyze_chapter(chapter.content, chapter.index)
                if characters:
                    logger.info(f"  → 识别到 {len(characters)} 个角色: {', '.join([c['name'] for c in characters])}")
                    analyzer.merge_characters(characters, chapter.index)
                else:
                    logger.info(f"  → 未识别到角色")

            # 获取所有角色
            all_characters = analyzer.get_all_characters()
            logger.info("")
            logger.info(f"✓ 共识别 {len(all_characters)} 个角色")

            # 自动合并重复角色
            logger.info("")
            logger.info("正在检查并合并重复角色...")
            merger = CharacterMerger(llm_manager)
            all_characters = merger.merge_duplicate_characters(all_characters)

        # 分配音色
        logger.info("")
        logger.info("为角色分配音色...")
        voice_assigner = VoiceAssigner()
        all_characters = voice_assigner.assign_voices(all_characters)

        # 创建角色配音模板
        character_template_data = VoiceAssigner.create_character_template(
            all_characters,
            input_path.stem,
            input_path.stem
        )

        # 保存模板
        template_path = Path(config.CHARACTER_CACHE_DIR) / f"{input_path.stem}_characters.json"
        template_path.parent.mkdir(parents=True, exist_ok=True)

        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(character_template_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 角色配音模板已保存: {template_path}")
        logger.info("")
        logger.info("=" * 60)
        logger.info("角色统计")
        logger.info("=" * 60)
        logger.info(f"总角色数: {len(all_characters)}")
        logger.info("")

        for i, char in enumerate(all_characters[:10], 1):
            logger.info(f"{i}. {char['name']}: {char['voice']} (出现 {char['appearance_count']} 次)")

        if len(all_characters) > 10:
            logger.info(f"... 还有 {len(all_characters) - 10} 个角色")

        logger.info("")
        logger.info(f"旁白音色: {character_template_data['narrator']['voice']}")
        logger.info("")
        logger.info("=" * 60)
        logger.info("下一步")
        logger.info("=" * 60)
        logger.info("您可以编辑模板文件来调整角色音色：")
        logger.info(f"  {template_path}")
        logger.info("")
        logger.info("然后使用以下命令生成多角色配音：")
        logger.info(f"  bash cli.sh -i {input_file} --multi-voice")
        logger.info("")

        # 角色分析完成，退出
        return

    # ========== TTS 生成模式 ==========

    # 初始化管理器
    llm_manager = None
    if enable_llm or multi_voice:
        try:
            logger.info("正在初始化 LLM 管理器...")
            llm_manager = LLMManager()
            logger.info(f"✓ LLM 管理器初始化成功")
        except Exception as e:
            logger.error(f"✗ LLM 初始化失败: {e}")
            if config.ENABLE_MULTI_VOICE:
                logger.error("多角色配音需要 LLM，无法继续")
                return
            logger.warning("将跳过 LLM 处理")
            import traceback
            logger.debug(traceback.format_exc())

    # 多角色配音：加载角色模板
    character_template_data = None
    if multi_voice:
        logger.info("")
        logger.info("=" * 60)
        logger.info("多角色配音模式")
        logger.info("=" * 60)
        logger.info("")

        # 确定模板文件路径
        if character_template is None:
            # 自动查找模板文件
            template_path = Path(config.CHARACTER_CACHE_DIR) / f"{input_path.stem}_characters.json"
            logger.info(f"自动查找角色配音模板: {template_path}")
        else:
            # 使用指定的模板文件
            template_path = Path(character_template)
            logger.info(f"使用指定的角色配音模板: {template_path}")

        # 检查模板文件是否存在
        if not template_path.exists():
            logger.error(f"✗ 角色配音模板文件不存在: {template_path}")
            logger.error("")
            logger.error("请先使用以下命令生成角色配音模板：")
            logger.error(f"  bash cli.sh -i {input_file} --analyze-characters")
            logger.error("")
            return

        # 加载模板文件
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                character_template_data = json.load(f)
            logger.info(f"✓ 已加载 {character_template_data['total_characters']} 个角色")
        except json.JSONDecodeError as e:
            logger.error(f"✗ 角色模板 JSON 格式错误: {e}")
            logger.error(f"✗ 文件路径: {template_path}")
            logger.error("")
            logger.error("请检查 JSON 文件格式，常见问题：")
            logger.error("  1. 多余的逗号（如 ],} 前的逗号）")
            logger.error("  2. 缺少引号或括号")
            logger.error("  3. 编码问题")
            logger.error("")
            logger.error("可以使用以下命令重新生成模板：")
            logger.error(f"  bash cli.sh -i {input_file} --analyze-characters")
            logger.error("")
            return
        except Exception as e:
            logger.error(f"✗ 加载角色模板失败: {e}")
            logger.error(f"✗ 文件路径: {template_path}")
            logger.error("")
            return

        logger.info("")

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
            intro = None
            outro = None
            if config.CHAPTER_INTRO_OUTRO:
                # 片头
                intro = config.CHAPTER_INTRO_TEMPLATE.format(
                    index=chapter.index,
                    title=chapter.title
                )

                # 片尾
                outro = config.CHAPTER_OUTRO_TEMPLATE

                # 组合内容（单人配音模式直接在文本里加入片头片尾）
                # Edge TTS 不支持 SSML，停顿只能通过标点符号自然产生
                final_content = f"{intro}。\n\n{content}\n\n{outro}。"

            # 多角色配音 vs 单人配音
            if multi_voice and character_template_data:
                # 多角色配音模式
                logger.info("  → 使用多角色配音模式")

                # 1. 解析对话（只解析正文，不包含片头片尾）
                dialogue_parser = DialogueParser(llm_manager, character_template_data['characters'])
                # 注意：对话解析只基于正文内容，不包含片头片尾，
                # 避免 LLM 在输出截断时丢失"本章播讲完毕"等提示语
                segments = dialogue_parser.parse_chapter(content, chapter.index)
                logger.info(f"  → 解析到 {len(segments)} 个对话片段（不含片头片尾）")

                # 如果启用了片头片尾，在多角色模式下强制在首尾各添加一个旁白片段，
                # 不依赖 LLM 输出，确保"开始/播讲完毕"等提示一定会被播报。
                if config.CHAPTER_INTRO_OUTRO and intro and outro:
                    enhanced_segments = []
                    # 片头使用旁白
                    enhanced_segments.append({
                        "text": f"{intro}。",
                        "speaker": "narrator",
                    })
                    # 正文对话
                    enhanced_segments.extend(segments)
                    # 片尾使用旁白
                    enhanced_segments.append({
                        "text": f"{outro}。",
                        "speaker": "narrator",
                    })
                    segments = enhanced_segments
                    logger.info(f"  → 已添加片头片尾，对话片段总数: {len(segments)}")

                # 2. 为每个片段生成音频
                temp_audio_files = []
                temp_dir = Path("cache/audio_temp") / f"chapter_{chapter.index}"
                temp_dir.mkdir(parents=True, exist_ok=True)

                for i, segment in enumerate(segments):
                    segment_text = segment['text']
                    speaker = dialogue_parser.normalize_speaker(segment['speaker'])
                    segment_voice = VoiceAssigner.get_voice_for_speaker(speaker, character_template_data)

                    # 生成临时音频文件
                    temp_audio_path = temp_dir / f"segment_{i:03d}.mp3"

                    logger.debug(f"  → 片段 {i+1}/{len(segments)}: {speaker} ({segment_voice})")

                    await tts_manager.generate_audio(
                        text=segment_text,
                        output_path=str(temp_audio_path),
                        voice=segment_voice
                    )

                    temp_audio_files.append(str(temp_audio_path))

                # 3. 合并音频
                audio_path = audio_exporter.get_output_path(
                    index=chapter.index,
                    title=chapter.title,
                    role="multi",
                    custom_base_path=output_dir
                )
                audio_path.parent.mkdir(parents=True, exist_ok=True)

                # 处理文件已存在的情况
                if audio_path.exists():
                    if config.OUTPUT_DUPLICATE_HANDLING == "skip":
                        logger.info(f"  ⊙ 文件已存在，跳过: {audio_path}")
                        logger.info("")
                        # 清理临时文件
                        audio_merger = AudioMerger()
                        audio_merger.cleanup_temp_files(temp_audio_files)
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        continue
                    elif config.OUTPUT_DUPLICATE_HANDLING == "rename":
                        audio_path = get_unique_filename(audio_path)
                        logger.info(f"  ⚠ 文件已存在，重命名为: {audio_path.name}")
                    # overwrite 模式不需要特殊处理

                logger.info(f"  → 合并 {len(temp_audio_files)} 个音频片段...")
                audio_merger = AudioMerger()
                if audio_merger.merge_audio_files(temp_audio_files, str(audio_path)):
                    logger.info(f"  ✓ 音频合并完成")
                    # 清理临时文件
                    audio_merger.cleanup_temp_files(temp_audio_files)
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    logger.error(f"  ✗ 音频合并失败")
                    raise Exception("音频合并失败")

            else:
                # 单人配音模式
                audio_path = audio_exporter.get_output_path(
                    index=chapter.index,
                    title=chapter.title,
                    role="default",
                    custom_base_path=output_dir
                )
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

                # TTS 生成音频（单人配音模式）
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

            # 如果是 LLM 余额不足（402），则终止后续章节生成
            msg = str(e)
            if "Insufficient Balance" in msg or "Error code: 402" in msg:
                logger.error("  ⚠ 检测到 LLM 余额不足（402），终止后续章节生成")
                break

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

  # 角色分析（智能模式，自动合并重复角色）
  python cli.py -i debug/择天记_修复.txt --analyze-characters

  # 角色分析（混合模式，用户指定角色列表）
  python cli.py -i debug/择天记_修复.txt --analyze-characters --character-list characters.txt

  # 角色分析（强制使用混合模式）
  python cli.py -i debug/择天记_修复.txt --analyze-characters --analysis-mode hybrid --character-list characters.txt
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

    parser.add_argument(
        "--analyze-characters",
        action="store_true",
        help="角色分析模式：分析小说角色并生成配音模板（生成后退出）"
    )

    parser.add_argument(
        "--multi-voice",
        nargs='?',
        const=None,
        type=str.lower,
        choices=["true", "false"],
        help="是否启用多角色配音模式（true/false，不带值或不写则使用配置文件）"
    )

    parser.add_argument(
        "--character-template",
        type=str,
        help="指定角色配音模板文件路径（可选，默认自动查找 cache/role/[文件名]_characters.json）"
    )

    parser.add_argument(
        "--character-list",
        type=str,
        help="指定角色列表文件路径（混合模式）：每行一个角色名，可选格式 '角色名 性别'"
    )

    parser.add_argument(
        "--analysis-mode",
        type=str,
        choices=["auto", "hybrid"],
        help="角色分析模式（覆盖配置文件的 CHARACTER_ANALYSIS_MODE）：auto=智能分析+自动合并, hybrid=用户指定角色列表"
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
    # 参数优先级：命令行参数 > 配置文件

    # LLM 参数
    if args.no_llm:
        enable_llm_arg = False
    else:
        enable_llm_arg = None  # 使用配置文件的值

    # 多角色参数（True/False/None）
    if args.multi_voice is None:
        multi_voice_arg = None  # 使用配置文件的值
    else:
        # 命令行使用: --multi-voice true / --multi-voice false
        multi_voice_arg = (args.multi_voice == "true")

    # 角色分析模式参数
    analysis_mode_arg = args.analysis_mode if args.analysis_mode else None

    asyncio.run(generate_from_file(
        input_file=args.input,
        output_dir=args.output,
        voice=args.voice,
        rate=args.rate,
        enable_llm=enable_llm_arg,
        start_chapter=args.start,
        end_chapter=args.end,
        analyze_characters=args.analyze_characters,
        multi_voice=multi_voice_arg,
        character_template=args.character_template,
        character_list=args.character_list,
        analysis_mode=analysis_mode_arg
    ))


if __name__ == "__main__":
    main()

