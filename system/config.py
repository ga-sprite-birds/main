"""Deployment and secret settings loaded from the project .env file."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Settings that remain owned by deployment, not the system-config API."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )

    LLM_MODE: str = "local"
    LLM_API_ENDPOINT: str = "https://api.openai.com/v1"
    LLM_API_KEY: str | None = None
    LLM_API_MODEL: str = "gpt-4"
    LLM_LOCAL_HOST: str = "http://localhost:11434"
    LLM_LOCAL_MODEL: str = "deepseek-r1:7b"
    LLM_SYSTEM_PROMPT: str = ""

    API_HOST: str = "127.0.0.1"
    API_PORT: int = Field(default=8000, ge=1, le=65535)
    API_DEBUG: bool = False
    API_CORS_ENABLED: bool = True
    API_CORS_ORIGINS: str = "*"
    API_MAX_UPLOAD_SIZE: int = Field(default=100, ge=0)
    API_UPLOAD_DIR: Path = PROJECT_ROOT / "uploads"

    TASK_RESULT_TTL: int = Field(default=86400, ge=0)
    TASK_CACHE_DIR: Path = PROJECT_ROOT / "cache" / "tasks"
    TASK_MAX_CONCURRENT: int = Field(default=2, gt=0)
    TASK_GRACE_SECONDS: float = Field(default=30.0, ge=0)

    FFMPEG_PATH: str = ""
    CORE_DIR: Path = PROJECT_ROOT / "ga_birds"
    DATA_DIR: Path = PROJECT_ROOT / "data"
    CACHE_DIR: Path = PROJECT_ROOT / "cache"
    RUN_DIR: Path = PROJECT_ROOT / "run"
    MODEL_CACHE_DIR: Path = PROJECT_ROOT / "cache" / "models"
    CHARACTER_CACHE_DIR: Path = PROJECT_ROOT / "cache" / "role"
    TTS_VOICE_CATALOG_CACHE: Path = PROJECT_ROOT / "cache" / "voices" / "edge_voices.json"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "%(asctime)s | %(levelname)s | "
        "%(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    LOG_FILE: Path = PROJECT_ROOT / "logs" / "app.log"
    LOG_MAX_FILE_SIZE: int = Field(default=10, gt=0)
    LOG_BACKUP_COUNT: int = Field(default=5, ge=0)
    LOG_CONSOLE: bool = True

    @field_validator(
        "API_UPLOAD_DIR",
        "TASK_CACHE_DIR",
        "CORE_DIR",
        "DATA_DIR",
        "CACHE_DIR",
        "RUN_DIR",
        "MODEL_CACHE_DIR",
        "CHARACTER_CACHE_DIR",
        "TTS_VOICE_CATALOG_CACHE",
        "LOG_FILE",
        mode="before",
    )
    @classmethod
    def resolve_project_path(cls, value: str | Path) -> Path:
        """Resolve relative deployment paths against the project root."""
        path = Path(value).expanduser()
        return path if path.is_absolute() else PROJECT_ROOT / path


settings = Settings()
