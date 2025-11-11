"""
GA Sprite Birds - LLM 管理器
统一管理本地和 API 模式的 LLM 调用

版本: v1.0
开发团队: Tiger
"""

import re
import importlib
from typing import Optional, List
import time

import ollama
from openai import OpenAI
from loguru import logger

import config

# 动态导入核心模块
_core_module_name = config.CORE_DIR.replace('-', '_')
_utils_module = importlib.import_module(f'{_core_module_name}.Utils.model_manager')
ModelManager = _utils_module.ModelManager

# 导入 token 工具
_token_utils_module = importlib.import_module(f'{_core_module_name}.Utils.token_utils')
count_tokens = _token_utils_module.count_tokens
split_text_smart = _token_utils_module.split_text_smart


class LLMManager:
    """LLM 管理器"""

    def __init__(self):
        """初始化 LLM 管理器"""
        # 统一转为小写，支持大小写不敏感
        self.mode = config.LLM_MODE.lower()
        self.model_manager = ModelManager()

        if self.mode == "local":
            # 验证本地 LLM 设置
            if not self.model_manager.validate_local_llm_setup():
                raise RuntimeError("本地 LLM 设置验证失败，请检查配置和模型")

            # 检查本地模式的配置是否合理
            self._validate_local_config()

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

    def _validate_local_config(self):
        """验证本地模式的配置"""
        # 常见本地模型的上下文限制
        model_limits = {
            "deepseek-r1:7b": 8192,
            "deepseek-r1:1.5b": 8192,
            "qwen2.5:7b": 32768,
            "llama3.1:8b": 128000,
        }

        # 获取当前模型的限制
        model_name = config.LLM_LOCAL_MODEL.lower()
        max_ctx = None

        for model_key, limit in model_limits.items():
            if model_key in model_name:
                max_ctx = limit
                break

        # 如果配置的 num_ctx 超过已知限制，发出警告
        if max_ctx and config.LLM_NUM_CTX > max_ctx:
            logger.warning(f"⚠ 警告：LLM_NUM_CTX={config.LLM_NUM_CTX} 可能超出模型 {config.LLM_LOCAL_MODEL} 的上下文限制（{max_ctx} tokens）")
            logger.warning(f"→ 建议修改 .env 配置：LLM_NUM_CTX={max_ctx}")
            logger.warning(f"→ 如果遇到超时或错误，请降低此配置")

        # 检查输出 tokens 是否合理
        if config.LLM_MAX_TOKENS >= config.LLM_NUM_CTX:
            logger.warning(f"⚠ 警告：LLM_MAX_TOKENS={config.LLM_MAX_TOKENS} 不应大于等于 LLM_NUM_CTX={config.LLM_NUM_CTX}")
            logger.warning(f"→ 建议修改 .env 配置：LLM_MAX_TOKENS={config.LLM_NUM_CTX // 4}")
    
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

        logger.debug(f"调用 Ollama，超时时间: {config.LLM_TIMEOUT} 秒")

        # 创建 Ollama 客户端并设置超时
        client = ollama.Client(
            host=config.LLM_LOCAL_HOST,
            timeout=config.LLM_TIMEOUT
        )

        response = client.chat(
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
        original_text = text

        # 策略1：如果存在 </think> 标签，提取其后的所有内容
        if '</think>' in text:
            # 找到最后一个 </think> 的位置
            last_think_end = text.rfind('</think>')
            result = text[last_think_end + len('</think>'):].strip()

            if result and len(result) >= 10:
                logger.debug(f"提取 </think> 后的内容，长度: {len(result)}")
                return result
            else:
                logger.warning("⚠ </think> 后内容为空或过短，尝试其他策略")

        # 策略2：移除所有 <think>...</think> 标签及其内容
        filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # 移除可能的其他思考标记
        filtered = re.sub(r'思考过程[:：].*?(?=\n\n|\Z)', '', filtered, flags=re.DOTALL)

        # 清理多余的空白
        filtered = re.sub(r'\n{3,}', '\n\n', filtered)
        filtered = filtered.strip()

        # 安全检查：如果过滤后文本为空或过短，返回原文
        if not filtered or len(filtered) < 10:
            logger.warning("⚠ 过滤后文本过短或为空，返回原文")
            logger.debug(f"原文前200字: {original_text[:200]}...")
            return original_text.strip()

        logger.debug(f"使用策略2过滤，结果长度: {len(filtered)}")
        return filtered
    
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
        将文本口语化（支持自动分段处理）

        Args:
            text: 原始文本

        Returns:
            口语化后的文本
        """
        # 使用自定义 prompt 或默认 prompt
        if config.LLM_SYSTEM_PROMPT:
            system_prompt = config.LLM_SYSTEM_PROMPT
        else:
            system_prompt = """你是一个专业的有声书文本改写助手。
你的任务是将书面小说文本改写为更适合语音朗读的口语化版本。

改写要求：
1. 将文言文、书面语改为现代口语表达
2. 将长句拆分为短句，便于朗读和理解
3. 将复杂的修辞简化为直白的表达
4. 适当添加语气词和停顿（用标点符号）
5. 保持故事情节和人物对话不变
6. 必须进行改写，不能原样输出

输出格式：
- 你可以在 <think> 标签中分析如何改写
- 在 </think> 之后直接输出改写后的文本
- 不要添加任何说明、前缀或后缀"""

        # 步骤 1：计算 token 数
        model_name = config.LLM_API_MODEL if self.mode == "api" else "gpt-3.5-turbo"
        input_tokens = count_tokens(text, model_name)
        system_tokens = count_tokens(system_prompt, model_name)

        # 步骤 2：计算可用的输入空间
        # 公式：可用空间 = 总上下文 - 输出预留 - system prompt - 安全边距
        available_tokens = config.LLM_NUM_CTX - config.LLM_MAX_TOKENS - system_tokens - 500

        logger.info(f"开始口语化文本，长度: {len(text)} 字符（约 {input_tokens} tokens）")
        logger.debug(f"可用输入空间: {available_tokens} tokens（上下文={config.LLM_NUM_CTX}, 输出预留={config.LLM_MAX_TOKENS}）")

        # 步骤 3：判断是否需要分段
        if input_tokens > available_tokens:
            logger.warning(f"⚠ 提示：当前文本较长（约 {input_tokens} tokens）")
            logger.warning(f"→ 根据配置 LLM_NUM_CTX={config.LLM_NUM_CTX}，可能超出模型上下文限制")

            # 分段处理
            segments = split_text_smart(text, available_tokens, model_name)
            logger.info(f"→ 已自动分为 {len(segments)} 段处理，确保生成质量")
            logger.info(f"→ 建议：如果模型支持更大上下文，可适当增加 LLM_NUM_CTX 配置")

            # 分别处理每段
            results = []
            for i, segment in enumerate(segments, 1):
                segment_tokens = count_tokens(segment, model_name)
                logger.info(f"→ 处理第 {i}/{len(segments)} 段（约 {segment_tokens} tokens）...")

                start_time = time.time()
                result = self._colloquialize_single(segment, system_prompt)
                elapsed = time.time() - start_time

                result_tokens = count_tokens(result, model_name)
                logger.info(f"  ✓ 第 {i} 段完成（{segment_tokens} → {result_tokens} tokens，耗时 {elapsed:.1f}s）")

                results.append(result)

            # 合并结果
            final_result = "\n".join(results)
            logger.info(f"✓ 文本分段处理完成（共 {len(segments)} 段）")
            logger.info(f"→ 合并后长度: {len(final_result)} 字符（约 {count_tokens(final_result, model_name)} tokens）")

            return final_result
        else:
            # 单次处理
            logger.debug(f"文本长度适中，单次处理")
            return self._colloquialize_single(text, system_prompt)

    def _colloquialize_single(self, text: str, system_prompt: str) -> str:
        """
        单次口语化处理（内部方法）

        Args:
            text: 原始文本
            system_prompt: 系统提示词

        Returns:
            口语化后的文本
        """
        prompt = f"""请将以下小说文本改写为适合朗读的口语化版本。

原文：
{text}

要求：
1. 必须进行改写，不能原样输出
2. 在 </think> 之后输出改写结果
3. 只输出改写后的文本，不要有任何说明"""

        logger.debug(f"原文前100字: {text[:100]}...")

        result = self.generate(prompt, system_prompt)

        logger.debug(f"LLM 原始输出长度: {len(result)} 字符")
        logger.debug(f"LLM 原始输出前200字: {result[:200]}...")

        # 过滤思考过程标签
        filtered_result = self._filter_think_tags(result)

        logger.debug(f"过滤后输出长度: {len(filtered_result)} 字符")
        logger.debug(f"过滤后前100字: {filtered_result[:100]}...")

        return filtered_result

