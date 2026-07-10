"""
Document exporter
Exports the voice list to a Markdown document
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime


class DocExporter:
    """Document exporter"""
    
    @staticmethod
    def export_to_markdown(
        voices: List[Dict],
        output_path: str,
        language: str = "全部",
        gender: str = "全部"
    ) -> str:
        """
        Export the voice list to a Markdown document
        
        Args:
            voices: voice list
            output_path: output file path
            language: filtered language (used in the document title)
            gender: filtered gender (used in the document title)
            
        Returns:
            output file path
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        lines = []
        
        lines.append("# Edge TTS 可用音色列表\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**筛选条件**: 语言={language}, 性别={gender}\n")
        lines.append(f"**音色总数**: {len(voices)}\n")
        lines.append("---\n")
        
        lines.append("## 音色列表\n")
        lines.append("| 序号 | 性别 | 音色名称 | 语言 | 友好名称 |")
        lines.append("|------|------|----------|------|----------|")
        
        for i, voice in enumerate(voices, 1):
            name = voice.get('ShortName', 'Unknown')
            gender_raw = voice.get('Gender', 'Unknown')
            locale = voice.get('Locale', 'Unknown')
            friendly_name = voice.get('FriendlyName', 'Unknown')
            
            gender_symbol = '♂ 男' if gender_raw == 'Male' else '♀ 女'
            
            lines.append(f"| {i} | {gender_symbol} | `{name}` | {locale} | {friendly_name} |")
        
        lines.append("\n---\n")
        lines.append("## 使用说明\n")
        lines.append("在 `.env` 配置文件中设置 `TTS_VOICE` 参数：\n")
        lines.append("```env")
        lines.append("TTS_VOICE=zh-CN-XiaoxiaoNeural")
        lines.append("```\n")
        lines.append("或在命令行中使用 `--voice` 参数指定音色。\n")
        
        content = "\n".join(lines)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(output_file)
    
    @staticmethod
    def export_voice_names(
        voices: List[Dict],
        output_path: str
    ) -> str:
        """
        Export the voice name list (plain text, one per line)
        
        Args:
            voices: voice list
            output_path: output file path
            
        Returns:
            output file path
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        voice_names = [v.get('ShortName', '') for v in voices]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(voice_names))
        
        return str(output_file)

