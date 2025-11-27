"""
对话解析器
使用 LLM 识别章节中每句话的说话人（多角色配音专用）
"""

import re
import json
from typing import List, Dict, Optional
from loguru import logger

import config


class DialogueParser:
    """对话解析器（多角色配音业务模块）"""

    # 分块大小（字符数），使用配置值
    CHUNK_SIZE = config.DIALOGUE_CHUNK_SIZE
    # 分块重叠（字符数），确保上下文连贯
    CHUNK_OVERLAP = config.DIALOGUE_CHUNK_OVERLAP

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

    @staticmethod
    def add_intro_outro_to_segments(
        segments: List[Dict],
        intro: Optional[str],
        outro: Optional[str]
    ) -> List[Dict]:
        """
        为对话片段添加片头片尾（多角色配音专用）

        Args:
            segments: 对话片段列表
            intro: 片头文本
            outro: 片尾文本

        Returns:
            添加片头片尾后的片段列表
        """
        if not intro or not outro:
            logger.debug("  → 未添加片头片尾（intro 或 outro 为空）")
            return segments

        original_count = len(segments)
        enhanced_segments = []

        # 片头使用旁白
        enhanced_segments.append({
            "text": f"{intro}。",
            "speaker": "narrator",
        })

        # 正文对话
        enhanced_segments.extend(segments)

        # 片尾使用旁白
        enhanced_segments.append({
            "text": f"{outro}。",
            "speaker": "narrator",
        })

        logger.debug(f"  → 片段总数（添加前）: {original_count}")
        logger.debug(f"  → 片段总数（添加后）: {len(enhanced_segments)}")
        logger.debug(f"  → 第一个片段: {enhanced_segments[0]}")
        logger.debug(f"  → 最后一个片段: {enhanced_segments[-1]}")

        return enhanced_segments
    
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
        content_length = len(chapter_content)
        logger.debug(f"章节 {chapter_index} 内容长度: {content_length} 字符")

        # 如果内容较短，直接解析
        if content_length <= self.CHUNK_SIZE:
            return self._parse_chunk(chapter_content, chapter_index, 1, 1)

        # 长章节需要分块处理
        chunks = self._split_into_chunks(chapter_content)
        logger.info(f"  → 章节内容较长，分为 {len(chunks)} 块处理")

        all_segments = []
        for i, chunk in enumerate(chunks):
            chunk_num = i + 1
            logger.debug(f"  → 处理第 {chunk_num}/{len(chunks)} 块")
            segments = self._parse_chunk(chunk, chapter_index, chunk_num, len(chunks))
            all_segments.extend(segments)

        logger.info(f"  → 解析到 {len(all_segments)} 个对话片段（共 {len(chunks)} 块）")
        return all_segments

    def _split_into_chunks(self, content: str) -> List[str]:
        """
        将长内容分割为多个块

        Args:
            content: 原始内容

        Returns:
            内容块列表
        """
        chunks = []
        start = 0
        content_length = len(content)

        while start < content_length:
            end = start + self.CHUNK_SIZE

            # 如果不是最后一块，尝试在段落边界处切分
            if end < content_length:
                # 在切分点附近寻找段落边界（换行符）
                search_start = max(start + self.CHUNK_SIZE - 200, start)
                search_end = min(start + self.CHUNK_SIZE + 200, content_length)
                search_range = content[search_start:search_end]

                # 寻找最近的段落边界
                last_newline = search_range.rfind('\n')
                if last_newline != -1:
                    end = search_start + last_newline + 1

            chunk = content[start:end]
            chunks.append(chunk)

            # 下一块的起始位置（带重叠）
            start = end - self.CHUNK_OVERLAP if end < content_length else end

        return chunks

    def _parse_chunk(
        self,
        chunk_content: str,
        chapter_index: int,
        chunk_num: int,
        total_chunks: int
    ) -> List[Dict]:
        """
        解析单个内容块

        Args:
            chunk_content: 内容块
            chapter_index: 章节索引
            chunk_num: 当前块编号
            total_chunks: 总块数

        Returns:
            对话片段列表
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
{chunk_content}

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

        chunk_desc = f"章节{chapter_index}"
        if total_chunks > 1:
            chunk_desc += f"-块{chunk_num}/{total_chunks}"

        # 对话解析需要更大的输出空间（JSON 格式会膨胀约 3-4 倍）
        # 使用输入长度的 4 倍作为输出限制，最少 4096
        input_len = len(chunk_content)
        dialogue_max_tokens = max(4096, input_len * 4 // 3)  # 中文约 1.5 字符/token
        logger.debug(f"{chunk_desc} 输入长度: {input_len}，输出限制: {dialogue_max_tokens}")

        try:
            result = self.llm_manager.generate(prompt, max_tokens=dialogue_max_tokens)
            logger.debug(f"{chunk_desc} LLM 返回内容长度: {len(result)} 字符")

            return self._parse_llm_response(result, chapter_index, chunk_num)

        except Exception as e:
            logger.error(f"{chunk_desc} 对话解析失败: {e}")
            raise

    def _parse_llm_response(
        self,
        result: str,
        chapter_index: int,
        chunk_num: int
    ) -> List[Dict]:
        """
        解析 LLM 返回的 JSON 响应

        Args:
            result: LLM 返回的原始文本
            chapter_index: 章节索引
            chunk_num: 块编号

        Returns:
            对话片段列表
        """
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if not json_match:
            logger.warning(f"章节 {chapter_index} 块 {chunk_num} LLM 返回格式错误")
            return []

        json_str = json_match.group(0)

        # 清理 JSON
        json_str = self._clean_json_string(json_str)

        try:
            data = self._parse_json_with_fix(json_str, chapter_index, chunk_num)
            segments = data.get('segments', [])
            return segments

        except json.JSONDecodeError as e:
            logger.error(f"章节 {chapter_index} 块 {chunk_num} JSON 解析失败: {e}")
            self._save_debug_info(result, json_str, e, chapter_index, chunk_num)
            raise

    def _clean_json_string(self, json_str: str) -> str:
        """清理 JSON 字符串"""
        # 清理换行
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

        return json_str

    def _parse_json_with_fix(
        self,
        json_str: str,
        chapter_index: int,
        chunk_num: int
    ) -> Dict:
        """尝试解析 JSON，必要时自动修复"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 尝试自动补全结尾
            fixed = json_str.rstrip()
            if '"segments"' in fixed and not fixed.endswith(']}'):
                if not fixed.endswith(']'):
                    fixed += ']'
                if not fixed.endswith(']}'):
                    fixed += '}'
                try:
                    data = json.loads(fixed)
                    logger.warning(
                        f"章节 {chapter_index} 块 {chunk_num} "
                        f"JSON 通过自动补全尾部修复成功"
                    )
                    return data
                except json.JSONDecodeError:
                    pass
            raise e

    def _save_debug_info(
        self,
        result: str,
        json_str: str,
        error: json.JSONDecodeError,
        chapter_index: int,
        chunk_num: int
    ):
        """保存调试信息到文件"""
        debug_file = f"cache/debug_json_chapter_{chapter_index}_chunk_{chunk_num}.txt"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=== 原始 LLM 返回 ===\n")
                f.write(result)
                f.write("\n\n=== 清理后的 JSON ===\n")
                f.write(json_str)
                f.write("\n\n=== 错误位置附近 ===\n")
                start = max(0, error.pos - 200)
                end = min(len(json_str), error.pos + 200)
                f.write(f"...{json_str[start:end]}...")
            logger.error(f"已保存调试信息到: {debug_file}")
        except Exception as write_error:
            logger.error(f"保存调试信息失败: {write_error}")

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

