"""
Character merger
Uses an LLM to automatically detect and merge duplicate characters
"""

import json
from typing import List, Dict, Set
from loguru import logger
import config


class CharacterMerger:
    """Character merger - automatically detects and merges duplicate characters"""

    def __init__(self, llm_manager):
        self.llm_manager = llm_manager

    def merge_duplicate_characters(
        self,
        characters: List[Dict]
    ) -> List[Dict]:
        """
        Automatically detect and merge duplicate characters

        Args:
            characters: character list

        Returns:
            merged character list
        """
        if len(characters) <= 1:
            return characters

        logger.info("开始分析重复角色...")

        # Build the character list string
        character_list = []
        for i, char in enumerate(characters):
            character_list.append(
                f"{i+1}. {char['name']} "
                f"(别名: {', '.join(char.get('aliases', [])[:3])}, "
                f"性别: {char.get('gender', 'unknown')}, "
                f"出现: {char.get('appearance_count', 0)}次)"
            )

        character_list_str = "\n".join(character_list)

        # Build the LLM prompt
        prompt = f"""请分析以下角色列表，识别可能是同一个人的重复角色。

角色列表：
{character_list_str}

要求：
1. 识别可能是同一个人的角色（如"洪德"和"陈洪德"、"老爸"和"父亲"）
2. 对于每组重复角色，选择最完整的名字作为主名称
3. 返回合并建议的 JSON 格式

返回格式（必须是有效的 JSON）：
{{
  "merge_groups": [
    {{
      "primary_name": "陈洪德",
      "duplicate_names": ["洪德", "小洪德"],
      "reason": "都是指同一个人，陈洪德是完整名字"
    }},
    {{
      "primary_name": "老爸",
      "duplicate_names": ["父亲"],
      "reason": "都是指陈洪德的父亲"
    }}
  ]
}}

如果没有重复角色，返回：
{{
  "merge_groups": []
}}
"""

        try:
            # Call the LLM
            response = self.llm_manager.generate(prompt)

            # Parse the JSON
            merge_data = self._extract_json(response)

            if not merge_data or 'merge_groups' not in merge_data:
                logger.warning("LLM 未返回有效的合并建议")
                return characters

            merge_groups = merge_data['merge_groups']

            if not merge_groups:
                logger.info("✓ 未发现重复角色")
                return characters

            # Perform the merge
            logger.info(f"发现 {len(merge_groups)} 组重复角色，开始合并...")
            merged_characters = self._apply_merge(
                characters,
                merge_groups
            )

            logger.info(
                f"✓ 合并完成：{len(characters)} 个角色 → "
                f"{len(merged_characters)} 个角色"
            )

            return merged_characters

        except Exception as e:
            logger.error(f"角色合并失败: {e}")
            return characters

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from the LLM response"""
        try:
            # Try to parse directly
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract a JSON code block
            import re
            json_match = re.search(
                r'```(?:json)?\s*(\{.*?\})\s*```',
                text,
                re.DOTALL
            )
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find the first JSON object
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

            return {}

    def _apply_merge(
        self,
        characters: List[Dict],
        merge_groups: List[Dict]
    ) -> List[Dict]:
        """
        Apply the merge suggestions

        Args:
            characters: original character list
            merge_groups: list of merge groups

        Returns:
            merged character list
        """
        # Create a mapping from character name to character object
        char_map = {char['name']: char for char in characters}

        # Record character names to remove
        to_remove = set()

        # Process each merge group
        for group in merge_groups:
            primary_name = group.get('primary_name')
            duplicate_names = group.get('duplicate_names', [])
            reason = group.get('reason', '')

            if not primary_name or not duplicate_names:
                continue

            # Check whether the primary name exists
            if primary_name not in char_map:
                logger.warning(
                    f"主名称 '{primary_name}' 不存在，跳过合并"
                )
                continue

            logger.info(
                f"  合并: {', '.join(duplicate_names)} → {primary_name}"
            )
            logger.info(f"    原因: {reason}")

            primary_char = char_map[primary_name]

            # Merge each duplicate character
            for dup_name in duplicate_names:
                if dup_name not in char_map:
                    continue

                dup_char = char_map[dup_name]

                # Merge aliases
                primary_aliases = set(primary_char.get('aliases', []))
                dup_aliases = set(dup_char.get('aliases', []))
                primary_char['aliases'] = list(
                    primary_aliases | dup_aliases | {dup_name}
                )

                # Merge personality tags
                primary_personality = set(
                    primary_char.get('personality', [])
                )
                dup_personality = set(dup_char.get('personality', []))
                primary_char['personality'] = list(
                    primary_personality | dup_personality
                )

                # Accumulate appearance counts
                primary_char['appearance_count'] = (
                    primary_char.get('appearance_count', 0) +
                    dup_char.get('appearance_count', 0)
                )

                # Update first appearance chapter (take the minimum)
                if dup_char.get('first_chapter'):
                    if not primary_char.get('first_chapter'):
                        primary_char['first_chapter'] = (
                            dup_char['first_chapter']
                        )
                    else:
                        primary_char['first_chapter'] = min(
                            primary_char['first_chapter'],
                            dup_char['first_chapter']
                        )

                # Update last appearance chapter (take the maximum)
                if dup_char.get('last_chapter'):
                    if not primary_char.get('last_chapter'):
                        primary_char['last_chapter'] = (
                            dup_char['last_chapter']
                        )
                    else:
                        primary_char['last_chapter'] = max(
                            primary_char['last_chapter'],
                            dup_char['last_chapter']
                        )

                # Mark as pending removal
                to_remove.add(dup_name)

        # Return characters that were not removed
        return [
            char for char in characters
            if char['name'] not in to_remove
        ]

