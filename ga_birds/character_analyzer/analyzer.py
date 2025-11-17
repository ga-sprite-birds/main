import re
import json
from typing import List, Dict, Set
from pathlib import Path

from loguru import logger
import config


class CharacterAnalyzer:

    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.all_characters = {}
        self.max_content_length = config.CHARACTER_MAX_CONTENT_LENGTH
    
    def analyze_chapter(self, chapter_content: str, chapter_index: int) -> List[Dict]:
        prompt = f"""请分析以下小说章节，提取所有出现的角色名。

要求：
1. 只提取人物角色名，不要提取地名、物品名
2. 识别角色的别名（如"张三"、"小张"、"张公子"是同一人）
3. 尝试识别角色性别（male/female/unknown）
4. 返回 JSON 格式，不要有任何其他说明文字

章节内容：
{chapter_content[:self.max_content_length]}

返回格式（必须是有效的 JSON）：
{{
  "characters": [
    {{"name": "陈长生", "aliases": ["长生", "陈某"], "gender": "male"}},
    {{"name": "徐有容", "aliases": ["有容", "徐姑娘"], "gender": "female"}}
  ]
}}"""
        
        try:
            result = self.llm_manager.generate(prompt)
            logger.debug(f"LLM 返回内容长度: {len(result)} 字符")
            
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                data = json.loads(json_str)
                characters = data.get('characters', [])
                
                logger.info(f"章节 {chapter_index} 识别到 {len(characters)} 个角色")
                return characters
            else:
                logger.warning(f"章节 {chapter_index} LLM 返回格式错误")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"章节 {chapter_index} JSON 解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"章节 {chapter_index} 分析失败: {e}")
            return []
    
    def merge_characters(self, chapter_characters: List[Dict], chapter_index: int):
        for char in chapter_characters:
            name = char.get('name', '')
            if not name:
                continue
            
            if name in self.all_characters:
                self.all_characters[name]['appearance_count'] += 1
                self.all_characters[name]['last_chapter'] = chapter_index
                
                existing_aliases = set(self.all_characters[name].get('aliases', []))
                new_aliases = set(char.get('aliases', []))
                self.all_characters[name]['aliases'] = list(existing_aliases | new_aliases)
            else:
                self.all_characters[name] = {
                    'name': name,
                    'aliases': char.get('aliases', []),
                    'gender': char.get('gender', 'unknown'),
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
        
        logger.info(f"角色数据已保存到: {output_path}")

