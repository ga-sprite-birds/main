"""
GA Sprite Birds - Configuration management
Simple configuration approach using environment variables + default values

Version: v2.0
Dev team: Tiger
"""

import os
from dotenv import load_dotenv

# Automatically load the .env file
load_dotenv()

# ========== LLM configuration ==========

# ENABLE_LLM: Whether to enable LLM colloquialization
# Purpose: Controls whether to apply LLM colloquialization to the text
# Allowed values: 'true' (enabled), 'false' (disabled)
# Effect: When disabled, audio is generated directly from the original text, skipping LLM processing
# Recommendation: Recommended for audiobook projects; can be disabled for quick testing
ENABLE_LLM = os.getenv('ENABLE_LLM', 'true').lower() in ('true', '1', 'yes')

# LLM_MODE: LLM runtime mode
# Purpose: Choose between a local model or the API service
# Allowed values: 'local' (local Ollama), 'api' (OpenAI API)
# Effect: Determines which set of LLM configuration to use
# Recommendation: Use 'local' for local development; 'api' can be used in production
LLM_MODE = os.getenv('LLM_MODE', 'local')

# LLM_LOCAL_HOST: Local Ollama service address
# Purpose: Specifies the HTTP address of the Ollama service
# Format: http://host:port
# Recommendation: Default http://localhost:11434
LLM_LOCAL_HOST = os.getenv('LLM_LOCAL_HOST', 'http://localhost:11434')

# LLM_LOCAL_MODEL: Local LLM model name
# Purpose: Specifies the Ollama model to use
# Allowed values: deepseek-r1:7b, llama2:7b, qwen:7b, etc.
# Effect: Directly affects the quality and speed of text colloquialization
# Recommendation: deepseek-r1:7b is recommended for Chinese-language scenarios
LLM_LOCAL_MODEL = os.getenv('LLM_LOCAL_MODEL', 'deepseek-r1:7b')

# LLM_TEMPERATURE: Sampling temperature
# Purpose: Controls the randomness and creativity of generated text
# Range: 0.0-2.0
# Effect: 0.0-0.3 (conservative), 0.5-0.7 (balanced), 0.8-1.0 (creative)
# Recommendation: 0.7 recommended for colloquialization
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))

# LLM_MAX_TOKENS: Maximum number of tokens per single generation
# Purpose: Limits the maximum length of a single LLM output
# Effect: Larger values produce more detailed output but take longer
# Recommendation: 2000-8192, adjust based on chapter length
# Note: For DeepSeek R1 7B, it is recommended not to exceed 8192
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2000'))

# LLM_NUM_CTX: Context window size
# Purpose: Limits the total context length (input + output) the model processes
# Effect: Larger values allow longer text but consume more resources
# Recommendation: DeepSeek R1 7B supports a maximum of 8192
LLM_NUM_CTX = int(os.getenv('LLM_NUM_CTX', '8192'))

# LLM_TIMEOUT: LLM request timeout
# Purpose: Limits the maximum wait time (in seconds) for a single LLM request
# Effect: On timeout, an exception is raised and the original text is used
# Recommendation: 600 (10 minutes); DeepSeek R1 has a longer thinking time
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '600'))

# LLM_API_TYPE: API type
# Purpose: Specifies the API service type
# Allowed values: openai, azure, custom
LLM_API_TYPE = os.getenv('LLM_API_TYPE', 'openai')

# LLM_API_ENDPOINT: API endpoint
# Purpose: The URL address of the API service
LLM_API_ENDPOINT = os.getenv('LLM_API_ENDPOINT', 'https://api.openai.com/v1')

# LLM_API_KEY: API key
# Purpose: Authentication key for accessing the API service
# Recommendation: Sensitive information; must be configured in .env
LLM_API_KEY = os.getenv('LLM_API_KEY')

# LLM_API_MODEL: API model name
# Purpose: Specifies the API model to use
# Allowed values: gpt-4, gpt-3.5-turbo, etc.
LLM_API_MODEL = os.getenv('LLM_API_MODEL', 'gpt-4')

# LLM_SYSTEM_PROMPT: Custom system prompt
# Purpose: Custom behavior instructions for the LLM
# Recommendation: Leave empty to use the default colloquialization prompt
LLM_SYSTEM_PROMPT = os.getenv('LLM_SYSTEM_PROMPT', '')

# ========== Model cache configuration ==========

# MODEL_CACHE_DIR: Model cache directory
# Purpose: Stores downloaded model files
# Recommendation: Use the default path ./models
MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', './models')

# ========== TTS configuration ==========

# TTS_MODE: TTS runtime mode
# Purpose: Choose between a local model or the API service
# Allowed values: 'api' (API service), 'local' (local model)
# Effect: Determines which set of TTS configuration to use
# Recommendation: Use 'api' for quick testing, 'local' for high quality
TTS_MODE = os.getenv('TTS_MODE', 'api')

# TTS_ENGINE: TTS engine type
# Purpose: Specifies the TTS engine to use
# Allowed values: edge
TTS_ENGINE = os.getenv('TTS_ENGINE', 'edge')

# TTS_VOICE: Voice timbre / speaker
# Purpose: Specifies the voice timbre or speaker to use
# Format: zh-CN-YunxiNeural (male), zh-CN-XiaoxiaoNeural (female), etc.
TTS_VOICE = os.getenv('TTS_VOICE', 'zh-CN-YunxiNeural')

# TTS_RATE: Speech rate multiplier
# Purpose: Controls the speech playback speed
# Range: 0.5-2.0, where 1.0 is normal speed
# Effect: Higher is faster, lower is slower
# Recommendation: 0.9-1.2, can be overridden via the CLI --rate argument
# Note: All engines uniformly use the multiplier format
TTS_RATE = float(os.getenv('TTS_RATE', '1.0'))

# TTS_VOLUME: Volume multiplier
# Purpose: Controls the audio volume
# Range: 0.0-2.0, where 1.0 is normal volume
# Effect: Higher is louder, lower is quieter
# Recommendation: 0.8-1.2
# Note: All engines uniformly use the multiplier format
TTS_VOLUME = float(os.getenv('TTS_VOLUME', '1.0'))

# TTS_PITCH: Pitch offset
# Purpose: Controls the audio pitch (high/low)
# Range: -20 to +20 (Hz)
# Effect: Positive values raise the pitch, negative values lower it, 0 is normal
# Recommendation: -10 to +10
# Note: All engines uniformly use the Hz offset format
TTS_PITCH = int(os.getenv('TTS_PITCH', '0'))

# TTS_VOICE_CATALOG_CACHE: Edge TTS voice catalog cache path
# Purpose: Cache the fetched Edge voice list locally to avoid repeated network calls
# Format: JSON file path
# Default: ./cache/voices/edge_voices.json
TTS_VOICE_CATALOG_CACHE = os.getenv(
    'TTS_VOICE_CATALOG_CACHE',
    './cache/voices/edge_voices.json'
)

# ========== Chapter configuration ==========

# CHAPTER_REGEX_PATTERNS: Chapter recognition regular expressions
# Purpose: List of regex patterns used to recognize chapter titles
# Format: Comma-separated list of regular expression strings
CHAPTER_REGEX_PATTERNS = os.getenv(
    'CHAPTER_REGEX_PATTERNS',
    '^第[零一二三四五六七八九十百千万0-9]+[章回卷节](?![\\u4e00-\\u9fff]),^第[零一二三四五六七八九十百千万0-9]+卷(?![\\u4e00-\\u9fff])'
).split(',')

# CHAPTER_NORMALIZE_ENABLED: Whether to normalize irregular chapter headings
# Purpose: Converts Markdown-style headings (e.g. "**第一章**", "## 第一章")
#          into a canonical "第一章 ..." format before chapter splitting,
#          so ChapterParser does not need per-article rules
CHAPTER_NORMALIZE_ENABLED = os.getenv('CHAPTER_NORMALIZE_ENABLED', 'true').lower() == 'true'

# CHAPTER_MIN_LENGTH: Minimum chapter length
# Purpose: Filters out chapters that are too short to avoid false recognition
# Unit: Number of characters
# Recommendation: 100-200
CHAPTER_MIN_LENGTH = int(os.getenv('CHAPTER_MIN_LENGTH', '100'))

# CHAPTER_KEEP_TITLE: Whether to keep the chapter title
# Purpose: Controls whether the generated audio includes the chapter title
CHAPTER_KEEP_TITLE = os.getenv('CHAPTER_KEEP_TITLE', 'true').lower() == 'true'

# CHAPTER_INTRO_OUTRO: Whether to enable intro/outro
# Purpose: Controls whether to add prompts at the beginning and end of a chapter
CHAPTER_INTRO_OUTRO = os.getenv('CHAPTER_INTRO_OUTRO', 'true').lower() == 'true'

# CHAPTER_INTRO_TEMPLATE: Intro template
# Purpose: Prompt at the start of a chapter, supports {index}, {title} variables
# Note: This is a personal preference; set it to whatever language you want spoken
CHAPTER_INTRO_TEMPLATE = os.getenv('CHAPTER_INTRO_TEMPLATE', '第{index}章开始')

# CHAPTER_OUTRO_TEMPLATE: Outro template
# Purpose: Prompt at the end of a chapter
# Note: This is a personal preference; set it to whatever language you want spoken
CHAPTER_OUTRO_TEMPLATE = os.getenv('CHAPTER_OUTRO_TEMPLATE', '本章播讲完毕')

# CHAPTER_INTRO_OUTRO_PAUSE: Intro/outro pause duration
# Purpose: Pause duration before and after the intro/outro
# Implementation: Simulates pauses with ellipses (each ellipsis is about 0.3 seconds)
# Note: Edge TTS does not support SSML break tags, so ellipses are used instead
# Unit: Seconds
# Recommendation: 0.5-2.0
CHAPTER_INTRO_OUTRO_PAUSE = float(os.getenv('CHAPTER_INTRO_OUTRO_PAUSE', '1.0'))

# ========== Text preprocessing configuration ==========

# TEXT_PREPROCESSING_ENABLED: Whether to enable text preprocessing
# Purpose: Controls whether to clean and normalize the input text
TEXT_PREPROCESSING_ENABLED = os.getenv('TEXT_PREPROCESSING_ENABLED', 'true').lower() == 'true'

# ========== Output configuration ==========

# OUTPUT_BASE_PATH: Output base path
# Purpose: Output directory for audio files
OUTPUT_BASE_PATH = os.getenv('OUTPUT_BASE_PATH', './output')

# OUTPUT_STRATEGY: Output strategy
# Purpose: Controls how the output directory is organized
# Allowed values: by_role (by character), by_model (by model), by_date (by date)
OUTPUT_STRATEGY = os.getenv('OUTPUT_STRATEGY', 'by_role')

# OUTPUT_FORMAT: Audio format
# Purpose: Output audio file format
# Allowed values: mp3, m4a, wav
OUTPUT_FORMAT = os.getenv('OUTPUT_FORMAT', 'mp3')

# OUTPUT_BITRATE: Audio bitrate
# Purpose: Controls audio quality and file size
# Unit: kbps
# Recommendation: 128 (standard), 192 (high quality), 320 (very high quality)
OUTPUT_BITRATE = int(os.getenv('OUTPUT_BITRATE', '128'))

# OUTPUT_FILENAME_TEMPLATE: Filename template
# Purpose: Controls the naming format of output files
# Supported variables: {index}, {title}, {role}, {date}, {format}
OUTPUT_FILENAME_TEMPLATE = os.getenv('OUTPUT_FILENAME_TEMPLATE', '{index:03d}-{title}.{format}')

# OUTPUT_KEEP_TEMP_FILES: Keep temporary files
# Purpose: Whether to keep temporary files generated during processing
OUTPUT_KEEP_TEMP_FILES = os.getenv('OUTPUT_KEEP_TEMP_FILES', 'false').lower() == 'true'

# OUTPUT_DUPLICATE_HANDLING: Duplicate file handling
# Purpose: How to handle a file that already exists
# Allowed values: overwrite, rename, skip
OUTPUT_DUPLICATE_HANDLING = os.getenv('OUTPUT_DUPLICATE_HANDLING', 'rename')

# OUTPUT_SAVE_CHAPTER_TEXT: Save chapter text
# Purpose: Whether to save chapter text for proofreading
OUTPUT_SAVE_CHAPTER_TEXT = os.getenv('OUTPUT_SAVE_CHAPTER_TEXT', 'true').lower() == 'true'

# OUTPUT_CHAPTER_TEXT_ENCODING: Chapter text encoding
# Purpose: Encoding used when saving chapter text
OUTPUT_CHAPTER_TEXT_ENCODING = os.getenv('OUTPUT_CHAPTER_TEXT_ENCODING', 'utf-8')

# ========== Logging configuration ==========

# LOG_LEVEL: Log level
# Purpose: Controls the verbosity of log output
# Allowed values: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# LOG_FORMAT: Log format
# Purpose: Defines the format of log output
LOG_FORMAT = os.getenv('LOG_FORMAT', '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}')

# LOG_FILE: Log file path
# Purpose: Specifies where the log file is saved
LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')

# LOG_MAX_FILE_SIZE: Maximum log file size
# Purpose: Maximum size of a single log file (MB)
LOG_MAX_FILE_SIZE = int(os.getenv('LOG_MAX_FILE_SIZE', '10'))

# LOG_BACKUP_COUNT: Log backup count
# Purpose: Number of log file backups to retain
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

# LOG_CONSOLE: Whether to output to the console
# Purpose: Controls whether to also output logs to the console
LOG_CONSOLE = os.getenv('LOG_CONSOLE', 'true').lower() == 'true'

# ========== API service configuration ==========

# API_HOST: API service listening address
# Purpose: Specifies the IP address the FastAPI service listens on
# Recommendation: Use 127.0.0.1 for development, 0.0.0.0 for production
API_HOST = os.getenv('API_HOST', '0.0.0.0')

# API_PORT: API service port
# Purpose: Specifies the port the FastAPI service listens on
API_PORT = int(os.getenv('API_PORT', '8000'))

# API_DEBUG: Debug mode
# Purpose: Whether to enable FastAPI debug mode
API_DEBUG = os.getenv('API_DEBUG', 'true').lower() == 'true'

# API_CORS_ENABLED: Whether to enable CORS
# Purpose: Controls whether cross-origin requests are allowed
API_CORS_ENABLED = os.getenv('API_CORS_ENABLED', 'true').lower() == 'true'

# API_CORS_ORIGINS: Allowed cross-origin sources
# Purpose: Specifies the list of allowed cross-origin sources
# Format: Comma-separated list of URLs; * means allow all sources
API_CORS_ORIGINS = os.getenv('API_CORS_ORIGINS', '*').split(',')

# API_MAX_UPLOAD_SIZE: Maximum upload file size
# Purpose: Limits the maximum size of uploaded files (MB)
API_MAX_UPLOAD_SIZE = int(os.getenv('API_MAX_UPLOAD_SIZE', '100'))

# API_UPLOAD_DIR: Upload file storage directory
# Purpose: Specifies where the API stores uploaded files
# Note: This config is for internal API use only and is not exposed to users
# Default: ./uploads
API_UPLOAD_DIR = os.getenv('API_UPLOAD_DIR', './uploads')

# ========== Task configuration ==========

# TASK_QUEUE_TYPE: Task queue type
# Purpose: Specifies the task queue implementation
# Allowed values: memory (in-memory queue), redis (Redis queue)
# Recommendation: Use 'memory' for development, 'redis' for production
TASK_QUEUE_TYPE = os.getenv('TASK_QUEUE_TYPE', 'memory')

# TASK_MAX_CONCURRENT: Maximum concurrent tasks
# Purpose: Limits the number of tasks running simultaneously
TASK_MAX_CONCURRENT = int(os.getenv('TASK_MAX_CONCURRENT', '3'))

# TASK_TIMEOUT: Task timeout
# Purpose: Maximum execution time for a single task (seconds)
TASK_TIMEOUT = int(os.getenv('TASK_TIMEOUT', '3600'))

# TASK_RESULT_TTL: Task result retention time
# Purpose: How long task results are retained in the system (seconds)
TASK_RESULT_TTL = int(os.getenv('TASK_RESULT_TTL', '86400'))

# ========== Redis configuration ==========

# REDIS_HOST: Redis server address
# Purpose: Specifies the IP address of the Redis server
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')

# REDIS_PORT: Redis server port
# Purpose: Specifies the port of the Redis server
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

# REDIS_DB: Redis database number
# Purpose: Specifies the Redis database number to use
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# REDIS_PASSWORD: Redis password
# Purpose: Authentication password for the Redis server
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# ========== Character analysis configuration ==========

# ENABLE_MULTI_VOICE: Whether to enable multi-character voice
# Purpose: Controls whether to use LLM to analyze characters and assign a different voice to each
# Allowed values: 'true' (enable multi-character), 'false' (single voice)
# Effect: When enabled, characters are auto-analyzed and assigned voices; when disabled, uses TTS_VOICE
# Recommendation: Recommended for audiobook projects; can be disabled for quick testing
# Default: false (single-character mode)
ENABLE_MULTI_VOICE = os.getenv('ENABLE_MULTI_VOICE', 'false').lower() in ('true', '1', 'yes')

# CHARACTER_ANALYSIS_MODE: Character analysis mode
# Purpose: Controls the character analysis approach
# Allowed values:
#   - 'auto': Smart analysis mode, the LLM auto-discovers all characters
#   - 'hybrid': Hybrid mode, user specifies the character list, and the LLM analyzes aliases and personality
# Effect:
#   - auto mode: Duplicate characters may appear and need to be merged later
#   - hybrid mode: Higher accuracy, but requires the user to provide a character list
# Recommendation: Use 'auto' the first time, then switch to 'hybrid' for refinement
# Default: auto
CHARACTER_ANALYSIS_MODE = os.getenv('CHARACTER_ANALYSIS_MODE', 'auto').lower()

# CHARACTER_CACHE_DIR: Character data cache directory
# Purpose: Stores the JSON files of character analysis results
# Recommendation: Use the default path ./cache/role
CHARACTER_CACHE_DIR = os.getenv('CHARACTER_CACHE_DIR', './cache/role')

# CHARACTER_MAX_CONTENT_LENGTH: Maximum content length for character analysis
# Purpose: Limits the length (in characters) of chapter content sent to the LLM
# Effect: Larger values yield more accurate analysis but take longer
# Recommendation: 3000-5000
CHARACTER_MAX_CONTENT_LENGTH = int(os.getenv('CHARACTER_MAX_CONTENT_LENGTH', '3000'))

# DIALOGUE_CHUNK_SIZE: Dialogue parsing chunk size
# Purpose: Long chapters are split into chunks of this size to avoid LLM output truncation
# Recommendation: 3000-4000
DIALOGUE_CHUNK_SIZE = int(os.getenv('DIALOGUE_CHUNK_SIZE', '3000'))

# DIALOGUE_CHUNK_OVERLAP: Dialogue parsing chunk overlap
# Purpose: Ensures contextual coherence at chunk boundaries
# Recommendation: 100-300
DIALOGUE_CHUNK_OVERLAP = int(os.getenv('DIALOGUE_CHUNK_OVERLAP', '200'))

# SEGMENT_ENABLE_LANGUAGE_ANALYSIS: Whether to attach language metadata to each parsed segment
# Purpose: Enables per-segment language routing for multilingual dialogue
SEGMENT_ENABLE_LANGUAGE_ANALYSIS = os.getenv(
    'SEGMENT_ENABLE_LANGUAGE_ANALYSIS',
    'true'
).lower() in ('true', '1', 'yes')

# SEGMENT_ENABLE_EMOTION_ANALYSIS: Whether to attach emotion/tone metadata to each parsed segment
# Purpose: Enables dynamic TTS parameter adjustments for dialogue segments
SEGMENT_ENABLE_EMOTION_ANALYSIS = os.getenv(
    'SEGMENT_ENABLE_EMOTION_ANALYSIS',
    'true'
).lower() in ('true', '1', 'yes')

# SEGMENT_MAX_RATE_DELTA: Maximum allowed per-segment deviation from the base TTS rate
# Purpose: Prevents LLM-suggested speaking rates from becoming too extreme
SEGMENT_MAX_RATE_DELTA = float(os.getenv('SEGMENT_MAX_RATE_DELTA', '0.25'))

# SEGMENT_MAX_PITCH_DELTA: Maximum allowed per-segment deviation from the base TTS pitch
# Purpose: Prevents LLM-suggested pitch shifts from becoming too extreme
SEGMENT_MAX_PITCH_DELTA = int(os.getenv('SEGMENT_MAX_PITCH_DELTA', '8'))

# SEGMENT_MAX_VOLUME_DELTA: Maximum allowed per-segment deviation from the base TTS volume
# Purpose: Prevents LLM-suggested volume shifts from becoming too extreme
SEGMENT_MAX_VOLUME_DELTA = float(os.getenv('SEGMENT_MAX_VOLUME_DELTA', '0.15'))

# VOICE_PREFER_REGION_MATCH: Whether to prioritize region/accent hints when selecting voices
# Purpose: Allows character profile region hints to influence locale selection
VOICE_PREFER_REGION_MATCH = os.getenv(
    'VOICE_PREFER_REGION_MATCH',
    'true'
).lower() in ('true', '1', 'yes')

# PERSONALITY_TAGS: Personality tag library
# Purpose: Predefined character personality tags, used as a reference when the LLM analyzes character personalities
# Usage: Intended for future emotional voice casting, adjusting TTS parameters based on character personality
PERSONALITY_TAGS = {
    # Personality traits
    "性格": [
        "热血", "冷静", "冲动", "理智", "善良", "邪恶",
        "勇敢", "胆小", "自信", "自卑", "乐观", "悲观",
        "开朗", "内向", "外向", "孤僻", "温柔", "暴躁"
    ],

    # Speaking style
    "说话": [
        "直接", "委婉", "大声", "轻声", "快速", "缓慢",
        "幽默", "严肃", "啰嗦", "简洁", "粗鲁", "礼貌",
        "尖锐", "温和"
    ],

    # Emotional tendency
    "情绪": [
        "激动", "平静", "易怒", "温和", "焦虑", "淡定",
        "热情", "冷漠", "敏感", "迟钝", "多愁善感", "豁达"
    ],

    # Social role
    "角色": [
        "长辈", "晚辈", "领导", "下属", "老师", "学生",
        "严父", "慈母", "智者", "愚者", "导师", "学徒"
    ],

    # Other characteristics
    "其他": [
        "传统", "现代", "固执", "灵活", "狡猾", "单纯",
        "圆滑", "耿直", "势利", "正直", "慈祥", "严厉",
        "谨慎", "鲁莽", "细心", "粗心"
    ]
}

# ========== FFmpeg configuration ==========

# FFMPEG_PATH: FFmpeg executable directory
# Purpose: Specifies the directory containing ffmpeg and ffprobe
# Note: If empty, the system PATH ffmpeg is used
# Recommendation: Windows users are advised to configure this path to avoid environment variable issues
# Example: F:/soft/ffmpeg/bin
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '')

# ========== Project configuration ==========

# CORE_DIR: Core module directory name
# Purpose: Specifies the directory name of the project's core module
# Default value: ga_birds
# Note: If you change the core directory name, you must update this config accordingly
CORE_DIR = os.getenv('CORE_DIR', 'ga_birds')

# ========== Multilingual configuration ==========

# LANGUAGE: System language
# Purpose: Sets the language for the system UI and output
# Allowed values: en_US (English), zh_CN (Simplified Chinese), ja_JP (Japanese)
# Effect: Language of CLI output, API responses, and log messages
# Recommendation: Choose based on the user base; default is English
# Default: en_US
LANGUAGE = os.getenv('LANGUAGE', 'en_US')
