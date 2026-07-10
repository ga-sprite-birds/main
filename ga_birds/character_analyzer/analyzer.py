import re
import json
from typing import List, Dict, Set
from pathlib import Path

from loguru import logger
import config
from ga_birds.Common.i18n import t


class CharacterAnalyzer:

    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.all_characters = {}
        self.max_content_length = config.CHARACTER_MAX_CONTENT_LENGTH
    
    def analyze_chapter(self, chapter_content: str, chapter_index: int) -> List[Dict]:
        # Build personality tag hints
        personality_examples = []
        for category, tags in config.PERSONALITY_TAGS.items():
            personality_examples.append(f"{category}: {', '.join(tags[:8])}")
        personality_hint = "\n".join(personality_examples)

        prompt = f"""请分析以下小说章节，提取所有出现的角色名。

要求：
1. 只提取人物角色名，不要提取地名、物品名
2. 识别角色的别名（如"张三"、"小张"、"张公子"是同一人）
3. 尝试识别角色性别（male/female/unknown）
4. 为每个角色提取 3-5 个性格标签（personality）：从以下维度选择
{personality_hint}
5. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{chapter_content[:self.max_content_length]}

返回格式（必须是有效的 JSON）：
{{
  "characters": [
    {{"name": "陈长生", "aliases": ["长生", "陈某"], "gender": "male", "personality": ["冷静", "理智", "善良"]}},
    {{"name": "徐有容", "aliases": ["有容", "徐姑娘"], "gender": "female", "personality": ["高傲", "强大", "美丽"]}}
  ]
}}"""
        
        try:
            result = self.llm_manager.generate(prompt)
            logger.debug(t("character.llm_response_length", length=len(result)))
            
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                data = json.loads(json_str)
                characters = data.get('characters', [])
                
                logger.info(t("character.chapter_characters_found", index=chapter_index, count=len(characters)))
                return characters
            else:
                logger.warning(t("character.chapter_llm_format_error", index=chapter_index))
                return []
                
        except json.JSONDecodeError as e:
            logger.error(t("character.chapter_json_parse_failed", index=chapter_index, error=e))
            return []
        except Exception as e:
            logger.error(t("character.chapter_analyze_failed", index=chapter_index, error=e))
            return []
    
    def merge_characters(self, chapter_characters: List[Dict], chapter_index: int):
        for char in chapter_characters:
            name = char.get('name', '')
            if not name:
                continue

            if name in self.all_characters:
                self.all_characters[name]['appearance_count'] += 1
                self.all_characters[name]['last_chapter'] = chapter_index

                # Merge aliases
                existing_aliases = set(self.all_characters[name].get('aliases', []))
                new_aliases = set(char.get('aliases', []))
                self.all_characters[name]['aliases'] = list(existing_aliases | new_aliases)

                # Merge personality tags
                existing_personality = set(self.all_characters[name].get('personality', []))
                new_personality = set(char.get('personality', []))
                self.all_characters[name]['personality'] = list(existing_personality | new_personality)
            else:
                self.all_characters[name] = {
                    'name': name,
                    'aliases': char.get('aliases', []),
                    'gender': char.get('gender', 'unknown'),
                    'personality': char.get('personality', []),
                    'appearance_count': 1,
                    'first_chapter': chapter_index,
                    'last_chapter': chapter_index
                }
    
    def get_all_characters(self) -> List[Dict]:
        return sorted(
            self.all_characters.values(),
            key=lambda x: x['appearance_count'],
            reverse=True
        )
    
    def analyze_chapter_for_characters(
        self,
        chapter_content: str,
        chapter_index: int,
        character_names: List[str]
    ) -> Dict[str, Dict]:
        """
        Analyze aliases and personality for specified characters (hybrid mode)

        Args:
            chapter_content: chapter content
            chapter_index: chapter index
            character_names: list of specified character names

        Returns:
            character info dict: {character_name: {aliases: [...], personality: [...]}}
        """
        # Build personality tag hints
        personality_examples = []
        for category, tags in config.PERSONALITY_TAGS.items():
            personality_examples.append(f"{category}: {', '.join(tags[:8])}")
        personality_hint = "\n".join(personality_examples)

        # Build character list
        character_list_str = ", ".join(character_names)

        prompt = f"""请分析以下章节内容，为指定的角色找出别名和性格特征。

已知角色列表：
{character_list_str}

要求：
1. 为每个角色找出在本章中出现的别名（如"张三"可能被称为"小张"、"张公子"）
2. 为每个角色提取 3-5 个性格标签（personality）：从以下维度选择
{personality_hint}
3. 如果某个角色在本章未出现，返回空列表
4. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{chapter_content[:self.max_content_length]}

返回格式（必须是有效的 JSON）：
{{
  "陈洪德": {{
    "aliases": ["洪德", "小洪德"],
    "personality": ["善良", "勇敢", "热血"]
  }},
  "老爸": {{
    "aliases": ["父亲", "老子"],
    "personality": ["严厉", "关心", "传统"]
  }}
}}"""

        try:
            result = self.llm_manager.generate(prompt)
            logger.debug(t("character.llm_response_length", length=len(result)))

            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)

                data = json.loads(json_str)
                logger.info(t("character.chapter_hybrid_found", index=chapter_index, count=len(data)))
                return data
            else:
                logger.warning(t("character.chapter_llm_format_error", index=chapter_index))
                return {}

        except json.JSONDecodeError as e:
            logger.error(t("character.chapter_json_parse_failed", index=chapter_index, error=e))
            return {}
        except Exception as e:
            logger.error(t("character.chapter_analyze_failed", index=chapter_index, error=e))
            return {}

    def save_to_json(self, output_path: Path, novel_id: str, novel_title: str):
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'novel_id': novel_id,
            'novel_title': novel_title,
            'total_characters': len(self.all_characters),
            'characters': self.get_all_characters()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(t("character.data_saved", path=output_path))

