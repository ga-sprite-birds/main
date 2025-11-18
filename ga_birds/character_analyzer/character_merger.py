"""
角色合并器
使用 LLM 自动识别并合并重复的角色
"""

import json
from typing import List, Dict, Set
from loguru import logger
import config


class CharacterMerger:
    """角色合并器 - 自动识别并合并重复角色"""

    def __init__(self, llm_manager):
        self.llm_manager = llm_manager

    def merge_duplicate_characters(
        self,
        characters: List[Dict]
    ) -> List[Dict]:
        """
        自动识别并合并重复角色

        Args:
            characters: 角色列表

        Returns:
            合并后的角色列表
        """
        if len(characters) <= 1:
            return characters

        logger.info("开始分析重复角色...")

        # 构建角色列表字符串
        character_list = []
        for i, char in enumerate(characters):
            character_list.append(
                f"{i+1}. {char['name']} "
                f"(别名: {', '.join(char.get('aliases', [])[:3])}, "
                f"性别: {char.get('gender', 'unknown')}, "
                f"出现: {char.get('appearance_count', 0)}次)"
            )

        character_list_str = "\n".join(character_list)

        # 构建 LLM Prompt
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
            # 调用 LLM
            response = self.llm_manager.generate(prompt)

            # 解析 JSON
            merge_data = self._extract_json(response)

            if not merge_data or 'merge_groups' not in merge_data:
                logger.warning("LLM 未返回有效的合并建议")
                return characters

            merge_groups = merge_data['merge_groups']

            if not merge_groups:
                logger.info("✓ 未发现重复角色")
                return characters

            # 执行合并
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
        """从 LLM 响应中提取 JSON"""
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 代码块
            import re
            json_match = re.search(
                r'```(?:json)?\s*(\{.*?\})\s*```',
                text,
                re.DOTALL
            )
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试查找第一个 JSON 对象
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
        应用合并建议

        Args:
            characters: 原始角色列表
            merge_groups: 合并组列表

        Returns:
            合并后的角色列表
        """
        # 创建角色名到角色对象的映射
        char_map = {char['name']: char for char in characters}

        # 记录要删除的角色名
        to_remove = set()

        # 处理每个合并组
        for group in merge_groups:
            primary_name = group.get('primary_name')
            duplicate_names = group.get('duplicate_names', [])
            reason = group.get('reason', '')

            if not primary_name or not duplicate_names:
                continue

            # 检查主名称是否存在
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

            # 合并每个重复角色
            for dup_name in duplicate_names:
                if dup_name not in char_map:
                    continue

                dup_char = char_map[dup_name]

                # 合并别名
                primary_aliases = set(primary_char.get('aliases', []))
                dup_aliases = set(dup_char.get('aliases', []))
                primary_char['aliases'] = list(
                    primary_aliases | dup_aliases | {dup_name}
                )

                # 合并性格标签
                primary_personality = set(
                    primary_char.get('personality', [])
                )
                dup_personality = set(dup_char.get('personality', []))
                primary_char['personality'] = list(
                    primary_personality | dup_personality
                )

                # 累加出现次数
                primary_char['appearance_count'] = (
                    primary_char.get('appearance_count', 0) +
                    dup_char.get('appearance_count', 0)
                )

                # 更新首次出现章节（取最小值）
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

                # 更新最后出现章节（取最大值）
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

                # 标记为待删除
                to_remove.add(dup_name)

        # 返回未被删除的角色
        return [
            char for char in characters
            if char['name'] not in to_remove
        ]

