"""
角色音色分配器
根据角色性别自动分配音色
"""

from typing import Dict, List
from loguru import logger


class VoiceAssigner:
    """角色音色分配器"""
    
    # 预定义的音色池
    MALE_VOICES = [
        "zh-CN-YunxiNeural",      # 男声1
        "zh-CN-YunjianNeural",    # 男声2
        "zh-CN-YunyangNeural",    # 男声3
        "zh-CN-YunzeNeural",      # 男声4
    ]
    
    FEMALE_VOICES = [
        "zh-CN-XiaoxiaoNeural",   # 女声1
        "zh-CN-XiaoyiNeural",     # 女声2
        "zh-CN-XiaochenNeural",   # 女声3
        "zh-CN-XiaohanNeural",    # 女声4
    ]
    
    NARRATOR_VOICE = "zh-CN-XiaoxiaoNeural"  # 旁白默认使用女声
    
    def __init__(self):
        """初始化音色分配器"""
        self.male_index = 0
        self.female_index = 0
        logger.info("音色分配器初始化完成")
    
    def assign_voices(self, characters: List[Dict]) -> List[Dict]:
        """
        为角色列表分配音色
        
        Args:
            characters: 角色列表（从 CharacterAnalyzer 生成）
            
        Returns:
            添加了 voice 字段的角色列表
        """
        for char in characters:
            gender = char.get('gender', 'unknown')
            
            # 如果已经有 voice 字段（用户手动设置），跳过
            if 'voice' in char and char['voice']:
                logger.info(f"角色 {char['name']} 已有音色: {char['voice']}")
                continue
            
            # 根据性别分配音色
            if gender == 'male':
                char['voice'] = self._get_male_voice()
                logger.info(f"角色 {char['name']} (男) 分配音色: {char['voice']}")
            elif gender == 'female':
                char['voice'] = self._get_female_voice()
                logger.info(f"角色 {char['name']} (女) 分配音色: {char['voice']}")
            else:
                # 性别未知，默认使用男声
                char['voice'] = self._get_male_voice()
                logger.info(f"角色 {char['name']} (未知) 分配音色: {char['voice']}")
        
        return characters
    
    def _get_male_voice(self) -> str:
        """获取下一个男声音色（循环使用）"""
        voice = self.MALE_VOICES[self.male_index % len(self.MALE_VOICES)]
        self.male_index += 1
        return voice
    
    def _get_female_voice(self) -> str:
        """获取下一个女声音色（循环使用）"""
        voice = self.FEMALE_VOICES[self.female_index % len(self.FEMALE_VOICES)]
        self.female_index += 1
        return voice
    
    @staticmethod
    def create_character_template(characters: List[Dict], novel_id: str, novel_title: str) -> Dict:
        """
        创建角色配音模板

        Args:
            characters: 角色列表（已分配音色）
            novel_id: 小说ID
            novel_title: 小说标题

        Returns:
            角色配音模板（JSON 格式）
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
        获取说话人的音色
        
        Args:
            speaker: 说话人名称（或 "narrator"）
            character_template: 角色配音模板
            
        Returns:
            音色名称
        """
        if speaker == "narrator":
            return character_template.get('narrator', {}).get('voice', VoiceAssigner.NARRATOR_VOICE)
        
        # 查找角色
        for char in character_template.get('characters', []):
            if speaker == char['name']:
                return char.get('voice', VoiceAssigner.NARRATOR_VOICE)
        
        # 未找到，使用旁白音色
        logger.warning(f"未找到角色 {speaker} 的音色，使用旁白音色")
        return character_template.get('narrator', {}).get('voice', VoiceAssigner.NARRATOR_VOICE)

