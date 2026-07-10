import re
import json
from typing import List, Dict
from pathlib import Path

from loguru import logger
import config
from ga_birds.Common.i18n import t

EN_PERSONALITY_TAGS = {
    "personality": [
        "passionate", "calm", "impulsive", "rational", "kind", "evil",
        "brave", "timid", "confident", "inferior", "optimistic", "pessimistic",
        "cheerful", "introverted", "outgoing", "lonely", "gentle", "irritable"
    ],
    "speech": [
        "direct", "tactful", "loud", "soft", "fast", "slow",
        "humorous", "serious", "wordy", "concise", "rude", "polite",
        "sharp", "mild"
    ],
    "emotion": [
        "excited", "calm", "hot-tempered", "gentle", "anxious", "composed",
        "enthusiastic", "indifferent", "sensitive", "slow", "sentimental", "open-minded"
    ],
    "role": [
        "elder", "junior", "leader", "subordinate", "teacher", "student",
        "strict father", "kind mother", "wise", "foolish", "mentor", "apprentice"
    ],
    "other": [
        "traditional", "modern", "stubborn", "flexible", "cunning", "simple",
        "smooth", "straightforward", "snobbish", "upright", "kind", "strict",
        "careful", "reckless", "meticulous", "careless"
    ],
}

ZH_TO_EN_CATEGORY = {
    "性格": "personality",
    "说话": "speech",
    "情绪": "emotion",
    "角色": "role",
    "其他": "other",
}

ZH_TO_EN_PERSONALITY = {}
for zh_category, en_category in ZH_TO_EN_CATEGORY.items():
    for zh_tag, en_tag in zip(config.PERSONALITY_TAGS[zh_category], EN_PERSONALITY_TAGS[en_category]):
        ZH_TO_EN_PERSONALITY[zh_tag] = en_tag


class CharacterAnalyzer:

    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.all_characters = {}
        self.max_content_length = config.CHARACTER_MAX_CONTENT_LENGTH

    def _uses_english_metadata(self) -> bool:
        return str(config.LANGUAGE).lower().startswith("en")

    def _build_personality_hint(self) -> str:
        if self._uses_english_metadata():
            return "\n".join(
                f"{category}: {', '.join(tags[:8])}"
                for category, tags in EN_PERSONALITY_TAGS.items()
            )

        return "\n".join(
            f"{category}: {', '.join(tags[:8])}"
            for category, tags in config.PERSONALITY_TAGS.items()
        )

    @staticmethod
    def _dedupe_strings(values: List[str]) -> List[str]:
        result = []
        seen = set()
        for value in values:
            cleaned = str(value).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result

    @staticmethod
    def _normalize_simple_value(value: str, fallback: str = "unknown") -> str:
        cleaned = str(value or "").strip()
        return cleaned if cleaned else fallback

    @classmethod
    def _normalize_age_group(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        aliases = {
            "child": "child",
            "kid": "child",
            "children": "child",
            "儿童": "child",
            "小孩": "child",
            "teen": "teen",
            "teenager": "teen",
            "青少年": "teen",
            "adult": "adult",
            "成年人": "adult",
            "elder": "elder",
            "elderly": "elder",
            "old": "elder",
            "老年": "elder",
            "unknown": "unknown",
            "未知": "unknown",
        }
        return aliases.get(normalized, "unknown")

    @classmethod
    def _normalize_profile(cls, char: Dict) -> Dict:
        profile = char.get("profile", {}) if isinstance(char.get("profile"), dict) else {}
        region_hint = profile.get("region_hint", char.get("region_hint", "unknown"))
        accent_preference = profile.get("accent_preference", char.get("accent_preference", "unknown"))
        occupation = profile.get("occupation", char.get("occupation", "unknown"))
        age_group = profile.get("age_group", char.get("age_group", "unknown"))
        speech_style = cls._dedupe_strings(profile.get("speech_style", char.get("speech_style", [])))

        return {
            "age_group": cls._normalize_age_group(age_group),
            "occupation": cls._normalize_simple_value(occupation),
            "region_hint": cls._normalize_simple_value(region_hint),
            "accent_preference": cls._normalize_simple_value(accent_preference),
            "speech_style": speech_style,
        }

    @staticmethod
    def _merge_profile(existing: Dict, incoming: Dict) -> Dict:
        merged = dict(existing or {})
        incoming = incoming or {}
        for key in ("age_group", "occupation", "region_hint", "accent_preference"):
            current = str(merged.get(key, "unknown")).strip() or "unknown"
            candidate = str(incoming.get(key, "unknown")).strip() or "unknown"
            if current == "unknown" and candidate != "unknown":
                merged[key] = candidate

        merged["speech_style"] = list(set(merged.get("speech_style", [])) | set(incoming.get("speech_style", [])))
        return merged

    def _filter_aliases_by_source(self, aliases: List[str], source_text: str, primary_name: str) -> List[str]:
        return self._dedupe_strings(
            alias for alias in aliases
            if alias != primary_name and alias in source_text
        )

    def _normalize_personality_tags(self, tags: List[str]) -> List[str]:
        if not self._uses_english_metadata():
            return self._dedupe_strings(tags)

        return self._dedupe_strings([
            ZH_TO_EN_PERSONALITY.get(str(tag).strip(), str(tag).strip().lower())
            for tag in tags
            if str(tag).strip()
        ])

    def _normalize_auto_character(self, char: Dict, source_text: str) -> Dict:
        name = str(char.get('name', '')).strip()
        aliases = self._dedupe_strings(char.get('aliases', []))
        gender = str(char.get('gender', 'unknown')).strip().lower() or 'unknown'
        personality = self._normalize_personality_tags(char.get('personality', []))
        profile = self._normalize_profile(char)

        source_aliases = [alias for alias in aliases if alias in source_text]
        if name and name not in source_text and source_aliases:
            name = max(source_aliases, key=len)

        aliases = self._filter_aliases_by_source(aliases, source_text, name)

        return {
            'name': name,
            'aliases': aliases,
            'gender': gender,
            'personality': personality,
            'profile': profile,
        }

    def _normalize_hybrid_character(self, info: Dict, source_text: str) -> Dict:
        aliases = self._dedupe_strings(info.get('aliases', []))
        aliases = self._dedupe_strings(alias for alias in aliases if alias in source_text)
        personality = self._normalize_personality_tags(info.get('personality', []))
        profile = self._normalize_profile(info)
        return {
            'aliases': aliases,
            'personality': personality,
            'profile': profile,
        }

    def _build_auto_prompt(self, chapter_content: str) -> str:
        personality_hint = self._build_personality_hint()
        excerpt = chapter_content[:self.max_content_length]

        if self._uses_english_metadata():
            return f"""Analyze the following novel chapter and extract all characters that appear.

Requirements:
1. Extract only people or character names. Do not extract places or objects.
2. Identify aliases that actually appear in the source text for the same character.
3. Do not translate, localize, or invent names or aliases. Keep every name and alias exactly as it appears in the source text.
4. Infer gender as male / female / unknown.
5. Infer a concise profile for each character:
   - age_group: child / teen / adult / elder / unknown
   - occupation: short English noun phrase or unknown
   - region_hint: explicit region/nationality/accent clue from the text, otherwise unknown
   - accent_preference: standard / regional / unknown
   - speech_style: 1-3 English tags that describe how the character speaks
6. Provide 3-5 personality tags in English for each character, chosen from the following reference categories:
{personality_hint}
7. Return valid JSON only, with no extra explanation.

Chapter content:
{excerpt}

Return format (must be valid JSON):
{{
  "characters": [
    {{
      "name": "A",
      "aliases": [],
      "gender": "female",
      "personality": ["impulsive", "straightforward", "timid"],
      "profile": {{
        "age_group": "adult",
        "occupation": "office worker",
        "region_hint": "unknown",
        "accent_preference": "unknown",
        "speech_style": ["direct", "fast"]
      }}
    }},
    {{
      "name": "boss",
      "aliases": [],
      "gender": "male",
      "personality": ["strict", "serious", "direct"],
      "profile": {{
        "age_group": "adult",
        "occupation": "manager",
        "region_hint": "unknown",
        "accent_preference": "standard",
        "speech_style": ["firm", "concise"]
      }}
    }}
  ]
}}"""

        return f"""请分析以下小说章节，提取所有出现的角色名。

要求：
1. 只提取人物角色名，不要提取地名、物品名
2. 识别角色在原文中实际出现过的别名
3. 不要翻译、改写或臆造角色名和别名，必须保持原文里的写法
4. 尝试识别角色性别（male/female/unknown）
5. 为每个角色补充画像：
   - age_group：child / teen / adult / elder / unknown
   - occupation：简短职业描述，没有则填 unknown
   - region_hint：原文中明确出现的地域/国籍/口音线索，没有则填 unknown
   - accent_preference：standard / regional / unknown
   - speech_style：1-3 个说话风格标签
6. 为每个角色提取 3-5 个性格标签（personality）：从以下维度选择
{personality_hint}
7. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{excerpt}

返回格式（必须是有效的 JSON）：
{{
  "characters": [
    {{
      "name": "陈长生",
      "aliases": ["长生", "陈某"],
      "gender": "male",
      "personality": ["冷静", "理智", "善良"],
      "profile": {{
        "age_group": "adult",
        "occupation": "修行者",
        "region_hint": "unknown",
        "accent_preference": "unknown",
        "speech_style": ["简洁", "温和"]
      }}
    }},
    {{
      "name": "徐有容",
      "aliases": ["有容", "徐姑娘"],
      "gender": "female",
      "personality": ["高傲", "强大", "美丽"],
      "profile": {{
        "age_group": "adult",
        "occupation": "修行者",
        "region_hint": "unknown",
        "accent_preference": "unknown",
        "speech_style": ["冷静", "礼貌"]
      }}
    }}
  ]
}}"""

    def _build_hybrid_prompt(self, chapter_content: str, character_names: List[str]) -> str:
        personality_hint = self._build_personality_hint()
        excerpt = chapter_content[:self.max_content_length]
        character_list_str = ", ".join(character_names)

        if self._uses_english_metadata():
            return f"""Analyze the following chapter and find aliases and personality traits for the specified characters.

Known characters:
{character_list_str}

Requirements:
1. For each character, list aliases that actually appear in this chapter.
2. Do not translate, localize, or invent character names or aliases. Keep them exactly as they appear in the source text.
3. Infer or update the character profile:
   - age_group: child / teen / adult / elder / unknown
   - occupation: short English noun phrase or unknown
   - region_hint: explicit region/nationality/accent clue from the chapter, otherwise unknown
   - accent_preference: standard / regional / unknown
   - speech_style: 1-3 English tags that describe how the character speaks
4. Provide 3-5 personality tags in English for each character, chosen from the following reference categories:
{personality_hint}
5. If a character does not appear in this chapter, return empty lists and unknown profile fields.
6. Return valid JSON only, with no extra explanation.

Chapter content:
{excerpt}

Return format (must be valid JSON):
{{
  "boss": {{
    "aliases": [],
    "personality": ["strict", "serious", "direct"],
    "profile": {{
      "age_group": "adult",
      "occupation": "manager",
      "region_hint": "unknown",
      "accent_preference": "standard",
      "speech_style": ["firm", "concise"]
    }}
  }},
  "A": {{
    "aliases": [],
    "personality": ["impulsive", "straightforward", "timid"],
    "profile": {{
      "age_group": "adult",
      "occupation": "office worker",
      "region_hint": "unknown",
      "accent_preference": "unknown",
      "speech_style": ["direct", "fast"]
    }}
  }}
}}"""

        return f"""请分析以下章节内容，为指定的角色找出别名和性格特征。

已知角色列表：
{character_list_str}

要求：
1. 为每个角色找出在本章中实际出现过的别名
2. 不要翻译、改写或臆造角色名和别名，必须保持原文里的写法
3. 为每个角色补充画像：
   - age_group：child / teen / adult / elder / unknown
   - occupation：简短职业描述，没有则填 unknown
   - region_hint：原文中明确出现的地域/国籍/口音线索，没有则填 unknown
   - accent_preference：standard / regional / unknown
   - speech_style：1-3 个说话风格标签
4. 为每个角色提取 3-5 个性格标签（personality）：从以下维度选择
{personality_hint}
5. 如果某个角色在本章未出现，返回空列表与 unknown 画像
6. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{excerpt}

返回格式（必须是有效的 JSON）：
{{
  "陈洪德": {{
    "aliases": ["洪德", "小洪德"],
    "personality": ["善良", "勇敢", "热血"],
    "profile": {{
      "age_group": "adult",
      "occupation": "unknown",
      "region_hint": "unknown",
      "accent_preference": "unknown",
      "speech_style": ["直接", "热情"]
    }}
  }},
  "老爸": {{
    "aliases": ["父亲", "老子"],
    "personality": ["严厉", "关心", "传统"],
    "profile": {{
      "age_group": "adult",
      "occupation": "unknown",
      "region_hint": "unknown",
      "accent_preference": "standard",
      "speech_style": ["严肃", "简洁"]
    }}
  }}
}}"""

    def analyze_chapter(self, chapter_content: str, chapter_index: int) -> List[Dict]:
        prompt = self._build_auto_prompt(chapter_content)
        
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
                characters = [
                    self._normalize_auto_character(char, chapter_content)
                    for char in data.get('characters', [])
                    if str(char.get('name', '')).strip() or char.get('aliases')
                ]
                characters = [char for char in characters if char['name']]
                
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
                self.all_characters[name]['profile'] = self._merge_profile(
                    self.all_characters[name].get('profile', {}),
                    char.get('profile', {}),
                )
            else:
                self.all_characters[name] = {
                    'name': name,
                    'aliases': char.get('aliases', []),
                    'gender': char.get('gender', 'unknown'),
                    'personality': char.get('personality', []),
                    'profile': char.get('profile', self._normalize_profile({})),
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
        prompt = self._build_hybrid_prompt(chapter_content, character_names)

        try:
            result = self.llm_manager.generate(prompt)
            logger.debug(t("character.llm_response_length", length=len(result)))

            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)

                data = {
                    char_name: self._normalize_hybrid_character(info, chapter_content)
                    for char_name, info in json.loads(json_str).items()
                    if isinstance(info, dict)
                }
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

