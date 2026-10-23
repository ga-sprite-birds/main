"""
GA Sprite Birds - CLI command-line mode
Generate audio directly from the command line without starting the API server

Version: v1.0
Dev team: Tiger
"""

import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import argparse
import importlib
import json
import shutil
from typing import Optional

from loguru import logger

import config
from ga_birds.Common.i18n import t

# Initialize multilingual support (defaults to config file, can be overridden via CLI argument)
_core_module_name = config.CORE_DIR.replace('-', '_')
_i18n_module = importlib.import_module(f'{_core_module_name}.Common.i18n')
_default_language = config.LANGUAGE

# Pre-parse the --language argument to set up multilingual support
if '--language' in sys.argv:
    try:
        lang_index = sys.argv.index('--language')
        if lang_index + 1 < len(sys.argv):
            _default_language = sys.argv[lang_index + 1]
    except (ValueError, IndexError):
        pass

_i18n_module.set_locale(_default_language)

# Dynamically import core modules (based on config.CORE_DIR)
_llm_module = importlib.import_module(f'{_core_module_name}.LLM')
_audio_module = importlib.import_module(f'{_core_module_name}.Audio')
_character_module = importlib.import_module(f'{_core_module_name}.character_analyzer')
_common_module = importlib.import_module(f'{_core_module_name}.Common')

# Import required classes and functions
load_chapters = _common_module.load_chapters
generate_single_voice_chapter = _audio_module.generate_single_voice_chapter
resolve_output_path = _audio_module.resolve_output_path
LLMManager = _llm_module.LLMManager
TTSManager = _audio_module.TTSManager
AudioExporter = _audio_module.AudioExporter
AudioMerger = _audio_module.AudioMerger
InterjectionMapper = _audio_module.InterjectionMapper
CharacterAnalyzer = _character_module.CharacterAnalyzer
DialogueParser = _character_module.DialogueParser
VoiceAssigner = _character_module.VoiceAssigner
CharacterListParser = _character_module.CharacterListParser
CharacterMerger = _character_module.CharacterMerger

# Import from the Common module
ParamManager = _common_module.ParamManager
ChapterProcessor = _common_module.ChapterProcessor
ChapterTextSaver = _common_module.ChapterTextSaver


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
    Generate audio from a file

    Args:
        input_file: Input file path
        output_dir: Output directory (optional)
        voice: Voice timbre (optional)
        rate: Speech rate (optional, 0.5-2.0)
        enable_llm: Whether to enable LLM colloquialization (None=use config file)
        start_chapter: Starting chapter (1-based)
        end_chapter: Ending chapter (optional, None means to the end)
        analyze_characters: Character analysis mode (exit after generating template)
        multi_voice: Multi-character voice mode (None=use config file)
        character_template: Character voice cast template file path (optional)
        character_list: Character list file path (hybrid mode, optional)
        analysis_mode: Character analysis mode (None=use config file, auto=smart analysis, hybrid=hybrid mode)
    """
    # Check the input file
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(t("cli.file_not_found", path=input_file))
        return

    # ========== Parameter merging: CLI/API arguments > config file ==========
    enable_llm = ParamManager.merge_enable_llm(enable_llm)
    multi_voice = ParamManager.merge_multi_voice(multi_voice)

    if rate is not None and not 0.5 <= rate <= 2.0:
        logger.error(t("cli.invalid_rate"))
        return

    logger.info(t("cli.input_file", path=input_file))
    logger.info(t("cli.llm_mode", mode=config.LLM_MODE))
    logger.info(t("cli.tts_engine", engine=config.TTS_ENGINE))
    logger.info(t("cli.llm_enabled", enabled=enable_llm))
    logger.info(t("cli.multi_voice", enabled=multi_voice))
    logger.info("")

    # Read, preprocess, normalize, and split chapters through the shared loader.
    logger.info(t("cli.reading_file"))
    chapters = load_chapters(str(input_path))
    logger.info(t("cli.chapters_parsed", count=len(chapters)))
    logger.info("")

    # Determine the range of chapters to process
    if end_chapter is None:
        end_chapter = len(chapters)

    # Validate chapter range
    if start_chapter < 1 or start_chapter > len(chapters):
        logger.error(t("cli.start_chapter_invalid", start=start_chapter, total=len(chapters)))
        return

    if end_chapter < start_chapter or end_chapter > len(chapters):
        logger.error(t("cli.end_chapter_invalid", end=end_chapter, start=start_chapter, total=len(chapters)))
        return

    logger.info(t("cli.processing_chapters", start=start_chapter, end=end_chapter))
    logger.info("")
    selected_contents = [
        chapter.content
        for chapter in chapters
        if start_chapter <= chapter.index <= end_chapter
    ]

    # ========== Character analysis mode ==========
    if analyze_characters:
        logger.info("")
        logger.info("=" * 60)

        # Determine the analysis mode (priority: CLI argument > character_list > config file)
        if analysis_mode is None:
            # The --analysis-mode argument was not specified
            if character_list:
                # The --character-list argument is present, use hybrid mode
                analysis_mode = "hybrid"
            else:
                # Use the value from the config file
                analysis_mode = config.CHARACTER_ANALYSIS_MODE

        # Hybrid mode requires a character list file
        if analysis_mode == "hybrid" and not character_list:
            logger.error(t("cli.hybrid_needs_list"))
            logger.error(t("cli.hybrid_use_list"))
            logger.error("")
            logger.error(t("cli.example"))
            logger.error("  bash cli.sh -i input.txt --analyze-characters --analysis-mode hybrid --character-list characters.txt")
            logger.error("")
            logger.error(t("cli.or_use_auto"))
            logger.error("  bash cli.sh -i input.txt --analyze-characters")
            return

        # Display the analysis mode
        if analysis_mode == "hybrid":
            logger.info(t("cli.analysis_mode_hybrid"))
        else:
            logger.info(t("cli.analysis_mode_auto"))

        logger.info("=" * 60)
        logger.info("")

        # Initialize the LLM
        logger.info(t("cli.initializing_llm"))
        try:
            llm_manager = LLMManager()
            logger.info(t("cli.llm_init_success"))
        except Exception as e:
            logger.error(t("cli.llm_init_failed", error=e))
            logger.error(t("cli.analysis_needs_llm"))
            return

        logger.info("")

        # ========== Hybrid mode: user-specified character list ==========
        if analysis_mode == "hybrid":
            logger.info(t("cli.reading_character_list"))

            # Parse the character list file
            user_characters = CharacterListParser.parse_file(character_list)

            if not user_characters:
                logger.error(t("cli.character_list_empty"))
                return

            if not CharacterListParser.validate_characters(user_characters):
                logger.error(t("cli.character_list_invalid"))
                return

            logger.info(t("cli.user_characters_found", count=len(user_characters)))
            for char in user_characters:
                logger.info(f"  - {char['name']} ({char['gender']})")

            logger.info("")
            logger.info(t("cli.analyzing_aliases"))

            # Find aliases and personality for each specified character
            analyzer = CharacterAnalyzer(llm_manager)
            character_names = [char['name'] for char in user_characters]

            # Merge analysis results across all chapters
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

                logger.info(t("cli.analyzing_chapter", index=chapter.index, title=chapter.title))
                chapter_data = analyzer.analyze_chapter_for_characters(
                    chapter.content,
                    chapter.index,
                    character_names
                )

                # Merge results
                for char_name, info in chapter_data.items():
                    if char_name in character_info:
                        # Merge aliases
                        character_info[char_name]['aliases'].update(info.get('aliases', []))
                        # Merge personality tags
                        character_info[char_name]['personality'].update(info.get('personality', []))
                        # Update appearance count
                        character_info[char_name]['appearance_count'] += 1
                        # Update first appearing chapter
                        if character_info[char_name]['first_chapter'] is None:
                            character_info[char_name]['first_chapter'] = chapter.index
                        # Update last appearing chapter
                        character_info[char_name]['last_chapter'] = chapter.index

                        logger.info(t("cli.alias_info", name=char_name, aliases=list(info.get('aliases', []))))

            # Convert to final format
            all_characters = []
            for char in user_characters:
                char_name = char['name']
                info = character_info[char_name]

                all_characters.append({
                    'name': char_name,
                    'aliases': list(info['aliases']),
                    'gender': char['gender'],
                    'personality': list(info['personality']),
                    'profile': info.get('profile', {
                        "age_group": "unknown",
                        "occupation": "unknown",
                        "region_hint": "unknown",
                        "accent_preference": "unknown",
                        "speech_style": [],
                    }),
                    'appearance_count': info['appearance_count'],
                    'first_chapter': info['first_chapter'] or 0,
                    'last_chapter': info['last_chapter'] or 0
                })

            logger.info("")
            logger.info(t("cli.hybrid_done"))

        # ========== Smart analysis mode: LLM auto-discovers characters ==========
        else:
            logger.info(t("cli.auto_analysis_start"))

            # Analyze characters
            analyzer = CharacterAnalyzer(llm_manager)

            for chapter in chapters:
                if chapter.index < start_chapter or chapter.index > end_chapter:
                    continue

                logger.info(t("cli.analyzing_chapter", index=chapter.index, title=chapter.title))
                characters = analyzer.analyze_chapter(chapter.content, chapter.index)
                if characters:
                    logger.info(t("cli.chapter_characters", count=len(characters), names=', '.join([c['name'] for c in characters])))
                    analyzer.merge_characters(characters, chapter.index)
                else:
                    logger.info(t("cli.chapter_no_characters"))

            # Get all characters
            all_characters = analyzer.get_all_characters()
            logger.info("")
            logger.info(t("cli.total_characters_found", count=len(all_characters)))

            # Automatically merge duplicate characters
            logger.info("")
            logger.info(t("cli.checking_duplicates"))
            merger = CharacterMerger(llm_manager)
            all_characters = merger.merge_duplicate_characters(all_characters)

        # Assign voices (timbre)
        logger.info("")
        logger.info(t("cli.assigning_voices"))
        voice_assigner = VoiceAssigner(source_text="\n\n".join(selected_contents))
        all_characters = voice_assigner.assign_voices(all_characters)

        # Create the character voice cast template
        character_template_data = VoiceAssigner.create_character_template(
            all_characters,
            input_path.stem,
            input_path.stem,
            narrator_voice=voice_assigner.narrator_voice,
        )

        # Save the template
        template_path = Path(config.CHARACTER_CACHE_DIR) / f"{input_path.stem}_characters.json"
        template_path.parent.mkdir(parents=True, exist_ok=True)

        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(character_template_data, f, ensure_ascii=False, indent=2)

        logger.info(t("cli.template_saved", path=template_path))
        logger.info("")
        logger.info("=" * 60)
        logger.info(t("cli.character_stats"))
        logger.info("=" * 60)
        logger.info(t("cli.total_count", count=len(all_characters)))
        logger.info("")

        for i, char in enumerate(all_characters[:10], 1):
            logger.info(t("cli.char_summary", i=i, name=char['name'], voice=char['voice'], count=char['appearance_count']))

        if len(all_characters) > 10:
            logger.info(t("cli.more_characters", count=len(all_characters) - 10))

        logger.info("")
        logger.info(t("cli.narrator_voice", voice=character_template_data['narrator']['voice']))
        logger.info("")
        logger.info("=" * 60)
        logger.info(t("cli.next_step"))
        logger.info("=" * 60)
        logger.info(t("cli.edit_template"))
        logger.info(f"  {template_path}")
        logger.info("")
        logger.info(t("cli.then_generate"))
        logger.info(f"  bash cli.sh -i {input_file} --multi-voice")
        logger.info("")

        # Character analysis complete, exit
        return

    # ========== TTS generation mode ==========

    # Initialize managers
    llm_manager = None
    if enable_llm or multi_voice:
        try:
            logger.info(t("cli.initializing_llm"))
            llm_manager = LLMManager()
            logger.info(t("cli.llm_init_success"))
        except Exception as e:
            logger.error(t("cli.llm_init_failed", error=e))
            if multi_voice:
                logger.error(t("cli.analysis_needs_llm"))
                return
            logger.warning(t("cli.skipping_llm"))
            import traceback
            logger.debug(traceback.format_exc())

    # Multi-character voice: load the character template
    character_template_data = None
    segment_voice_assigner = None
    if multi_voice:
        logger.info("")
        logger.info("=" * 60)
        logger.info(t("cli.multi_voice_mode"))
        logger.info("=" * 60)
        logger.info("")

        # Determine the template file path
        if character_template is None:
            # Auto-locate the template file
            template_path = Path(config.CHARACTER_CACHE_DIR) / f"{input_path.stem}_characters.json"
            logger.info(t("cli.auto_find_template", path=template_path))
        else:
            # Use the specified template file
            template_path = Path(character_template)
            logger.info(t("cli.using_template", path=template_path))

        # Check whether the template file exists
        if not template_path.exists():
            logger.error(t("cli.template_not_found", path=template_path))
            logger.error("")
            logger.error(t("cli.generate_template_first"))
            logger.error(f"  bash cli.sh -i {input_file} --analyze-characters")
            logger.error("")
            return

        # Load the template file
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                character_template_data = json.load(f)
            logger.info(t("cli.template_loaded", count=character_template_data['total_characters']))
        except json.JSONDecodeError as e:
            logger.error(t("cli.template_json_error", error=e))
            logger.error(t("cli.template_json_path", path=template_path))
            logger.error("")
            logger.error(t("cli.template_check_hints"))
            logger.error(t("cli.hint1"))
            logger.error(t("cli.hint2"))
            logger.error(t("cli.hint3"))
            logger.error("")
            logger.error(t("cli.template_regenerate"))
            logger.error(f"  bash cli.sh -i {input_file} --analyze-characters")
            logger.error("")
            return
        except Exception as e:
            logger.error(t("cli.template_load_failed", error=e))
            logger.error(t("cli.template_load_path", path=template_path))
            logger.error("")
            return

        segment_voice_assigner = VoiceAssigner(source_text="\n\n".join(selected_contents))
        logger.info("")

    logger.info(t("cli.initializing_tts"))
    tts_manager = TTSManager()

    logger.info(t("cli.initializing_exporter"))
    audio_exporter = AudioExporter()

    logger.info("")
    logger.info("=" * 60)
    logger.info(t("cli.starting_generation"))
    logger.info("=" * 60)
    logger.info("")

    # Generate audio
    success_count = 0
    failed_count = 0

    for chapter in chapters:
        # Check whether within the processing range
        if chapter.index < start_chapter or chapter.index > end_chapter:
            continue

        logger.info(f"[{chapter.index}/{len(chapters)}] {chapter.title}")
        logger.info(t("cli.content_length", length=len(chapter.content)))

        try:
            # Multi-character voice vs single voice
            if multi_voice and character_template_data:
                # Multi-character voice mode
                logger.info(t("cli.using_multi_voice"))

                # Save original content for comparison
                original_content = chapter.content
                original_length = len(original_content)
                content = original_content
                colloquialized_content = None

                # LLM colloquialization (optional)
                if enable_llm:
                    if llm_manager:
                        logger.info(t("cli.llm_colloquializing"))
                        logger.debug(t("cli.llm_original_length", length=original_length))
                        logger.debug(t("cli.llm_original_preview", text=content[:100]))
                        try:
                            colloquialized_content = llm_manager.colloquialize_text(content)
                            colloquialized_length = len(colloquialized_content)
                            logger.debug(t("cli.llm_result_length", length=colloquialized_length))
                            logger.debug(t("cli.llm_result_preview", text=colloquialized_content[:100]))

                            # Check whether the LLM actually changed the text
                            if colloquialized_content != content:
                                content = colloquialized_content
                                logger.info(t("cli.llm_done", original=original_length, result=colloquialized_length))
                            else:
                                logger.warning(t("cli.llm_unchanged"))
                                logger.warning(t("cli.llm_debug_saved"))
                                # Do not set to None; keep the LLM output for debugging

                        except Exception as e:
                            logger.error(t("cli.llm_failed", error=e))
                            logger.warning(t("cli.llm_using_original"))
                            import traceback
                            logger.debug(traceback.format_exc())
                            colloquialized_content = None
                    else:
                        logger.warning(t("cli.llm_not_initialized"))
                        logger.debug(f"  → enable_llm={enable_llm}, llm_manager={llm_manager}")

                # Add intro/outro (using ChapterProcessor)
                intro, outro = ChapterProcessor.prepare_intro_outro(
                    chapter.index, chapter.title
                )
                logger.debug(t("cli.intro_outro_enabled", enabled=intro is not None))

                # 1. Parse dialogue (only the body, excluding intro/outro)
                dialogue_parser = DialogueParser(
                    llm_manager, character_template_data['characters']
                )
                # Note: dialogue parsing is based only on body content, excluding intro/outro,
                # to avoid losing prompts like "本章播讲完毕" when the LLM truncates its output

                segments = dialogue_parser.parse_chapter(content, chapter.index)
                logger.info(t("cli.dialog_segments", count=len(segments)))

                # Validate content completeness
                original_length = len(content)
                total_segment_length = sum(len(seg['text']) for seg in segments)
                completeness_ratio = total_segment_length / original_length if original_length > 0 else 0

                logger.debug(t("cli.dialog_original_length", length=original_length))
                logger.debug(t("cli.dialog_total_length", length=total_segment_length))
                logger.debug(t("cli.dialog_completeness", ratio=completeness_ratio))

                if completeness_ratio < 0.9:
                    logger.warning(t("cli.dialog_content_loss", orig=original_length, parsed=total_segment_length, ratio=completeness_ratio))
                elif completeness_ratio > 1.5:
                    logger.warning(t("cli.dialog_content_swell", orig=original_length, parsed=total_segment_length, ratio=completeness_ratio))

                # Add intro/outro (using DialogueParser's static method)
                segments = DialogueParser.add_intro_outro_to_segments(
                    segments, intro, outro
                )
                if intro and outro:
                    logger.info(t("cli.dialog_with_intro_outro", count=len(segments)))

                # Generate the output path (used to save text)
                audio_path = audio_exporter.get_output_path(
                    index=chapter.index,
                    title=chapter.title,
                    role="multi",
                    custom_base_path=output_dir
                )
                audio_path.parent.mkdir(parents=True, exist_ok=True)

                resolved_path = resolve_output_path(audio_path)
                if resolved_path is None:
                    logger.info("")
                    success_count += 1
                    continue
                audio_path = resolved_path

                # Save chapter text (multi-character mode - saved before TTS generation)
                ChapterTextSaver.save_multi_voice_text(
                    audio_path=audio_path,
                    segments=segments,
                    original_content=original_content,
                    llm_content=colloquialized_content,
                    enable_llm=enable_llm
                )

                # 2. Generate audio for each segment
                temp_audio_files = []
                temp_dir = Path("cache/audio_temp") / f"chapter_{chapter.index}"
                temp_dir.mkdir(parents=True, exist_ok=True)

                for i, segment in enumerate(segments):
                    segment_text = segment['text']
                    speaker = dialogue_parser.normalize_speaker(segment['speaker'])
                    segment['speaker'] = speaker
                    segment_voice = segment_voice_assigner.get_voice_for_segment(
                        segment,
                        character_template_data,
                    )
                    tts_params = segment.get("tts_params", {})

                    # Generate a temporary audio file
                    temp_audio_path = temp_dir / f"segment_{i:03d}.mp3"

                    # Convert pure-punctuation text into interjections
                    tts_text = InterjectionMapper.process_text_for_tts(segment_text)

                    # Display segment info (if text is very short, show full text)
                    if len(segment_text) <= 10:
                        if tts_text != segment_text:
                            logger.debug(t("cli.segment_debug_with_text", i=i+1, total=len(segments), speaker=speaker, voice=segment_voice, raw=repr(segment_text), tts=repr(tts_text)))
                        else:
                            logger.debug(t("cli.segment_debug_with_text", i=i+1, total=len(segments), speaker=speaker, voice=segment_voice, raw=repr(segment_text), tts=repr(segment_text)))
                    else:
                        logger.debug(t("cli.segment_debug", i=i+1, total=len(segments), speaker=speaker, voice=segment_voice, length=len(segment_text)))

                    await tts_manager.generate_audio(
                        text=tts_text,
                        output_path=str(temp_audio_path),
                        voice=segment_voice,
                        rate=tts_params.get("rate"),
                        volume=tts_params.get("volume"),
                        pitch=tts_params.get("pitch"),
                    )

                    temp_audio_files.append(str(temp_audio_path))

                # 3. Merge audio
                logger.info(t("cli.merging_audio", count=len(temp_audio_files)))
                audio_merger = AudioMerger()
                if audio_merger.merge_audio_files(temp_audio_files, str(audio_path)):
                    logger.info(t("cli.merge_complete"))
                    # Clean up temporary files
                    audio_merger.cleanup_temp_files(temp_audio_files)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    logger.error(t("cli.merge_failed"))
                    raise Exception("音频合并失败")

            else:
                # Single-voice mode (shared with the API)
                await generate_single_voice_chapter(
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    content=chapter.content,
                    output_dir=output_dir,
                    voice=voice,
                    rate=rate,
                    enable_llm=enable_llm,
                    llm_manager=llm_manager,
                    tts_manager=tts_manager,
                    audio_exporter=audio_exporter,
                )

            logger.info("")
            success_count += 1

        except Exception as e:
            logger.error(t("cli.generation_failed", error=e))
            logger.info("")
            failed_count += 1

            # If the LLM balance is insufficient (402), stop generating subsequent chapters
            msg = str(e)
            if "Insufficient Balance" in msg or "Error code: 402" in msg:
                logger.error(t("cli.payment_required"))
                break

    # Summary
    logger.info("=" * 60)
    logger.info(t("cli.all_done"))
    logger.info("=" * 60)
    logger.info(t("cli.success_count", count=success_count))
    logger.info(t("cli.failed_count", count=failed_count))
    logger.info(t("cli.total_count", count=success_count + failed_count))


def main():
    """CLI main function"""
    # Build the example text
    examples = f"""{t('cli.examples.title')}
  {t('cli.examples.basic')}

  {t('cli.examples.output')}

  {t('cli.examples.voice')}

  {t('cli.examples.no_llm')}

  {t('cli.examples.chapters')}

  {t('cli.examples.analyze_auto')}

  {t('cli.examples.analyze_hybrid')}

  {t('cli.examples.analyze_force')}
        """

    parser = argparse.ArgumentParser(
        description=t('cli.description'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help=t('cli.help.input')
    )

    parser.add_argument(
        "-o", "--output",
        help=t('cli.help.output')
    )

    parser.add_argument(
        "--voice",
        help=t('cli.help.voice')
    )

    parser.add_argument(
        "--rate",
        type=float,
        help=t('cli.help.rate')
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help=t('cli.help.no_llm')
    )

    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help=t('cli.help.start')
    )

    parser.add_argument(
        "--end",
        type=int,
        help=t('cli.help.end')
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help=t('cli.help.log_level')
    )

    parser.add_argument(
        "--language",
        choices=["en_US", "zh_CN"],
        help=t('cli.help.language')
    )

    parser.add_argument(
        "--analyze-characters",
        action="store_true",
        help=t('cli.help.analyze_characters')
    )

    parser.add_argument(
        "--multi-voice",
        nargs='?',
        const="true",
        type=str.lower,
        choices=["true", "false"],
        help=t('cli.help.multi_voice')
    )

    parser.add_argument(
        "--character-template",
        type=str,
        help=t('cli.help.character_template')
    )

    parser.add_argument(
        "--character-list",
        type=str,
        help=t('cli.help.character_list')
    )

    parser.add_argument(
        "--analysis-mode",
        type=str,
        choices=["auto", "hybrid"],
        help=t('cli.help.analysis_mode')
    )

    args = parser.parse_args()

    # Configure logging
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

    # Run the generation task
    # Parameter priority: CLI arguments > config file

    # LLM parameters
    if args.no_llm:
        enable_llm_arg = False
    else:
        enable_llm_arg = None  # Use the value from the config file

    # Multi-character parameters (True/False/None)
    if args.multi_voice is None:
        multi_voice_arg = None  # Use the value from the config file
    else:
        # CLI usage: --multi-voice true / --multi-voice false
        multi_voice_arg = (args.multi_voice == "true")

    # Character analysis mode parameter
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

