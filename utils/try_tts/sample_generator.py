"""
Audition audio generator
Generates audition audio files for specified voices
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import edge_tts
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.try_tts.i18n import t
from ga_birds.Utils import get_unique_filename

logger = logging.getLogger(__name__)

# TTS retry decorator (for utils tooling)
tts_sample_retry = retry(
    stop=stop_after_attempt(3),  # 3 retries are enough for the audition tool
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


class SampleGenerator:
    """Audition audio generator"""

    DEFAULT_TEXTS = {
        "zh": "欢迎使用 GA Birds 文本转语音服务。这是一段中文试听文本。",
        "en": "Welcome to the GA Birds text-to-speech service. This is an English sample.",
    }
    
    def __init__(self, output_dir: str = "./output/tts_samples"):
        """
        Initialize the audition audio generator
        
        Args:
            output_dir: output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_language_key(language: Optional[str]) -> str:
        if not language:
            return ""
        lowered = str(language).strip().lower().replace("_", "-")
        if lowered.startswith("zh"):
            return "zh"
        if lowered.startswith("en"):
            return "en"
        return ""

    @staticmethod
    def _extract_locale_from_voice(voice: str) -> str:
        parts = str(voice).split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        return ""

    def resolve_sample_text(
        self,
        text: Optional[str] = None,
        language: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> str:
        """Resolve the sample text for a voice/language."""
        if text:
            return text

        normalized = self._normalize_language_key(language)
        if not normalized and voice:
            normalized = self._normalize_language_key(
                self._extract_locale_from_voice(voice)
            )

        if normalized in self.DEFAULT_TEXTS:
            return self.DEFAULT_TEXTS[normalized]

        language_label = language or self._extract_locale_from_voice(voice or "") or "unknown"
        raise ValueError(t("text_required_for_language", language=language_label))
    
    @tts_sample_retry
    async def generate_sample(
        self,
        voice: str,
        text: Optional[str] = None,
        language: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz"
    ) -> str:
        """
        Generate audition audio for a single voice (with automatic retry)

        Args:
            voice: voice name (e.g. zh-CN-XiaoxiaoNeural)
            text: audition text (uses the default text if None)
            rate: speech rate (e.g. "+0%")
            volume: volume (e.g. "+0%")
            pitch: pitch (e.g. "+0Hz")

        Returns:
            path to the generated audio file
        """
        text = self.resolve_sample_text(text=text, language=language, voice=voice)

        output_file = self.output_dir / f"{voice}.mp3"
        output_file = get_unique_filename(output_file)

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch
        )

        await communicate.save(str(output_file))

        return str(output_file)
    
    async def generate_batch(
        self,
        voices: List[Dict],
        text: Optional[str] = None,
        show_progress: bool = True,
        language: str = "全部",
        gender: str = "全部"
    ) -> Dict:
        """
        Batch-generate audition audio

        Args:
            voices: voice list (fetched from VoiceFetcher)
            text: audition text (uses the default text if None)
            show_progress: whether to show progress
            language: filtered language (used for saved records)
            gender: filtered gender (used for saved records)

        Returns:
            generation result (containing code, msg, data)
        """
        total = len(voices)
        voice_results = []

        for i, voice in enumerate(voices, 1):
            voice_name = voice.get('ShortName')

            if show_progress:
                print(f"[{i}/{total}] {t('generating')}: {voice_name}")

            voice_result = {
                "name": voice_name,
                "gender": voice.get('Gender', 'Unknown'),
                "language": voice.get('Locale', 'Unknown'),
                "friendly_name": voice.get('FriendlyName', 'Unknown'),
                "audio_file": None,
                "status": "failed",
                "error": None
            }

            try:
                # generate_sample already has the @tts_sample_retry decorator, which retries automatically
                output_file = await self.generate_sample(
                    voice_name,
                    text,
                    language=voice.get('Locale'),
                )
                voice_result["audio_file"] = output_file
                voice_result["status"] = "success"

                if show_progress:
                    print(f"  ✓ {t('saved')}: {output_file}")
            except Exception as error:
                # Still failed after 3 retries
                voice_result["error"] = str(error)
                if show_progress:
                    print(f"  ✗ {t('failed')}: {error}")

            voice_results.append(voice_result)

        success_count = sum(1 for v in voice_results if v["status"] == "success")
        failed_count = total - success_count

        if failed_count == 0:
            code = 1
            msg = "全部生成成功"
        elif success_count == 0:
            code = 0
            msg = "全部生成失败"
        else:
            code = 2
            msg = f"部分生成成功，{success_count} 个成功，{failed_count} 个失败"

        result = {
            "code": code,
            "msg": msg,
            "data": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "filter": {
                    "language": language,
                    "gender": gender
                },
                "output_dir": str(self.output_dir),
                "total": total,
                "success": success_count,
                "failed": failed_count,
                "voices": voice_results
            }
        }

        self._save_results(result)

        return result
    
    def generate_sample_sync(
        self,
        voice: str,
        text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        Generate a single audition audio synchronously
        
        Args:
            voice: voice name
            text: audition text
            
        Returns:
            path to the generated audio file
        """
        return asyncio.run(self.generate_sample(voice, text, language=language))
    
    def generate_batch_sync(
        self,
        voices: List[Dict],
        text: Optional[str] = None,
        show_progress: bool = True,
        language: str = "全部",
        gender: str = "全部"
    ) -> Dict:
        """
        Batch-generate audition audio synchronously

        Args:
            voices: voice list
            text: audition text
            show_progress: whether to show progress
            language: filtered language
            gender: filtered gender

        Returns:
            generation result (containing code, msg, data)
        """
        return asyncio.run(
            self.generate_batch(voices, text, show_progress, language, gender)
        )

    def _save_results(self, result: Dict):
        """
        Save the generation result to JSON and Markdown files

        Args:
            result: generation result
        """
        json_file = self.output_dir / "voices.json"
        md_file = self.output_dir / "voices.md"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self._save_markdown(result, md_file)

    def _save_markdown(self, result: Dict, output_path: Path):
        """
        Save the result in Markdown format

        Args:
            result: generation result
            output_path: output file path
        """
        data = result["data"]
        lines = []

        lines.append("# Edge TTS 试听列表\n")
        lines.append(f"**生成时间**: {data['generated_at']}\n")
        lines.append(f"**筛选条件**: 语言={data['filter']['language']}, 性别={data['filter']['gender']}\n")
        lines.append(f"**音色总数**: {data['total']}\n")
        lines.append(f"**成功**: {data['success']} | **失败**: {data['failed']}\n")
        lines.append("---\n")

        lines.append("## 生成结果\n")
        lines.append("| 序号 | 状态 | 姓名 | 性别 | 语言 | 友好名称 | 音频文件 |")
        lines.append("|------|------|------|------|------|----------|----------|")

        for i, voice in enumerate(data['voices'], 1):
            status_symbol = "✅" if voice['status'] == 'success' else "❌"
            gender_cn = "男" if voice['gender'] == 'Male' else "女"

            if voice['audio_file']:
                audio_link = f"[播放]({voice['audio_file']})"
            else:
                audio_link = "生成失败"

            lines.append(
                f"| {i} | {status_symbol} | {voice['name']} | {gender_cn} | "
                f"{voice['language']} | {voice['friendly_name']} | {audio_link} |"
            )

        failed_voices = [v for v in data['voices'] if v['status'] == 'failed']
        if failed_voices:
            lines.append("\n---\n")
            lines.append("## 失败详情\n")
            lines.append("| 音色名称 | 错误信息 |")
            lines.append("|---------|---------|")

            for voice in failed_voices:
                error_msg = voice.get('error', '未知错误')
                lines.append(f"| {voice['name']} | {error_msg} |")

        content = "\n".join(lines)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

