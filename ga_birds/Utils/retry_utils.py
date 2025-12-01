"""
GA Sprite Birds - 重试工具模块
提供统一的重试机制，支持指数退避、错误分类等策略

版本: v1.0
开发团队: GA Team
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import logging
from typing import Type, Tuple

logger = logging.getLogger(__name__)


# ============================================
# 可重试错误定义
# ============================================

class RetryableError(Exception):
    """可重试的错误（如网络超时、临时故障）"""
    pass


class NonRetryableError(Exception):
    """不可重试的错误（如参数错误、认证失败）"""
    pass


# ============================================
# TTS 重试装饰器
# ============================================

tts_retry = retry(
    stop=stop_after_attempt(5),  # TTS 可能不稳定，最多重试 5 次
    wait=wait_exponential(
        multiplier=1,  # 基础延迟 1 秒
        min=1,         # 最小延迟 1 秒
        max=30         # 最大延迟 30 秒
    ),
    retry=retry_if_exception_type((
        ConnectionError,
        TimeoutError,
        OSError,
        Exception  # 捕获所有异常，但会记录日志
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True  # 重试失败后抛出原始异常
)


# ============================================
# LLM 重试装饰器
# ============================================

llm_retry = retry(
    stop=stop_after_attempt(3),  # 本地服务，失败概率低，最多重试 3 次
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=10
    ),
    retry=retry_if_exception_type((
        ConnectionError,
        TimeoutError,
        Exception
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


# ============================================
# 文件 I/O 重试装饰器
# ============================================

file_io_retry = retry(
    stop=stop_after_attempt(3),  # 文件操作，快速重试
    wait=wait_exponential(
        multiplier=0.1,  # 基础延迟 100ms
        min=0.1,
        max=1
    ),
    retry=retry_if_exception_type((
        OSError,
        IOError,
        PermissionError
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


# ============================================
# 自定义重试装饰器工厂
# ============================================

def create_retry_decorator(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    创建自定义重试装饰器

    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        retry_exceptions: 需要重试的异常类型元组

    Returns:
        重试装饰器

    Example:
        >>> custom_retry = create_retry_decorator(
        ...     max_attempts=5,
        ...     base_delay=2.0,
        ...     retry_exceptions=(ConnectionError, TimeoutError)
        ... )
        >>> @custom_retry
        ... async def my_function():
        ...     pass
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=base_delay,
            min=base_delay,
            max=max_delay
        ),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

