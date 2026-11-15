"""Business configuration facade for v2.

Business values come from ``ConfigService`` (system.db defaults + user
overrides). Deployment paths/secrets come from :mod:`system.config`. During a
task, the Core installs an immutable snapshot so changes made while it runs do
not affect the current task.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from system.config import settings
from system.config_schema import CONFIG_ITEMS

_SNAPSHOT: ContextVar[dict[str, Any] | None] = ContextVar(
    "ga_business_config_snapshot", default=None
)
_SERVICE: Any = None

_DEPLOYMENT_FIELDS: dict[str, str] = {
    "LLM_MODE": "LLM_MODE",
    "LLM_API_TYPE": "LLM_API_TYPE",
    "LLM_API_ENDPOINT": "LLM_API_ENDPOINT",
    "LLM_API_KEY": "LLM_API_KEY",
    "LLM_API_MODEL": "LLM_API_MODEL",
    "LLM_LOCAL_HOST": "LLM_LOCAL_HOST",
    "LLM_LOCAL_MODEL": "LLM_LOCAL_MODEL",
    "LLM_SYSTEM_PROMPT": "LLM_SYSTEM_PROMPT",
    "MODEL_CACHE_DIR": "MODEL_CACHE_DIR",
    "CHARACTER_CACHE_DIR": "CHARACTER_CACHE_DIR",
    "TASK_CACHE_DIR": "TASK_CACHE_DIR",
    "TASK_RESULT_TTL": "TASK_RESULT_TTL",
    "TASK_MAX_CONCURRENT": "TASK_MAX_CONCURRENT",
    "FFMPEG_PATH": "FFMPEG_PATH",
    "CORE_DIR": "CORE_DIR",
    "LOG_LEVEL": "LOG_LEVEL",
    "LOG_FORMAT": "LOG_FORMAT",
    "LOG_FILE": "LOG_FILE",
    "LOG_MAX_FILE_SIZE": "LOG_MAX_FILE_SIZE",
    "LOG_BACKUP_COUNT": "LOG_BACKUP_COUNT",
    "LOG_CONSOLE": "LOG_CONSOLE",
    "API_HOST": "API_HOST",
    "API_PORT": "API_PORT",
    "API_DEBUG": "API_DEBUG",
    "API_CORS_ENABLED": "API_CORS_ENABLED",
    "API_CORS_ORIGINS": "API_CORS_ORIGINS",
    "API_MAX_UPLOAD_SIZE": "API_MAX_UPLOAD_SIZE",
    "API_UPLOAD_DIR": "API_UPLOAD_DIR",
    "TTS_VOICE_CATALOG_CACHE": "TTS_VOICE_CATALOG_CACHE",
}

PERSONALITY_TAGS = {
    "性格": [
        "热血", "冷静", "冲动", "理智", "善良", "邪恶",
        "勇敢", "胆小", "自信", "自卑", "乐观", "悲观",
        "开朗", "内向", "外向", "孤僻", "温柔", "暴躁",
    ],
    "说话": [
        "直接", "委婉", "大声", "轻声", "快速", "缓慢",
        "幽默", "严肃", "啰嗦", "简洁", "粗鲁", "礼貌",
        "尖锐", "温和",
    ],
    "情绪": [
        "激动", "平静", "易怒", "温和", "焦虑", "淡定",
        "热情", "冷漠", "敏感", "迟钝", "多愁善感", "豁达",
    ],
    "角色": [
        "长辈", "晚辈", "领导", "下属", "老师", "学生",
        "严父", "慈母", "智者", "愚者", "导师", "学徒",
    ],
    "其他": [
        "传统", "现代", "固执", "灵活", "狡猾", "单纯",
        "圆滑", "耿直", "势利", "正直", "慈祥", "严厉",
        "谨慎", "鲁莽", "细心", "粗心",
    ],
}


def get_config_service():
    """Return the process-wide ConfigService without importing it eagerly."""
    global _SERVICE
    if _SERVICE is None:
        from services.config_service import ConfigService

        _SERVICE = ConfigService()
    return _SERVICE


def set_config_service(service: Any) -> None:
    """Inject a service for tests or an embedding process."""
    global _SERVICE
    _SERVICE = service


def reset_config_service() -> None:
    global _SERVICE
    _SERVICE = None


def business_config_snapshot() -> dict[str, Any]:
    """Capture the effective business configuration for one new task."""
    return get_config_service().get_all()


def get_value(key: str) -> Any:
    """Read one value from the task snapshot, falling back to live config."""
    if key in CONFIG_ITEMS:
        snapshot = _SNAPSHOT.get()
        if snapshot is not None:
            return snapshot[key]
        return get_config_service().get(key)
    if key in _DEPLOYMENT_FIELDS:
        return getattr(settings, _DEPLOYMENT_FIELDS[key])
    if key == "PERSONALITY_TAGS":
        return PERSONALITY_TAGS
    raise AttributeError(key)


@contextmanager
def use_config_snapshot(snapshot: dict[str, Any]) -> Iterator[None]:
    """Install an immutable business-config snapshot for the current task."""
    token = _SNAPSHOT.set(dict(snapshot))
    try:
        yield
    finally:
        _SNAPSHOT.reset(token)


def current_config_snapshot() -> dict[str, Any] | None:
    return _SNAPSHOT.get()


def __getattr__(name: str) -> Any:
    value = get_value(name)
    if name in ("CORE_DIR", "API_UPLOAD_DIR", "TASK_CACHE_DIR", "LOG_FILE"):
        return str(value)
    return value
