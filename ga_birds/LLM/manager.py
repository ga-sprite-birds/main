"""
GA Sprite Birds - LLM Manager
Unified management of local and API mode LLM calls

Version: v1.0
Dev team: Tiger
"""

import re
import importlib
from typing import Optional, List
import time

import ollama
from openai import OpenAI
from loguru import logger

from ga_birds.Common.i18n import t

import config
from ga_birds.Utils.retry_utils import llm_retry

# Dynamically import the core module
_core_module_name = config.CORE_DIR.replace('-', '_')
_utils_module = importlib.import_module(f'{_core_module_name}.Utils.model_manager')
ModelManager = _utils_module.ModelManager

# Import token utilities
_token_utils_module = importlib.import_module(f'{_core_module_name}.Utils.token_utils')
count_tokens = _token_utils_module.count_tokens
split_text_smart = _token_utils_module.split_text_smart


class LLMManager:
    """LLM Manager"""

    def __init__(self):
        """Initialize the LLM manager"""
        # Normalize to lowercase for case-insensitive support
        self.mode = config.LLM_MODE.lower()
        self.model_manager = ModelManager()

        if self.mode == "local":
            # Validate local LLM setup
            if not self.model_manager.validate_local_llm_setup():
                raise RuntimeError(t("model.llm_validate_failed"))

            # Check whether the local-mode configuration is reasonable
            self._validate_local_config()

            self.client = None  # Ollama uses functional calls
            logger.info(t("llm.mode_local", model=config.LLM_LOCAL_MODEL))
        elif self.mode == "api":
            self.client = OpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_API_ENDPOINT
            )
            logger.info(t("llm.mode_api", model=config.LLM_API_MODEL))
        else:
            raise ValueError(t("llm.unsupported_mode", mode=self.mode))

    def _validate_local_config(self):
        """Validate the local-mode configuration"""
        # Context limits for common local models
        model_limits = {
            "deepseek-r1:7b": 8192,
            "deepseek-r1:1.5b": 8192,
            "qwen2.5:7b": 32768,
            "llama3.1:8b": 128000,
        }

        # Get the current model's limit
        model_name = config.LLM_LOCAL_MODEL.lower()
        max_ctx = None

        for model_key, limit in model_limits.items():
            if model_key in model_name:
                max_ctx = limit
                break

        # Warn if the configured num_ctx exceeds a known limit
        if max_ctx and config.LLM_NUM_CTX > max_ctx:
            logger.warning(t("llm.ctx_warning", ctx=config.LLM_NUM_CTX, model=config.LLM_LOCAL_MODEL, max_ctx=max_ctx))
            logger.warning(t("llm.ctx_suggestion", max_ctx=max_ctx))
            logger.warning(t("llm.ctx_timeout_hint"))

        # Check whether output tokens are reasonable
        if config.LLM_MAX_TOKENS >= config.LLM_NUM_CTX:
            logger.warning(t("llm.output_warning", tokens=config.LLM_MAX_TOKENS, ctx=config.LLM_NUM_CTX))
            logger.warning(t("llm.output_suggestion", suggested=config.LLM_NUM_CTX // 4))
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text

        Args:
            prompt: user prompt
            system_prompt: system prompt
            max_tokens: max output tokens (uses configured default if None)

        Returns:
            generated text
        """
        if max_tokens is None:
            max_tokens = config.LLM_MAX_TOKENS

        try:
            if self.mode == "local":
                return self._generate_local(prompt, system_prompt, max_tokens)
            else:
                return self._generate_api(prompt, system_prompt, max_tokens)
        except Exception as e:
            logger.error(t("llm.generate_failed", error=e))
            raise

    @llm_retry
    def _generate_local(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate locally using Ollama (with automatic retry)"""
        if max_tokens is None:
            max_tokens = config.LLM_MAX_TOKENS

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        logger.debug(t("llm.ollama_timeout", timeout=config.LLM_TIMEOUT))

        # Create the Ollama client and set the timeout
        client = ollama.Client(
            host=config.LLM_LOCAL_HOST,
            timeout=config.LLM_TIMEOUT
        )

        response = client.chat(
            model=config.LLM_LOCAL_MODEL,
            messages=messages,
            options={
                "temperature": config.LLM_TEMPERATURE,
                "num_predict": max_tokens,
                "num_ctx": config.LLM_NUM_CTX
            }
        )

        result = response["message"]["content"]
        logger.debug(t("llm.local_done", input=len(prompt), output=len(result), max_tokens=max_tokens))

        # Filter the DeepSeek R1 thinking-process tags
        result = self._filter_think_tags(result)

        return result

    def _filter_think_tags(self, text: str) -> str:
        """
        Filter the thinking-process tags of the DeepSeek R1 model

        DeepSeek R1 outputs a thinking process wrapped in <think>...</think>,
        but we only need the final answer content

        Args:
            text: original text

        Returns:
            filtered text
        """
        original_text = text

        # Strategy 1: if a </think> tag exists, extract everything after it
        if '</think>' in text:
            # Find the position of the last </think>
            last_think_end = text.rfind('</think>')
            result = text[last_think_end + len('</think>'):].strip()

            if result and len(result) >= 10:
                logger.debug(t("llm.think_extracted", length=len(result)))
                return result
            else:
                logger.warning(t("llm.think_empty"))

        # Strategy 2: remove all <think>...</think> tags and their content
        filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Remove other possible thinking markers
        filtered = re.sub(r'思考过程[:：].*?(?=\n\n|\Z)', '', filtered, flags=re.DOTALL)

        # Clean up excessive whitespace
        filtered = re.sub(r'\n{3,}', '\n\n', filtered)
        filtered = filtered.strip()

        # Safety check: if the filtered text is empty or too short, return the original
        if not filtered or len(filtered) < 10:
            logger.warning(t("llm.filter_empty"))
            logger.debug(t("llm.filter_original_preview", text=original_text[:200]))
            return original_text.strip()

        logger.debug(t("llm.filter_strategy2", length=len(filtered)))
        return filtered
    
    @llm_retry
    def _generate_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate via API (with automatic retry)"""
        if max_tokens is None:
            max_tokens = config.LLM_MAX_TOKENS

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=config.LLM_API_MODEL,
            messages=messages,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=max_tokens
        )

        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            logger.warning(t("llm.truncated_result"))

        result = choice.message.content or ""
        logger.debug(t("llm.api_done", input=len(prompt), output=len(result), max_tokens=max_tokens))

        return result
    
    def colloquialize_text(self, text: str) -> str:
        """
        Make the text colloquial (supports automatic segmentation)

        Args:
            text: original text

        Returns:
            colloquialized text
        """
        # Use a custom prompt or the default prompt
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

        # Step 1: count tokens
        model_name = config.LLM_API_MODEL if self.mode == "api" else "gpt-3.5-turbo"
        input_tokens = count_tokens(text, model_name)
        system_tokens = count_tokens(system_prompt, model_name)

        # Step 2: compute the available input space
        # Formula: available space = total context - output reserve - system prompt - safety margin
        available_tokens = config.LLM_NUM_CTX - config.LLM_MAX_TOKENS - system_tokens - 500

        logger.info(t("llm.colloquialize_start", length=len(text), tokens=input_tokens))
        logger.debug(t("llm.available_tokens", tokens=available_tokens, ctx=config.LLM_NUM_CTX, reserve=config.LLM_MAX_TOKENS))

        # Step 3: determine whether segmentation is needed
        if input_tokens > available_tokens:
            logger.warning(t("llm.text_too_long", tokens=input_tokens))
            logger.warning(t("llm.ctx_warning", ctx=config.LLM_NUM_CTX, model=config.LLM_API_MODEL, max_ctx="unknown"))

            # Process by segments
            segments = split_text_smart(text, available_tokens, model_name)
            logger.info(t("llm.auto_split", count=len(segments)))
            logger.info(t("llm.split_suggestion"))

            # Process each segment separately
            results = []
            for i, segment in enumerate(segments, 1):
                segment_tokens = count_tokens(segment, model_name)
                logger.info(t("llm.segment_processing", i=i, total=len(segments), tokens=segment_tokens))

                start_time = time.time()
                result = self._colloquialize_single(segment, system_prompt)
                elapsed = time.time() - start_time

                result_tokens = count_tokens(result, model_name)
                logger.info(t("llm.segment_done", i=i, input_tokens=segment_tokens, output_tokens=result_tokens, elapsed=elapsed))

                results.append(result)

            # Merge results
            final_result = "\n".join(results)
            logger.info(t("llm.all_segments_done", count=len(segments)))
            logger.info(t("llm.merged_length", length=len(final_result), tokens=count_tokens(final_result, model_name)))

            if not final_result.strip():
                logger.warning(t("llm.empty_result_fallback"))
                return text

            return final_result
        else:
            # Single-pass processing
            logger.debug(t("llm.single_pass"))
            return self._colloquialize_single(text, system_prompt)

    def _colloquialize_single(self, text: str, system_prompt: str) -> str:
        """
        Single-pass colloquialization (internal method)

        Args:
            text: original text
            system_prompt: system prompt

        Returns:
            colloquialized text
        """
        prompt = f"""请将以下小说文本改写为适合朗读的口语化版本。

原文：
{text}

要求：
1. 必须进行改写，不能原样输出
2. 在 </think> 之后输出改写结果
3. 只输出改写后的文本，不要有任何说明"""

        logger.debug(t("llm.original_preview", text=text[:100]))

        result = self.generate(prompt, system_prompt)

        logger.debug(t("llm.raw_output_length", length=len(result)))
        logger.debug(t("llm.raw_output_preview", text=result[:200]))

        # Filter the thinking-process tags
        filtered_result = self._filter_think_tags(result)

        logger.debug(t("llm.filtered_output_length", length=len(filtered_result)))
        logger.debug(t("llm.filtered_preview", text=filtered_result[:100]))

        if not filtered_result.strip():
            logger.warning(t("llm.empty_result_fallback"))
            return text

        return filtered_result

