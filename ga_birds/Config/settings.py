"""
GA Sprite Birds - 配置管理
支持从 YAML 文件加载配置，并支持 API 参数覆盖

版本: v1.0
开发团队: Tiger
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class LLMLocalConfig(BaseModel):
    """LLM 本地配置"""
    host: str = os.getenv("LLM_LOCAL_HOST", "http://localhost:11434")
    model: str = os.getenv("LLM_LOCAL_MODEL", "deepseek-r1:7b")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    num_ctx: int = int(os.getenv("LLM_NUM_CTX", "8192"))


class LLMAPIConfig(BaseModel):
    """LLM API 配置"""
    type: str = os.getenv("LLM_API_TYPE", "openai")
    endpoint: str = os.getenv("LLM_API_ENDPOINT", "https://api.openai.com/v1")
    api_key: Optional[str] = os.getenv("LLM_API_KEY")
    model: str = os.getenv("LLM_API_MODEL", "gpt-4")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))


class LLMPromptConfig(BaseModel):
    """LLM Prompt 配置"""
    system_prompt: str = ""  # 自定义 system prompt，留空使用默认


class LLMConfig(BaseModel):
    """LLM 配置"""
    mode: str = "local"  # local 或 api
    local: LLMLocalConfig = Field(default_factory=LLMLocalConfig)
    api: LLMAPIConfig = Field(default_factory=LLMAPIConfig)
    prompt: LLMPromptConfig = Field(default_factory=LLMPromptConfig)


class TTSLocalConfig(BaseModel):
    """TTS 本地配置"""
    engine: str = "cosyvoice"
    model_path: str = "./models/CosyVoice"
    voice: str = "default"
    sample_rate: int = 22050
    device: str = "cpu"  # cpu, cuda, mps

    def validate_device(self) -> str:
        """验证并返回实际可用的设备"""
        valid_devices = ["cpu", "cuda", "mps"]
        if self.device not in valid_devices:
            return "cpu"
        return self.device


class TTSAPIConfig(BaseModel):
    """TTS API 配置"""
    type: str = "edge-tts"
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: float = 1.0
    volume: float = 1.0
    pitch: float = 1.0


class TTSConfig(BaseModel):
    """TTS 配置"""
    mode: str = "api"  # local 或 api
    local: TTSLocalConfig = Field(default_factory=TTSLocalConfig)
    api: TTSAPIConfig = Field(default_factory=TTSAPIConfig)


class VoiceCloneConfig(BaseModel):
    """声音克隆配置"""
    enabled: bool = False
    reference_audio: Optional[str] = None
    reference_text: Optional[str] = None


class EmotionConfig(BaseModel):
    """情感配置"""
    enabled: bool = False
    default: str = "neutral"
    intensity: float = 0.5


class ChapterConfig(BaseModel):
    """章节配置"""
    enabled: bool = True
    regex_patterns: List[str] = Field(default_factory=lambda: [
        r'^第[零一二三四五六七八九十百千万0-9]+章',
        r'^第[零一二三四五六七八九十百千万0-9]+卷',
        r'^Chapter\s+\d+',
        r'^第[零一二三四五六七八九十百千万0-9]+回'
    ])
    min_length: int = 100
    keep_title: bool = True
    intro_outro: bool = True  # 是否启用片头片尾
    intro_template: str = "第{index}章开始"  # 片头模板
    outro_template: str = "本章播讲完毕"  # 片尾模板
    intro_outro_pause: float = 1.0  # 片头片尾停顿时间（秒）


class TextPreprocessingConfig(BaseModel):
    """文本预处理配置"""
    enabled: bool = True
    remove_extra_newlines: bool = True
    remove_headers_footers: bool = True
    fix_pdf_linebreaks: bool = True
    auto_detect_encoding: bool = True


class OutputConfig(BaseModel):
    """输出配置"""
    base_path: str = "./output"
    strategy: str = "by_role"
    format: str = "mp3"
    bitrate: int = 128
    filename_template: str = "{index:03d}-{title}.{format}"
    keep_temp_files: bool = False
    duplicate_handling: str = "rename"  # overwrite, rename, skip
    save_chapter_text: bool = True  # 是否保存章节文本
    chapter_text_encoding: str = "utf-8"  # 章节文本编码


class APIConfig(BaseModel):
    """API 服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    route_file: str = "fcgi-bin/api.py"
    debug: bool = True
    cors_enabled: bool = True
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    max_upload_size: int = 100


class RedisConfig(BaseModel):
    """Redis 配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class TaskConfig(BaseModel):
    """任务配置"""
    queue_type: str = "memory"
    max_concurrent_tasks: int = 3
    timeout: int = 3600
    result_ttl: int = 86400
    redis: RedisConfig = Field(default_factory=RedisConfig)


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    file: str = "./logs/app.log"
    max_file_size: int = 10
    backup_count: int = 5
    console: bool = True


class ModelDownloadConfig(BaseModel):
    """模型下载配置"""
    source: str = "modelscope"
    cache_dir: str = "./models"
    use_mirror: bool = True


class Settings(BaseSettings):
    """系统配置"""
    core_dir: str = "ga_birds"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    voice_clone: VoiceCloneConfig = Field(default_factory=VoiceCloneConfig)
    emotion: EmotionConfig = Field(default_factory=EmotionConfig)
    chapter: ChapterConfig = Field(default_factory=ChapterConfig)
    text_preprocessing: TextPreprocessingConfig = Field(default_factory=TextPreprocessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    model_download: ModelDownloadConfig = Field(default_factory=ModelDownloadConfig)

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "Settings":
        """从 YAML 文件加载配置"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        # 处理环境变量替换
        config_data = cls._resolve_env_vars(config_data)
        
        return cls(**config_data)
    
    @staticmethod
    def _resolve_env_vars(data: Any) -> Any:
        """递归解析环境变量"""
        if isinstance(data, dict):
            return {k: Settings._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Settings._resolve_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        return data
    
    def merge_with_api_params(self, api_params: Dict[str, Any]) -> "Settings":
        """合并 API 参数，返回新的配置对象"""
        # 创建当前配置的副本
        config_dict = self.model_dump()
        
        # 递归合并 API 参数
        self._deep_merge(config_dict, api_params)
        
        return Settings(**config_dict)
    
    @staticmethod
    def _deep_merge(base: Dict, update: Dict) -> None:
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Settings._deep_merge(base[key], value)
            else:
                base[key] = value


@lru_cache()
def get_settings(config_path: str = "config.yaml") -> Settings:
    """获取配置单例"""
    return Settings.from_yaml(config_path)

