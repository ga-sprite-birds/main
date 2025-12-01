"""
试听音频生成器
为指定音色生成试听音频文件
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import edge_tts

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.try_tts.i18n import t
from ga_birds.Utils import get_unique_filename


class SampleGenerator:
    """试听音频生成器"""
    
    DEFAULT_TEXT = "你好，我是微软语音合成服务。这是一段试听音频，用于测试音色效果。"
    
    def __init__(self, output_dir: str = "./output/tts_samples"):
        """
        初始化试听音频生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_sample(
        self,
        voice: str,
        text: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz"
    ) -> str:
        """
        为单个音色生成试听音频

        Args:
            voice: 音色名称（如 zh-CN-XiaoxiaoNeural）
            text: 试听文本（None 则使用默认文本）
            rate: 语速（如 "+0%"）
            volume: 音量（如 "+0%"）
            pitch: 音调（如 "+0Hz"）

        Returns:
            生成的音频文件路径
        """
        text = text or self.DEFAULT_TEXT

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
        批量生成试听音频

        Args:
            voices: 音色列表（从 VoiceFetcher 获取）
            text: 试听文本（None 则使用默认文本）
            show_progress: 是否显示进度
            language: 筛选的语言（用于保存记录）
            gender: 筛选的性别（用于保存记录）

        Returns:
            生成结果（包含 code, msg, data）
        """
        text = text or self.DEFAULT_TEXT
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
                output_file = await self.generate_sample(voice_name, text)
                voice_result["audio_file"] = output_file
                voice_result["status"] = "success"

                if show_progress:
                    print(f"  ✓ {t('saved')}: {output_file}")
            except Exception as e:
                if show_progress:
                    print(f"  ⚠ {t('retry')}")

                await asyncio.sleep(3)

                try:
                    output_file = await self.generate_sample(voice_name, text)
                    voice_result["audio_file"] = output_file
                    voice_result["status"] = "success"

                    if show_progress:
                        print(f"  ✓ {t('retry_success')}: {output_file}")
                except Exception as retry_error:
                    voice_result["error"] = str(retry_error)
                    if show_progress:
                        print(f"  ✗ {t('failed')}: {retry_error}")

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
        text: Optional[str] = None
    ) -> str:
        """
        同步方式生成单个试听音频
        
        Args:
            voice: 音色名称
            text: 试听文本
            
        Returns:
            生成的音频文件路径
        """
        return asyncio.run(self.generate_sample(voice, text))
    
    def generate_batch_sync(
        self,
        voices: List[Dict],
        text: Optional[str] = None,
        show_progress: bool = True,
        language: str = "全部",
        gender: str = "全部"
    ) -> Dict:
        """
        同步方式批量生成试听音频

        Args:
            voices: 音色列表
            text: 试听文本
            show_progress: 是否显示进度
            language: 筛选的语言
            gender: 筛选的性别

        Returns:
            生成结果（包含 code, msg, data）
        """
        return asyncio.run(
            self.generate_batch(voices, text, show_progress, language, gender)
        )

    def _save_results(self, result: Dict):
        """
        保存生成结果为 JSON 和 Markdown 文件

        Args:
            result: 生成结果
        """
        json_file = self.output_dir / "voices.json"
        md_file = self.output_dir / "voices.md"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self._save_markdown(result, md_file)

    def _save_markdown(self, result: Dict, output_path: Path):
        """
        保存结果为 Markdown 格式

        Args:
            result: 生成结果
            output_path: 输出文件路径
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

