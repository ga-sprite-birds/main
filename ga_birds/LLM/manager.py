"""
GA Sprite Birds - LLM 管理器
统一管理本地和 API 模式的 LLM 调用

版本: v1.0
开发团队: Tiger
"""

import re
import importlib
from typing import Optional

import ollama
from openai import OpenAI
from loguru import logger

import config

# 动态导入核心模块
_core_module_name = config.CORE_DIR.replace('-', '_')
_utils_module = importlib.import_module(f'{_core_module_name}.Utils.model_manager')
ModelManager = _utils_module.ModelManager


class LLMManager:
    """LLM 管理器"""

    def __init__(self):
        """初始化 LLM 管理器"""
        self.mode = config.LLM_MODE
        self.model_manager = ModelManager()

        if self.mode == "local":
            # 验证本地 LLM 设置
            if not self.model_manager.validate_local_llm_setup():
                raise RuntimeError("本地 LLM 设置验证失败，请检查配置和模型")

            self.client = None  # Ollama 使用函数式调用
            logger.info(f"LLM 模式: 本地 (Ollama), 模型: {config.LLM_LOCAL_MODEL}")
        elif self.mode == "api":
            self.client = OpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_API_ENDPOINT
            )
            logger.info(f"LLM 模式: API, 模型: {config.LLM_API_MODEL}")
        else:
            raise ValueError(f"不支持的 LLM 模式: {self.mode}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            
        Returns:
            生成的文本
        """
        try:
            if self.mode == "local":
                return self._generate_local(prompt, system_prompt)
            else:
                return self._generate_api(prompt, system_prompt)
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            raise
    
    def _generate_local(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用 Ollama 本地生成"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = ollama.chat(
            model=config.LLM_LOCAL_MODEL,
            messages=messages,
            options={
                "temperature": config.LLM_TEMPERATURE,
                "num_predict": config.LLM_MAX_TOKENS,
                "num_ctx": config.LLM_NUM_CTX
            }
        )

        result = response["message"]["content"]
        logger.debug(f"LLM 本地生成完成，输入: {len(prompt)} 字符，输出: {len(result)} 字符")

        # 过滤 DeepSeek R1 的思考过程标签
        result = self._filter_think_tags(result)

        return result

    def _filter_think_tags(self, text: str) -> str:
        """
        过滤 DeepSeek R1 模型的思考过程标签

        DeepSeek R1 会输出 <think>...</think> 包裹的思考过程，
        我们只需要最终的回答内容

        Args:
            text: 原始文本

        Returns:
            过滤后的文本
        """
        # 移除 <think>...</think> 标签及其内容
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # 移除可能的其他思考标记
        text = re.sub(r'思考过程[:：].*?(?=\n\n|\Z)', '', text, flags=re.DOTALL)

        # 清理多余的空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text
    
    def _generate_api(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用 API 生成"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=config.LLM_API_MODEL,
            messages=messages,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS
        )
        
        result = response.choices[0].message.content
        logger.debug(f"LLM API 生成完成，输入: {len(prompt)} 字符，输出: {len(result)} 字符")
        
        return result
    
    def colloquialize_text(self, text: str) -> str:
        """
        将文本口语化

        Args:
            text: 原始文本

        Returns:
            口语化后的文本
        """
        # 使用自定义 prompt 或默认 prompt
        if config.LLM_SYSTEM_PROMPT:
            system_prompt = config.LLM_SYSTEM_PROMPT
        else:
            system_prompt = """你是一个专业的文本口语化助手。
你的任务是将书面文本转换为适合朗读的口语化文本。

要求：
1. 保持原文意思不变
2. 将复杂的书面语转换为自然的口语表达
3. 适当添加停顿标记（用逗号、句号）
4. 不要添加任何解释、评论、思考过程
5. 不要使用 <think> 标签
6. 直接输出转换后的文本，不要有任何前缀或后缀"""

        prompt = f"请将以下文本口语化，直接输出结果，不要有任何思考过程或解释：\n\n{text}"

        logger.info(f"开始口语化文本，长度: {len(text)} 字符")
        result = self.generate(prompt, system_prompt)

        return result.strip()

