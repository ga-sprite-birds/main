"""
Voice list fetcher
Fetches the available voice list from the Edge TTS API and supports filtering
"""

import asyncio
from typing import List, Dict, Optional
import edge_tts
from utils.try_tts.i18n import t


class VoiceFetcher:
    """Voice list fetcher"""
    
    def __init__(self):
        """Initialize the voice fetcher"""
        self.voices = []
    
    async def fetch_voices(self) -> List[Dict]:
        """
        Fetch all available voices from the Edge TTS API
        
        Returns:
            voice list
        """
        self.voices = await edge_tts.list_voices()
        return self.voices
    
    def filter_voices(
        self,
        language: Optional[str] = None,
        gender: Optional[str] = None
    ) -> List[Dict]:
        """
        Filter the voice list
        
        Args:
            language: language code (e.g. zh-CN, en-US); None means all
            gender: gender (male/female); None means all
            
        Returns:
            filtered voice list
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
        Format a single voice's info into a readable string
        
        Args:
            voice: voice data
            
        Returns:
            formatted string
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
        Format the voice list as a table

        Args:
            voices: voice list

        Returns:
            formatted table string
        """
        if not voices:
            return t('no_voices_found')

        lines = []
        lines.append("=" * 100)
        lines.append(t('voice_count_found', count=len(voices)))
        lines.append("=" * 100)
        lines.append(t('voice_table_header'))
        lines.append("-" * 100)
        
        for voice in voices:
            lines.append(VoiceFetcher.format_voice_info(voice))
        
        lines.append("=" * 100)
        
        return "\n".join(lines)
    
    def get_voices_sync(self) -> List[Dict]:
        """
        Fetch the voice list synchronously
        
        Returns:
            voice list
        """
        return asyncio.run(self.fetch_voices())

