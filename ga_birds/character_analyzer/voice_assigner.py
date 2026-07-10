"""
Character voice assigner
Automatically assigns voices based on character gender
"""

from typing import Dict, List
from loguru import logger


class VoiceAssigner:
    """Character voice assigner"""

    # Predefined voice pool
    MALE_VOICES = [
        "zh-CN-YunxiNeural",      # male voice 1
        "zh-CN-YunjianNeural",    # male voice 2
        "zh-CN-YunyangNeural",    # male voice 3
        "zh-CN-YunzeNeural",      # male voice 4
    ]

    FEMALE_VOICES = [
        "zh-CN-XiaoxiaoNeural",   # female voice 1
        "zh-CN-XiaoyiNeural",     # female voice 2
        "zh-CN-XiaochenNeural",   # female voice 3
        "zh-CN-XiaohanNeural",    # female voice 4
    ]

    NARRATOR_VOICE = "zh-CN-XiaoxiaoNeural"  # narrator uses female voice by default

    def __init__(self):
        """Initialize the voice assigner"""
        self.male_index = 0
        self.female_index = 0
        logger.info("音色分配器初始化完成")
    
    def assign_voices(self, characters: List[Dict]) -> List[Dict]:
        """
        Assign voices to the character list

        Args:
            characters: character list (generated from CharacterAnalyzer)

        Returns:
            character list with the voice field added
        """
        for char in characters:
            gender = char.get('gender', 'unknown')

            # If the voice field already exists (manually set by user), skip
            if 'voice' in char and char['voice']:
                logger.info(f"角色 {char['name']} 已有音色: {char['voice']}")
                continue

            # Assign voice based on gender
            if gender == 'male':
                char['voice'] = self._get_male_voice()
                logger.info(f"角色 {char['name']} (男) 分配音色: {char['voice']}")
            elif gender == 'female':
                char['voice'] = self._get_female_voice()
                logger.info(f"角色 {char['name']} (女) 分配音色: {char['voice']}")
            else:
                # Unknown gender, default to male voice
                char['voice'] = self._get_male_voice()
                logger.info(f"角色 {char['name']} (未知) 分配音色: {char['voice']}")

        return characters

    def _get_male_voice(self) -> str:
        """Get the next male voice (cycling)"""
        voice = self.MALE_VOICES[self.male_index % len(self.MALE_VOICES)]
        self.male_index += 1
        return voice
    
    def _get_female_voice(self) -> str:
        """Get the next female voice (cycling)"""
        voice = self.FEMALE_VOICES[self.female_index % len(self.FEMALE_VOICES)]
        self.female_index += 1
        return voice
    
    @staticmethod
    def create_character_template(characters: List[Dict], novel_id: str, novel_title: str) -> Dict:
        """
        Create the character voice cast template

        Args:
            characters: character list (voices already assigned)
            novel_id: novel ID
            novel_title: novel title

        Returns:
            character voice cast template (JSON format)
        """
        return {
            "novel_id": novel_id,
            "novel_title": novel_title,
            "total_characters": len(characters),
            "characters": [
                {
                    "name": char['name'],
                    "aliases": char.get('aliases', []),
                    "gender": char.get('gender', 'unknown'),
                    "voice": char.get('voice', VoiceAssigner.NARRATOR_VOICE),
                    "description": char.get('description', ''),
                    "personality": char.get('personality', []),
                    "appearance_count": char.get('appearance_count', 0),
                    "first_chapter": char.get('first_chapter', 0),
                    "last_chapter": char.get('last_chapter', 0)
                }
                for char in characters
            ],
            "narrator": {
                "name": "旁白",
                "voice": VoiceAssigner.NARRATOR_VOICE,
                "personality": ["客观", "平静"]
            }
        }
    
    @staticmethod
    def get_voice_for_speaker(speaker: str, character_template: Dict) -> str:
        """
        Get the voice for a speaker

        Args:
            speaker: speaker name (or "narrator")
            character_template: character voice cast template

        Returns:
            voice name
        """
        if speaker == "narrator":
            return character_template.get('narrator', {}).get('voice', VoiceAssigner.NARRATOR_VOICE)

        # Look up the character
        for char in character_template.get('characters', []):
            if speaker == char['name']:
                return char.get('voice', VoiceAssigner.NARRATOR_VOICE)

        # Not found, use the narrator voice
        logger.warning(f"未找到角色 {speaker} 的音色，使用旁白音色")
        return character_template.get('narrator', {}).get('voice', VoiceAssigner.NARRATOR_VOICE)

