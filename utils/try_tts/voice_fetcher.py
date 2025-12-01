"""
音色列表获取器
从 Edge TTS API 获取可用音色列表并支持筛选
"""

import asyncio
from typing import List, Dict, Optional
import edge_tts


class VoiceFetcher:
    """音色列表获取器"""
    
    def __init__(self):
        """初始化音色获取器"""
        self.voices = []
    
    async def fetch_voices(self) -> List[Dict]:
        """
        从 Edge TTS API 获取所有可用音色
        
        Returns:
            音色列表
        """
        self.voices = await edge_tts.list_voices()
        return self.voices
    
    def filter_voices(
        self,
        language: Optional[str] = None,
        gender: Optional[str] = None
    ) -> List[Dict]:
        """
        筛选音色列表
        
        Args:
            language: 语言代码（如 zh-CN, en-US），None 表示全部
            gender: 性别（male/female），None 表示全部
            
        Returns:
            筛选后的音色列表
        """
        filtered = self.voices
        
        if language:
            language_lower = language.lower()
            filtered = [
                v for v in filtered
                if v.get('Locale', '').lower().startswith(language_lower)
            ]
        
        if gender:
            gender_map = {
                'male': 'Male',
                'female': 'Female',
                '1': 'Male',
                '0': 'Female'
            }
            target_gender = gender_map.get(gender.lower(), gender)
            filtered = [
                v for v in filtered
                if v.get('Gender', '') == target_gender
            ]
        
        return filtered
    
    @staticmethod
    def format_voice_info(voice: Dict) -> str:
        """
        格式化单个音色信息为可读字符串
        
        Args:
            voice: 音色数据
            
        Returns:
            格式化后的字符串
        """
        name = voice.get('ShortName', 'Unknown')
        gender = voice.get('Gender', 'Unknown')
        locale = voice.get('Locale', 'Unknown')
        friendly_name = voice.get('FriendlyName', 'Unknown')
        
        gender_symbol = '♂' if gender == 'Male' else '♀'
        
        return f"{gender_symbol} {name:35s} | {locale:8s} | {friendly_name}"
    
    @staticmethod
    def format_voice_list(voices: List[Dict]) -> str:
        """
        格式化音色列表为表格形式
        
        Args:
            voices: 音色列表
            
        Returns:
            格式化后的表格字符串
        """
        if not voices:
            return "未找到匹配的音色"
        
        lines = []
        lines.append("=" * 100)
        lines.append(f"共找到 {len(voices)} 个音色")
        lines.append("=" * 100)
        lines.append(f"{'性别'} {'音色名称':35s} | {'语言':8s} | 友好名称")
        lines.append("-" * 100)
        
        for voice in voices:
            lines.append(VoiceFetcher.format_voice_info(voice))
        
        lines.append("=" * 100)
        
        return "\n".join(lines)
    
    def get_voices_sync(self) -> List[Dict]:
        """
        同步方式获取音色列表
        
        Returns:
            音色列表
        """
        return asyncio.run(self.fetch_voices())

