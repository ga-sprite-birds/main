"""
GA Sprite Birds - Retry utility module
Provides a unified retry mechanism supporting strategies like exponential backoff and error classification

Version: v1.0
Dev team: GA Team
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
from typing import Type, Tuple

logger = logging.getLogger(__name__)


# ============================================
# Retryable error definitions
# ============================================

class RetryableError(Exception):
    """An error that can be retried (e.g. network timeout, transient failure)"""
    pass


class NonRetryableError(Exception):
    """An error that cannot be retried (e.g. invalid argument, authentication failure)"""
    pass


def _is_retryable_tts_error(exception: Exception) -> bool:
    """TTS errors are retryable except explicitly classified failures."""
    return not isinstance(exception, NonRetryableError)


def _is_retryable_llm_error(exception: Exception) -> bool:
    """LLM errors are retryable except authentication and bad-request failures."""
    if isinstance(exception, NonRetryableError):
        return False
    return exception.__class__.__name__ not in (
        "AuthenticationError",
        "PermissionDeniedError",
        "BadRequestError",
    )


# ============================================
# TTS retry decorator
# ============================================

tts_retry = retry(
    stop=stop_after_attempt(5),  # TTS may be unstable; retry at most 5 times
    wait=wait_exponential(
        multiplier=1,  # base delay 1 second
        min=1,         # minimum delay 1 second
        max=30         # maximum delay 30 seconds
    ),
    retry=retry_if_exception(_is_retryable_tts_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True  # raise the original exception after retries fail
)


# ============================================
# LLM retry decorator
# ============================================

llm_retry = retry(
    stop=stop_after_attempt(3),  # local service, low failure probability; retry at most 3 times
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=10
    ),
    retry=retry_if_exception(_is_retryable_llm_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


# ============================================
# File I/O retry decorator
# ============================================

file_io_retry = retry(
    stop=stop_after_attempt(3),  # file operations; retry quickly
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
# Custom retry decorator factory
# ============================================

def create_retry_decorator(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Create a custom retry decorator

    Args:
        max_attempts: maximum number of retry attempts
        base_delay: base delay time (seconds)
        max_delay: maximum delay time (seconds)
        retry_exceptions: tuple of exception types to retry on

    Returns:
        retry decorator

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

