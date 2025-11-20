"""
对话解析器
使用 LLM 识别章节中每句话的说话人
"""

import re
import json
from typing import List, Dict
from loguru import logger


class DialogueParser:
    """对话解析器"""
    
    def __init__(self, llm_manager, characters: List[Dict]):
        """
        初始化对话解析器
        
        Args:
            llm_manager: LLM 管理器
            characters: 角色列表（从角色模板加载）
        """
        self.llm_manager = llm_manager
        self.characters = characters
        
        # 构建角色名称列表（包括别名）
        self.character_names = set()
        for char in characters:
            self.character_names.add(char['name'])
            for alias in char.get('aliases', []):
                self.character_names.add(alias)
        
        logger.info(f"对话解析器初始化完成，已知角色: {len(characters)} 个")
    
    def parse_chapter(self, chapter_content: str, chapter_index: int) -> List[Dict]:
        """
        解析章节内容，识别每句话的说话人
        
        Args:
            chapter_content: 章节内容
            chapter_index: 章节索引
            
        Returns:
            对话片段列表，格式：
            [
                {"text": "二叔走了过来，说：", "speaker": "narrator"},
                {"text": "你去哪里？", "speaker": "二叔"},
                ...
            ]
        """
        # 构建角色名称字符串
        character_names_str = "、".join([c['name'] for c in self.characters])
        
        prompt = f"""请分析以下小说章节，将内容拆分为对话片段，并识别每个片段的说话人。

已知角色：{character_names_str}

要求：
1. 将内容拆分为多个片段（对话、旁白、描述等）
2. 识别每个片段的说话人（角色名或 "narrator" 表示旁白）
3. 保持原文内容完整，不要修改文字
4. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{chapter_content[:4000]}

返回格式（必须是有效的 JSON）：
{{
  "segments": [
    {{"text": "二叔走了过来，说：", "speaker": "narrator"}},
    {{"text": "你去哪里？", "speaker": "二叔"}},
    {{"text": "老爸回答：", "speaker": "narrator"}},
    {{"text": "我去买菜。", "speaker": "老爸"}},
    {{"text": "他们一起离开了。", "speaker": "narrator"}}
  ]
}}"""
        
        try:
            result = self.llm_manager.generate(prompt)
            logger.debug(f"LLM 返回内容长度: {len(result)} 字符")

            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)

                # 清理 JSON
                json_str = json_str.replace('\n', ' ').replace('\r', '')

                # 修复各种引号问题
                json_str = json_str.replace('\u201c', '\\"')  # " 左双引号
                json_str = json_str.replace('\u201d', '\\"')  # " 右双引号
                json_str = json_str.replace('\u2018', "'")    # ' 左单引号
                json_str = json_str.replace('\u2019', "'")    # ' 右单引号
                json_str = json_str.replace('\u300c', '\\"')  # 「
                json_str = json_str.replace('\u300d', '\\"')  # 」
                json_str = json_str.replace('\u300e', '\\"')  # 『
                json_str = json_str.replace('\u300f', '\\"')  # 』

                # 修复 JSON 中的控制字符
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)

                # 移除尾部逗号
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)

                try:
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        # 尝试自动补全结尾（大多数情况下是缺少 ]}）
                        fixed = json_str.rstrip()
                        if '"segments"' in fixed and not fixed.endswith(']}'):
                            if not fixed.endswith(']'):
                                fixed += ']'
                            if not fixed.endswith(']}'):
                                fixed += '}'
                            try:
                                data = json.loads(fixed)
                                logger.warning(f"章节 {chapter_index} JSON 通过自动补全尾部修复成功")
                                json_str = fixed
                            except json.JSONDecodeError:
                                # 修复失败，重新抛出原始异常
                                raise e
                        else:
                            # 不是我们能修复的情况，直接抛出
                            raise e

                    segments = data.get('segments', [])
                    logger.info(f"  → 解析到 {len(segments)} 个对话片段")
                    return segments

                except json.JSONDecodeError as e:
                    logger.error(f"章节 {chapter_index} JSON 解析失败: {e}")
                    logger.error(f"错误位置: 第 {e.pos} 个字符")

                    # 保存完整的 JSON 到文件以便调试
                    debug_file = f"cache/debug_json_chapter_{chapter_index}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write("=== 原始 LLM 返回 ===\n")
                        f.write(result)
                        f.write("\n\n=== 清理后的 JSON ===\n")
                        f.write(json_str)
                        f.write("\n\n=== 错误位置附近 ===\n")
                        start = max(0, e.pos - 200)
                        end = min(len(json_str), e.pos + 200)
                        f.write(f"...{json_str[start:end]}...")
                    logger.error(f"已保存调试信息到: {debug_file}")

                    # 对于 JSON 解析错误，视为致命错误，交由上层处理
                    raise
            else:
                logger.warning(f"章节 {chapter_index} LLM 返回格式错误")
                return [{"text": chapter_content, "speaker": "narrator"}]
        except Exception as e:
            logger.error(f"章节 {chapter_index} 对话解析失败: {e}")
            # 对于 LLM 错误（如余额不足 402 等），视为致命错误，交由上层处理
            raise

    def normalize_speaker(self, speaker: str) -> str:
        """
        规范化说话人名称（将别名转为主名称）
        
        Args:
            speaker: 说话人名称
            
        Returns:
            规范化后的名称
        """
        if speaker == "narrator":
            return "narrator"
        
        # 查找角色
        for char in self.characters:
            if speaker == char['name']:
                return char['name']
            if speaker in char.get('aliases', []):
                return char['name']
        
        # 未找到，返回原名
        logger.warning(f"未知说话人: {speaker}，将作为旁白处理")
        return "narrator"

