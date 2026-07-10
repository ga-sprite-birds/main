#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge TTS voice casting audition tool - command-line interface
Fetches the available voice list and generates audition audio
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.try_tts.i18n import t, get_i18n
from utils.try_tts.voice_fetcher import VoiceFetcher
from utils.try_tts.sample_generator import SampleGenerator
from utils.try_tts.doc_exporter import DocExporter

# Default language (later updated based on arguments or config)
_default_lang = "en_US"
try:
    import config
    _default_lang = config.LANGUAGE
except ImportError:
    pass


def _builtin_language_label(language_key: str) -> str:
    locale = getattr(get_i18n(), "locale", "en_US")
    if locale == "zh_CN":
        return "中文" if language_key == "zh" else "英文"
    return "Chinese" if language_key == "zh" else "English"


def parse_args():
    # Pre-parse the --language argument to set the help-text language
    import sys
    help_lang = _default_lang
    if '--language' in sys.argv:
        try:
            lang_index = sys.argv.index('--language')
            if lang_index + 1 < len(sys.argv):
                help_lang = sys.argv[lang_index + 1]
        except (ValueError, IndexError):
            pass

    # Set the help-text language
    get_i18n(help_lang)
    """Parse command-line arguments"""
    examples = f"""
{t('help.examples')}
  # {t('help.example_list_all')}
  python utils/try_tts/cli.py list

  # {t('help.example_list_lang')}
  python utils/try_tts/cli.py list --lang zh-CN

  # {t('help.example_list_gender')}
  python utils/try_tts/cli.py list --lang zh-CN --gender male

  # {t('help.example_generate_all')}
  python utils/try_tts/cli.py generate --lang zh-CN

  # {t('help.example_generate_one')}
  python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural

  # {t('help.example_export')}
  python utils/try_tts/cli.py list --lang zh-CN --save-doc voices.md
    """

    parser = argparse.ArgumentParser(
        description=t('help.description'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples
    )

    parser.add_argument(
        'action',
        choices=['list', 'generate'],
        help=t('help.action')
    )

    parser.add_argument(
        '--lang',
        help=t('help.lang')
    )

    parser.add_argument(
        '--gender',
        choices=['male', 'female', '1', '0'],
        help=t('help.gender')
    )

    parser.add_argument(
        '--voice',
        help=t('help.voice')
    )

    parser.add_argument(
        '--text',
        help=t('help.text')
    )

    parser.add_argument(
        '--output',
        default='./output/tts_samples',
        help=t('help.output')
    )

    parser.add_argument(
        '--save-doc',
        metavar='FILE',
        help=t('help.save_doc')
    )

    parser.add_argument(
        '--language',
        choices=['en_US', 'zh_CN'],
        help=t('help.ui_language')
    )

    return parser.parse_args()


def main():
    """Main function"""
    args = parse_args()

    # The language was already set in parse_args(), no need to set it again here
    # The language was already set in parse_args() based on the --language argument

    print("=" * 100)
    print(t('help.description'))
    print("=" * 100)

    fetcher = VoiceFetcher()

    print(f"\n📡 {t('fetching_voices')}")
    fetcher.get_voices_sync()
    print(f"✓ {t('voices_fetched', count=len(fetcher.voices))}")

    language_display = args.lang or t("all")
    gender_display = args.gender or t("all")

    filtered_voices = fetcher.filter_voices(
        language=args.lang,
        gender=args.gender
    )

    if args.action == 'list':
        filter_msg = t('filter_condition',
                       language=language_display,
                       gender=gender_display)
        print(f"\n📋 {filter_msg}")
        print()
        print(VoiceFetcher.format_voice_list(filtered_voices))

        if args.save_doc:
            print(f"\n💾 {t('saving_doc')}")
            doc_path = DocExporter.export_to_markdown(
                filtered_voices,
                args.save_doc,
                language=language_display,
                gender=gender_display
            )
            print(f"✓ {t('list_exported', file=doc_path)}")
    
    elif args.action == 'generate':
        generator = SampleGenerator(args.output)

        if args.voice:
            print(f"\n🎵 {t('single_generate', voice=args.voice)}")
            if not args.text:
                builtin_key = generator._normalize_language_key(
                    generator._extract_locale_from_voice(args.voice)
                )
                if not builtin_key:
                    print(f"\n❌ {t('text_required_for_language', language=generator._extract_locale_from_voice(args.voice) or args.voice)}")
                    sys.exit(1)
                print(f"   {t('using_builtin_text', language=_builtin_language_label(builtin_key))}")

            output_file = generator.generate_sample_sync(
                args.voice,
                args.text,
                language=generator._extract_locale_from_voice(args.voice),
            )
            print(f"✓ {t('audio_generated', file=output_file)}")
        else:
            if not filtered_voices:
                print(f"\n❌ {t('no_voices')}")
                sys.exit(1)

            if not args.text:
                builtin_key = generator._normalize_language_key(args.lang)
                if not args.lang:
                    print(f"\n❌ {t('text_required_for_mixed_languages')}")
                    sys.exit(1)
                if not builtin_key:
                    print(f"\n❌ {t('text_required_for_language', language=args.lang)}")
                    sys.exit(1)
                print(f"\n📝 {t('using_builtin_text', language=_builtin_language_label(builtin_key))}")

            print(f"\n🎵 {t('batch_generate')}")
            filter_msg = t('filter_condition',
                           language=language_display,
                           gender=gender_display)
            print(f"   {filter_msg}")
            print(f"   {t('voice_count', count=len(filtered_voices))}")
            print(f"   {t('output_dir', dir=args.output)}")
            print()

            result = generator.generate_batch_sync(
                filtered_voices,
                args.text,
                show_progress=True,
                language=language_display,
                gender=gender_display
            )

            print()
            print(f"✓ {t('batch_complete')}")
            print(f"  {t('status', msg=result['msg'])}")
            print(f"  {t('success_count', count=result['data']['success'])}")
            print(f"  {t('failed_count', count=result['data']['failed'])}")
            print(f"✓ {t('output_dir', dir=args.output)}")
            json_file = f'{args.output}/voices.json'
            md_file = f'{args.output}/voices.md'
            print(f"✓ Results saved: {json_file}, {md_file}")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()

