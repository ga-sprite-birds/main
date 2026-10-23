# GA Sprite Birds 开发规范

本文档定义了 GA Sprite Birds 项目的开发标准与规范，包括模块结构、代码组织、业务流程、配置管理等核心开发规范。

**项目简介**：GA Sprite Birds 是一个智能音频朗读系统，支持将文本（小说、文章）转换为高质量音频，支持单角色和多角色配音模式。

---

## 1. 项目目录结构

```
ga-sprite-birds/
├── config/                 # 配置模块（根目录）
│   ├── __init__.py         # 配置加载器
│   └── defaults.py         # 默认配置（如需要）
├── fcgi-bin/               # 对外统一入口
│   ├── api.py              # FastAPI HTTP 服务入口
│   └── cli.py              # CLI 命令行入口
├── ga_birds/               # 核心业务模块（CORE_DIR）
│   ├── Common/             # 公共基础模块（章节加载、i18n、文本保存）
│   ├── Utils/              # 通用工具模块
│   ├── Parser/             # 解析器模块
│   ├── LLM/                # LLM 调用模块
│   ├── Audio/              # 音频处理模块（章节生成器、TTS、导出）
│   ├── character_analyzer/ # 角色分析模块（多角色专用）
│   └── Task/               # 任务管理与 JSON 持久化
├── gui/                    # Vue 3 + Element Plus 前端源码
├── cache/                  # 缓存目录
│   ├── audio_temp/         # 临时音频文件
│   ├── dialogue/           # 对话解析缓存
│   ├── role/               # 角色模板缓存
│   └── tasks/              # 任务记录（完成后自动删除）
├── output/                 # 输出目录
├── uploads/                # API 上传的源文件
├── models/                 # AI 模型文件
├── logs/                   # 日志目录
├── tests/                  # 单元测试与集成测试
├── help/                   # 开发文档
├── .env                    # 环境配置文件
└── requirements.txt        # Python 依赖
```

---

## 2. 模块分类与职责

### 2.1 公共基础模块（Common）

**位置**：`ga_birds/Common/`

**职责**：提供 CLI 和 API 共用的基础设施，**不包含业务逻辑**。

**包含模块**：

| 模块 | 文件 | 职责 | 使用场景 |
|------|------|------|----------|
| ConfigManager | `config_manager.py` | 配置管理封装 | 所有模块读取配置 |
| ParamManager | `param_manager.py` | 参数合并与验证 | CLI/API 参数处理 |
| ChapterProcessor | `chapter_processor.py` | 片头片尾处理 | 单角色/多角色通用 |
| ChapterTextSaver | `text_saver.py` | 文本保存 | 单角色/多角色通用 |
| chapter_loader | `chapter_loader.py` | 读取、预处理、规范化并解析章节 | CLI 和 API 共用 |

**设计原则**：
- ✅ 只包含跨业务共享的基础设施
- ❌ 不包含业务逻辑（如对话解析、角色分析）
- ✅ 单角色和多角色模式都能使用
- ✅ 无外部业务依赖

**示例**：
```python
from ga_birds.Common import ChapterProcessor, ChapterTextSaver

# 准备片头片尾（单角色/多角色通用）
intro, outro = ChapterProcessor.prepare_intro_outro(1, "第一章")

# 保存文本（单角色模式）
ChapterTextSaver.save_single_voice_text(audio_path, content)
```

---

### 2.2 工具模块（Utils）

**位置**：`ga_birds/Utils/`

**职责**：提供独立的工具函数，**无业务逻辑**。

**包含模块**：

| 模块 | 文件 | 职责 |
|------|------|------|
| 文件处理 | `file_utils.py` | 文件读写、编码检测、文本预处理 |
| Token 工具 | `token_utils.py` | Token 计算、文本智能分段 |
| 模型管理 | `model_manager.py` | AI 模型下载与管理 |

**设计原则**：
- ✅ 纯工具函数，无状态
- ✅ 可独立测试
- ❌ 不依赖业务模块

**示例**：
```python
from ga_birds.Utils import read_file, preprocess_text

# 智能读取文件（自动识别 .txt/.pdf）
content = read_file("novel.txt")

# 文本预处理
content = preprocess_text(content, remove_extra_newlines=True)
```

---

### 2.3 业务模块

#### Parser（解析器）

**位置**：`ga_birds/Parser/`

**职责**：章节拆分

| 模块 | 文件 | 职责 |
|------|------|------|
| ChapterParser | `chapter_parser.py` | 使用正则表达式识别章节标题，拆分章节 |

---

#### LLM（大语言模型）

**位置**：`ga_birds/LLM/`

**职责**：LLM 调用与文本处理

| 模块 | 文件 | 职责 |
|------|------|------|
| LLMManager | `manager.py` | 统一管理本地（Ollama）和 API（OpenAI）模式的 LLM 调用 |

**功能**：
- 口语化处理（`colloquialize_text`）
- 自动分段处理（超长文本）
- 支持自定义 `max_tokens`

---

#### Audio（音频处理）

**位置**：`ga_birds/Audio/`

**职责**：TTS 生成与音频处理

| 模块 | 文件 | 职责 |
|------|------|------|
| TTSManager | `tts_manager.py` | TTS 引擎管理（当前版本使用 Edge TTS） |
| AudioExporter | `audio_exporter.py` | 音频导出路径管理 |
| AudioMerger | `audio_merger.py` | 音频合并（多角色模式） |
| chapter_generator | `chapter_generator.py` | 单角色章节共享流程（LLM、片头片尾、文本、TTS、重名处理） |
| Engines | `engines/` | TTS 引擎实现 |

---

#### character_analyzer（角色分析）

**位置**：`ga_birds/character_analyzer/`

**职责**：多角色配音专用业务模块

| 模块 | 文件 | 职责 |
|------|------|------|
| CharacterAnalyzer | `analyzer.py` | 从文本中提取角色信息 |
| DialogueParser | `dialogue_parser.py` | 解析对话，识别说话人 |
| VoiceAssigner | `voice_assigner.py` | 为角色分配音色 |
| CharacterListParser | `character_list_parser.py` | 解析用户提供的角色列表 |
| CharacterMerger | `character_merger.py` | 合并重复角色 |

**重要方法**：
```python
# DialogueParser 新增的静态方法（多角色专用）
DialogueParser.add_intro_outro_to_segments(segments, intro, outro)
```

---

#### Task（任务管理）

**位置**：`ga_birds/Task/`

**职责**：内存任务状态、后台生成控制和 API 任务 JSON 持久化。

**任务状态**：

| 状态 | 含义 |
|------|------|
| `pending` | 已上传，尚未解析 |
| `parsing` | 正在解析章节 |
| `parsed` | 章节已就绪，可能有章节待生成 |
| `generating` | 正在生成音频 |
| `paused` | 章节之间暂停 |
| `completed` | 所有章节都有音频；任务记录被删除 |
| `failed` | 章节或任务失败 |
| `cancelled` | 任务已取消 |

任务记录以可读 JSON 原子写入 `TASK_CACHE_DIR`。生成任务会保存参数和 `chapter_indexes` 范围，`/resume` 沿用同一范围。服务启动时，`generating` 任务恢复为 `paused`，被中断的章节重置为 `pending`。超过 `TASK_RESULT_TTL` 的记录会在启动时清理。

---

## 3. 调用方式

### 3.1 CLI 模式

**入口**：`fcgi-bin/cli.py`

**启动方式**：
```bash
bash cli.sh -i <文件> [参数]
```

**特点**：
- 命令行直接执行
- 同步处理
- 适合本地批量生成、调试

---

### 3.2 API 模式

**入口**：`fcgi-bin/api.py`

**启动方式**：
```bash
# 推荐：自动选择空闲端口并打开界面
bash api.sh

# 直接启动（需要 PYTHONPATH）
PYTHONPATH=. python fcgi-bin/api.py
```

`api.sh` 从 `API_PORT`（默认 `8000`）开始寻找空闲端口。API 仅面向本地使用，没有鉴权。

**特点**：
- FastAPI HTTP 服务
- 异步任务
- 适合 Web 服务、远程调用

---

## 4. 重试机制规范

系统采用 **tenacity 库** 实现统一的重试机制，支持指数退避、错误分类、自动日志记录。

### 4.1 重试工具模块

**文件**：`ga_birds/Utils/retry_utils.py`

**核心装饰器**：

```python
from ga_birds.Utils.retry_utils import tts_retry, llm_retry, file_io_retry

# TTS 重试（最多 5 次，指数退避 1s-30s）
@tts_retry
async def generate_tts(text, voice):
    return await edge_tts.communicate(text, voice)

# LLM 重试（最多 3 次，指数退避 1s-10s）
@llm_retry
def call_llm(prompt):
    return ollama.chat(prompt)

# 文件 I/O 重试（最多 3 次，快速重试 100ms-1s）
@file_io_retry
def save_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
```

### 4.2 自定义重试装饰器

```python
from ga_birds.Utils.retry_utils import create_retry_decorator

# 创建自定义重试装饰器
custom_retry = create_retry_decorator(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    retry_exceptions=(ConnectionError, TimeoutError)
)

@custom_retry
async def my_function():
    pass
```

### 4.3 重试策略对比

| 装饰器 | 最大重试次数 | 重试间隔 | 适用场景 |
|--------|------------|---------|---------|
| `tts_retry` | 5 次 | 1s, 2s, 4s, 8s, 16s（最大 30s） | TTS API 请求 |
| `llm_retry` | 3 次 | 1s, 2s, 4s（最大 10s） | LLM 本地/API 调用 |
| `file_io_retry` | 3 次 | 100ms, 200ms, 400ms（最大 1s） | 文件读写操作 |

### 4.4 错误分类

```python
from ga_birds.Utils.retry_utils import RetryableError, NonRetryableError

# 可重试的错误
raise RetryableError("Network timeout")  # 会自动重试

# 不可重试的错误
raise NonRetryableError("Invalid parameter")  # 直接抛出，不重试
```

### 4.5 使用规范

**何时使用重试**：
- ✅ 网络请求（TTS、LLM API）
- ✅ 外部服务调用（Ollama、OpenAI）
- ✅ 文件 I/O 操作（可能被占用）
- ❌ 业务逻辑错误（参数错误、数据验证失败）
- ❌ 用户输入错误

**日志记录**：
- 重试时自动记录 WARNING 级别日志
- 包含重试次数、错误信息、等待时间
- 示例：`WARNING - Attempt 1 failed: Connection timeout, retrying in 1.0s...`

---

## 5. 配音模式

### 5.1 单角色配音

**流程**：
```
文本文件
  → load_chapters()（读取、预处理、规范化、ChapterParser）
  → generate_single_voice_chapter()
      → [可选] LLM 口语化（LLMManager，失败时回退原文）
      → 添加片头片尾（ChapterProcessor）
      → 保存文本（ChapterTextSaver）
      → TTS 生成音频（TTSManager，应用重名策略）
```

CLI 和 API 都必须调用 `load_chapters()` 和 `generate_single_voice_chapter()`，不要在入口中重复实现流程。

**特点**：
- 整章内容一次性生成
- 使用单一音色
- 流程简单，速度快

---

### 5.2 多角色配音

**流程**：
```
文本文件 
  → 章节拆分（ChapterParser）
  → [可选] LLM 口语化（LLMManager）
  → 对话解析（DialogueParser + LLM）
  → 角色音色分配（VoiceAssigner）
  → 添加片头片尾（DialogueParser.add_intro_outro_to_segments）
  → 逐片段 TTS 生成（TTSManager）
  → 音频合并（AudioMerger）
  → 保存文本（ChapterTextSaver）
```

**特点**：
- 需要角色模板（`characters.json`）
- 每个对话片段单独生成
- 支持多音色
- 流程复杂，需要 LLM 解析对话

---

## 6. 配置管理

### 6.1 配置文件

**位置**：`.env`

**加载方式**：
```python
from dotenv import load_dotenv
import os

load_dotenv()
```

**配置分类**：

```env
# ===== 核心模块路径 =====
CORE_DIR=ga_birds

# ===== 多语言配置 =====
LANGUAGE=en_US                  # 系统语言：en_US(英语), zh_CN(简体中文)

# ===== TTS 配置 =====
TTS_ENGINE=edge                 # Edge TTS（当前唯一实现的引擎）
TTS_VOICE=zh-CN-XiaoxiaoNeural  # 默认音色
TTS_RATE=1.0                    # 语速
TTS_CHUNK_MAX_CHARS=2000        # 长文本分块大小（按句子边界）
TTS_CHUNK_TIMEOUT=180           # 单个分块超时（秒）
OUTPUT_BITRATE=192              # 输出比特率

# ===== LLM 配置 =====
LLM_MODE=api                    # api / local（Ollama）
LLM_API_KEY=your_key
LLM_API_MODEL=deepseek-chat
LLM_MAX_TOKENS=2048             # 默认输出限制
LLM_NUM_CTX=8192                # 上下文窗口

# ===== 对话解析配置 =====
DIALOGUE_CHUNK_SIZE=3000        # 对话解析分块大小
DIALOGUE_CHUNK_OVERLAP=200      # 分块重叠

# ===== 章节配置 =====
CHAPTER_REGEX_PATTERNS=^第[零一二三四五六七八九十百千万0-9]+[章回卷节](?![\u4e00-\u9fff]),^第[零一二三四五六七八九十百千万0-9]+卷(?![\u4e00-\u9fff])
CHAPTER_MIN_LENGTH=100
CHAPTER_KEEP_TITLE=true
CHAPTER_NORMALIZE_ENABLED=true  # 解析前规范化 Markdown/加粗标题
CHAPTER_INTRO_OUTRO_ENABLED=true
CHAPTER_INTRO_TEMPLATE=第{index}章开始
CHAPTER_OUTRO_TEMPLATE=本章播讲完毕

# ===== 输出配置 =====
OUTPUT_BASE_PATH=./output
OUTPUT_FORMAT=mp3
OUTPUT_STRATEGY=by_role         # by_role / by_model / by_date / flat
OUTPUT_DUPLICATE_HANDLING=rename  # skip / rename / overwrite

# ===== API 与任务配置 =====
API_MAX_UPLOAD_SIZE=100         # MB；0 表示不限制
API_UPLOAD_DIR=./uploads
TASK_CACHE_DIR=./cache/tasks
TASK_RESULT_TTL=86400           # 秒；0 表示永不过期
```

### 6.2 配置访问

**方式 1：直接访问**（推荐用于简单场景）
```python
import config

device = config.AI_DEVICE
model_dir = config.MODEL_DIR
```

**方式 2：通过 ConfigManager**（推荐用于复杂场景）
```python
from ga_birds.Common import ConfigManager

# 检查功能是否启用
if ConfigManager.is_chapter_intro_outro_enabled():
    intro = ConfigManager.get_chapter_intro_template()
```

---

## 7. 开发规范

### 7.1 模块职责划分

| 模块类型 | 职责 | 示例 | 禁止 |
|---------|------|------|------|
| **Common** | 公共基础设施 | 配置管理、参数管理、片头片尾 | 业务逻辑、LLM 调用 |
| **Utils** | 独立工具函数 | 文件读写、Token 计算 | 依赖业务模块 |
| **业务模块** | 具体业务逻辑 | 对话解析、角色分析、TTS 生成 | 放在 Common 中 |

### 7.2 代码组织原则

1. **Common 模块只包含基础设施**
   - ✅ 配置管理、参数管理
   - ✅ 单角色/多角色通用的功能
   - ❌ 业务逻辑（如对话解析）
   - ❌ 只在某一模式使用的功能

2. **业务逻辑放在对应的业务模块**
   - 多角色专用 → `character_analyzer/`
   - LLM 相关 → `LLM/`
   - 音频处理 → `Audio/`

3. **避免循环依赖**
   - Common 不依赖业务模块
   - Utils 不依赖任何业务模块
   - 业务模块可以依赖 Common 和 Utils

### 7.3 命名规范

#### 7.3.1 文件和目录命名

**Python 文件**：
- 使用小写 + 下划线：`chapter_processor.py`
- 避免缩写：`manager.py` 而非 `mgr.py`

**目录命名**：
- 核心模块目录：使用 `ga_` 前缀 + 项目名，如 `ga_birds`
- 子模块目录：使用大驼峰，如 `Common/`, `Utils/`, `Parser/`
- 缓存目录：使用小写 + 下划线，如 `audio_temp/`, `role/`

**翻译文件**：
- 格式：`<语言代码>.json`
- 示例：`en_US.json`, `zh_CN.json`
- 位置：`<模块>/Langues/` 或 `<模块>/langues/`

#### 7.3.2 代码命名

**类命名**：
- 使用大驼峰：`ChapterProcessor`
- 管理器类：`XXXManager`
- 解析器类：`XXXParser`

**函数命名**：
- 使用小写 + 下划线：`prepare_intro_outro()`
- 布尔函数：`is_enabled()`, `has_content()`

**常量命名**：
- 使用大写 + 下划线：`MAX_TOKENS`, `DEFAULT_VOICE`

**翻译键命名**：
- 使用点号分隔：`cli.help.input`, `common.success`
- 分类清晰：`<模块>.<子分类>.<键名>`
- 示例：
  ```json
  {
    "cli": {
      "help": {
        "input": "Input file path"
      }
    }
  }
  ```

#### 7.3.3 参数命名

**CLI 参数**：
- 长参数：使用小写 + 连字符：`--input-file`, `--log-level`
- 短参数：使用单字母：`-i`, `-o`
- 布尔参数：使用 `--no-` 前缀表示否定：`--no-llm`

**API 参数**：
- 使用小写 + 下划线：`task_id`, `output_path`
- 保持与 Python 命名一致

**环境变量**：
- 使用大写 + 下划线：`LANGUAGE`, `TTS_VOICE`

### 7.4 参数优先级规范

系统采用 **三级参数优先级机制**，确保灵活性和可配置性。

#### 7.4.1 优先级顺序

```
CLI/API 参数 > 环境变量（.env） > 代码默认值
```

**示例**：
```bash
# .env 文件
LANGUAGE=zh_CN
TTS_VOICE=zh-CN-XiaoxiaoNeural

# CLI 参数覆盖配置
python fcgi-bin/cli.py -i input.txt --language en_US --voice zh-CN-YunxiNeural
# 实际使用：language=en_US, voice=zh-CN-YunxiNeural
```

#### 7.4.2 参数合并规则

| 参数类型 | CLI 参数 | API 参数 | 环境变量 | 默认值 | 说明 |
|---------|---------|---------|---------|--------|------|
| **必填参数** | ✅ | ✅ | ❌ | ❌ | 必须通过 CLI/API 提供 |
| **可选参数** | ✅ | ✅ | ✅ | ✅ | 优先级：CLI/API > 环境变量 > 默认值 |
| **系统配置** | ❌ | ❌ | ✅ | ✅ | 只能通过环境变量配置 |

**必填参数示例**：
- CLI: `-i/--input` (输入文件)
- API: `task_id` (任务 ID)

**可选参数示例**：
- `--language` / `language` (界面语言)
- `--voice` / `voice` (音色)
- `--output` / `output_path` (输出路径)

**系统配置示例**：
- `CORE_DIR` (核心模块路径)
- `LLM_API_KEY` (LLM API 密钥)

#### 7.4.3 参数处理实现

**CLI 参数处理**：
```python
# fcgi-bin/cli.py

# 1. 预解析 --language 参数（用于设置帮助文本语言）
if '--language' in sys.argv:
    try:
        lang_index = sys.argv.index('--language')
        if lang_index + 1 < len(sys.argv):
            _default_language = sys.argv[lang_index + 1]
    except (ValueError, IndexError):
        pass

# 2. 设置多语言
_i18n_module.set_locale(_default_language)

# 3. 参数合并（CLI 参数 > 配置文件）
voice = args.voice or config.TTS_VOICE
output_dir = args.output or config.OUTPUT_BASE_PATH
```

**API 参数处理**：
```python
# fcgi-bin/api.py

@app.post("/generate")
async def generate_audio(request: GenerateRequest):
    # 1. 设置语言（如果提供）
    if request.language:
        _i18n_module.set_locale(request.language)

    # 2. 参数合并（API 参数 > 配置文件）
    voice = request.voice or config.TTS_VOICE
    output_path = request.output_path or config.OUTPUT_BASE_PATH
```

### 7.5 导入规范

**动态导入核心模块**：
```python
import importlib
import config

_core_module_name = config.CORE_DIR.replace('-', '_')
_utils_module = importlib.import_module(f'{_core_module_name}.Utils')
```

**标准导入顺序**：
```python
# 1. 标准库
import os
import json
from pathlib import Path

# 2. 第三方库
from loguru import logger
from fastapi import FastAPI

# 3. 项目配置
import config

# 4. 项目模块
from ga_birds.Common import ChapterProcessor
from ga_birds.Utils import read_file
```

---

## 8. 多语言（i18n）规范

### 8.1 多语言架构

系统采用 **分层多语言架构**，支持项目级和工具级翻译。

#### 8.1.1 项目级多语言

**位置**：`ga_birds/Langues/`

**职责**：核心项目的翻译（CLI、API、业务逻辑）

**文件结构**：
```
ga_birds/Langues/
├── en_US.json          # 英语翻译
└── zh_CN.json          # 简体中文翻译
```

**翻译文件示例**：
```json
{
  "common": {
    "success": "Success",
    "failed": "Failed"
  },
  "cli": {
    "description": "GA Sprite Birds - Audio Reading System CLI Mode",
    "help": {
      "input": "Input file path (supports .txt, .pdf)",
      "voice": "Voice (override config, e.g., zh-CN-YunxiNeural)"
    }
  }
}
```

#### 8.1.2 工具级多语言

**位置**：`utils/<工具名>/langues/`

**职责**：独立工具的翻译（如 `utils/try_tts/`）

**特点**：
- ✅ 完全独立，不依赖项目翻译
- ✅ 可作为第三方工具单独使用
- ✅ 支持三级翻译回退机制

**翻译优先级**：
```
本地翻译文件 > 项目多语言 > 硬编码默认值
```

### 8.2 多语言实现

#### 8.2.1 项目级 i18n 实现

**文件**：`ga_birds/Common/i18n.py`

**核心功能**：
```python
class I18n:
    def __init__(self, locale: str = "en_US"):
        self.locale = locale
        self.translations = {}
        self._load_translations()

    def t(self, key: str, **kwargs) -> str:
        """翻译函数，支持点号分隔的键和占位符"""
        keys = key.split('.')
        text = self.translations
        for k in keys:
            if isinstance(text, dict):
                text = text.get(k, key)
            else:
                text = key
                break

        if isinstance(text, str):
            return text.format(**kwargs) if kwargs else text
        return str(text)

# 全局单例
_i18n = None

def t(key: str, **kwargs) -> str:
    """全局翻译函数"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n.t(key, **kwargs)

def set_locale(locale: str):
    """设置语言"""
    global _i18n
    _i18n = I18n(locale)
```

**使用方式**：
```python
from ga_birds.Common.i18n import t, set_locale

# 设置语言
set_locale("zh_CN")

# 使用翻译
print(t('common.success'))  # 输出: 成功
print(t('cli.help.input'))  # 输出: 输入文件路径（支持 .txt, .pdf）

# 使用占位符
print(t('error.file_not_found', path='/path/to/file'))
# 输出: 文件不存在: /path/to/file
```

#### 8.2.2 工具级 i18n 实现

**文件**：`utils/try_tts/i18n.py`

**三级回退机制**：
```python
class UtilsI18n:
    def _load_translations(self):
        """加载翻译（优先级：本地 > 项目 > 硬编码）"""
        # 1. 优先使用本地翻译文件（工具自己的翻译）
        if self._try_load_from_local():
            return
        # 2. 其次尝试项目多语言（如果工具被集成到项目中）
        if self._try_load_from_project():
            return
        # 3. 最后使用硬编码默认翻译
        self._load_hardcoded()
```

### 8.3 多语言开发规范

#### 8.3.1 翻译文件规范

**文件命名**：
- 格式：`<语言代码>.json`
- 语言代码使用下划线：`en_US`, `zh_CN`（不是 `en-US`）

**JSON 结构**：
```json
{
  "模块名": {
    "子分类": {
      "键名": "翻译文本"
    }
  }
}
```

**占位符规范**：
- 使用 Python `.format()` 语法：`{变量名}`
- 示例：`"Found {count} voices"` → `t('voice_count', count=10)`

#### 8.3.2 翻译键命名规范

**分类清晰**：
```json
{
  "common": {},      // 通用翻译
  "cli": {},         // CLI 相关
  "api": {},         // API 相关
  "error": {},       // 错误消息
  "help": {}         // 帮助文本
}
```

**层级合理**：
```json
{
  "cli": {
    "help": {
      "input": "...",
      "output": "..."
    },
    "examples": {
      "basic": "...",
      "advanced": "..."
    }
  }
}
```

**避免重复**：
- ✅ `common.success` → 多处复用
- ❌ `cli.success`, `api.success` → 重复定义

#### 8.3.3 代码中使用翻译

**CLI 帮助文本**：
```python
parser = argparse.ArgumentParser(
    description=t('cli.description'),
    epilog=t('cli.examples.all')
)

parser.add_argument(
    '-i', '--input',
    help=t('cli.help.input')
)
```

**日志消息**：
```python
logger.info(t('processing.start', file=input_file))
logger.error(t('error.file_not_found', path=file_path))
```

**API 响应**：
```python
return {
    "status": "success",
    "message": t('api.upload_success', task_id=task_id)
}
```

### 8.4 多语言参数支持

#### 8.4.1 CLI 多语言参数

**参数定义**：
```python
parser.add_argument(
    '--language',
    choices=['en_US', 'zh_CN'],
    help=t('cli.help.language')
)
```

**预解析机制**：
```python
# 在创建 ArgumentParser 之前预解析 --language
if '--language' in sys.argv:
    try:
        lang_index = sys.argv.index('--language')
        if lang_index + 1 < len(sys.argv):
            _default_language = sys.argv[lang_index + 1]
    except (ValueError, IndexError):
        pass

# 设置语言后再创建 parser（确保帮助文本使用正确语言）
set_locale(_default_language)
parser = argparse.ArgumentParser(...)
```

#### 8.4.2 API 多语言参数

**请求模型**：
```python
class GenerateRequest(BaseModel):
    task_id: str
    voice: Optional[str] = None
    language: Optional[str] = None  # 界面语言
```

**路由处理**：
```python
@app.post("/generate")
async def generate_audio(request: GenerateRequest):
    # 设置语言
    if request.language:
        _i18n_module.set_locale(request.language)

    # 业务逻辑...
```

### 8.5 添加新语言

**步骤**：

1. **创建翻译文件**：
   ```bash
   # 项目级
   cp ga_birds/Langues/en_US.json ga_birds/Langues/ja_JP.json

   # 工具级
   cp utils/try_tts/langues/en_US.json utils/try_tts/langues/ja_JP.json
   ```

2. **翻译所有键值对**：
   ```json
   {
     "common": {
       "success": "成功する",
       "failed": "失敗"
     }
   }
   ```

3. **更新参数选项**：
   ```python
   # CLI
   parser.add_argument(
       '--language',
       choices=['en_US', 'zh_CN', 'ja_JP'],  # 添加新语言
       help=t('cli.help.language')
   )

   # API
   class GenerateRequest(BaseModel):
       language: Optional[str] = None  # 支持 en_US, zh_CN, ja_JP
   ```

4. **更新文档**：
   - 更新 `docs/MULTILINGUAL.md`
   - 更新 `.env` 配置说明

---

## 9. 业务流程规范

### 9.1 单角色配音流程

```python
from ga_birds.Audio import generate_single_voice_chapter
from ga_birds.Common import load_chapters

# 1-2. 读取、预处理、规范化并拆分章节
chapters = load_chapters(input_file)

# 3. 通过共享流程处理每章
for chapter in chapters:
    await generate_single_voice_chapter(
        chapter_index=chapter.index,
        chapter_title=chapter.title,
        content=chapter.content,
        output_dir=output_dir,
        voice=voice,
        rate=rate,
        enable_llm=enable_llm,
        llm_manager=llm_manager,
        tts_manager=tts_manager,
        audio_exporter=audio_exporter,
    )
```

### 9.2 多角色配音流程

```python
# 1-2. 同单角色（读取文件、章节拆分）

# 3. 处理每章
for chapter in chapters:
    # 3.1 LLM 口语化（可选）
    if enable_llm:
        content = llm_manager.colloquialize_text(chapter.content)

    # 3.2 对话解析
    dialogue_parser = DialogueParser(llm_manager, characters)
    segments = dialogue_parser.parse_chapter(content, chapter.index)

    # 3.3 添加片头片尾
    intro, outro = ChapterProcessor.prepare_intro_outro(
        chapter.index, chapter.title
    )
    segments = DialogueParser.add_intro_outro_to_segments(
        segments, intro, outro
    )

    # 3.4 逐片段 TTS 生成
    temp_audio_files = []
    for segment in segments:
        voice = VoiceAssigner.get_voice_for_speaker(
            segment['speaker'], character_template
        )
        await tts_manager.generate_audio(
            text=segment['text'],
            output_path=temp_audio_path,
            voice=voice
        )
        temp_audio_files.append(temp_audio_path)

    # 3.5 音频合并
    audio_merger.merge_audio_files(temp_audio_files, audio_path)

    # 3.6 保存文本
    ChapterTextSaver.save_multi_voice_text(
        audio_path, segments
    )
```

---

## 10. 测试规范

### 10.1 测试目录结构

```
tests/
├── unit/                    # 单元测试（FastAPI TestClient）
│   ├── test_root.py         # 测试根路径
│   ├── test_upload.py       # 测试上传接口
│   ├── test_parse.py        # 测试解析接口
│   ├── test_generate.py     # 测试生成接口
│   ├── test_api_validation.py # 上传/解析/生成校验
│   ├── test_generation_control.py # 暂停、继续与任务控制
│   ├── test_shared_pipeline.py # 共享章节加载与重名处理
│   ├── test_task_persistence.py # JSON 持久化与 TTL
│   ├── test_character_metadata.py # 角色元数据
│   ├── test_dialogue_parser_metadata.py # 对话解析元数据
│   ├── test_text_normalizer.py # 章节标题规范化
│   ├── test_voice_assigner.py # 音色分配
│   └── test_task_status.py  # 测试任务状态
│
├── integration/             # 集成测试（httpx）
│   └── test_full_workflow.py # 完整流程测试
│
├── fixtures/                # 测试数据
│   ├── sample.txt
│   └── sample_multi_chapter.txt
│
├── conftest.py              # pytest 全局配置
├── pytest.ini               # pytest 配置
└── README.md                # 测试文档
```

### 10.2 单元测试（API）

**技术栈**：FastAPI TestClient

**特点**：
- ✅ 不需要启动服务器
- ✅ 测试速度快（毫秒级）
- ✅ 适合测试单个接口逻辑

**示例**：
```python
# tests/unit/test_upload.py
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "api", project_root / "fcgi-bin" / "api.py"
)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

client = TestClient(api_module.app)

@pytest.mark.unit
def test_upload_with_file(sample_text_file):
    """测试文件上传"""
    with open(sample_text_file, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("sample.txt", f, "text/plain")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"
```

**运行单元测试**：
```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定测试文件
pytest tests/unit/test_upload.py -v

# 运行特定测试函数
pytest tests/unit/test_upload.py::test_upload_with_file -v
```

### 10.3 集成测试（API）

**技术栈**：pytest + httpx

**特点**：
- ✅ 真实 HTTP 请求
- ✅ 测试完整流程
- ✅ 模拟真实用户场景

**示例**：
```python
# tests/integration/test_full_workflow.py
import pytest
import httpx

@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_workflow(api_base_url, sample_text_file):
    """测试完整工作流程"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # 1. 上传文件
        with open(sample_text_file, "rb") as f:
            response = await client.post(
                "/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )
        task_id = response.json()["task_id"]

        # 2. 解析文本
        await client.post("/parse", json={"task_id": task_id})

        # 3. 生成音频
        await client.post("/generate", json={"task_id": task_id})

        # 4. 查询状态
        response = await client.get(f"/task/{task_id}/status")
        assert response.status_code == 200
```

**运行集成测试**：
```bash
# 步骤 1: 启动 API 服务器（新终端）
bash api.sh

# 步骤 2: 运行集成测试（另一个终端）
pytest tests/integration -v
```

### 10.4 测试标记

使用 pytest 标记来筛选测试：

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"
```

**标记定义**（`pytest.ini`）：
```ini
markers =
    unit: 单元测试（快速，不需要启动服务）
    integration: 集成测试（需要启动服务）
    slow: 慢速测试（超过 10 秒）
```

### 10.5 测试报告

**生成 HTML 报告**：
```bash
# 安装 pytest-html
pip install pytest-html

# 生成报告
pytest --html=report.html --self-contained-html
```

**测试覆盖率**：
```bash
# 安装 pytest-cov
pip install pytest-cov

# 生成覆盖率报告
pytest --cov=ga_birds --cov=fcgi-bin --cov-report=html
```

### 10.6 功能测试（CLI）

**实际功能测试**：
```bash
# 单角色模式
bash cli.sh -i debug/test.txt --start 1 --end 2

# 多角色模式
bash cli.sh -i debug/test.txt --multi-voice true \
  --character-template cache/role/test_characters.json \
  --start 1 --end 2
```

---

## 11. 常见问题与解决方案

### 11.1 多角色配音内容不完整

**原因**：LLM 输出 token 限制导致 JSON 输出被截断

**解决方案**：
- `DialogueParser` 自动计算输出限制：`max(4096, 输入长度 * 4 / 3)`
- 支持分块处理：`DIALOGUE_CHUNK_SIZE=3000`

### 11.2 音频有破音

**原因**：多角色模式合并音频时未指定比特率

**解决方案**：
- `AudioMerger` 使用配置的比特率：`OUTPUT_BITRATE=192`

### 11.3 Edge TTS 请求失败

**原因**：请求频率过高被限流

**解决方案**：
- 系统有自动重试机制
- 等待一段时间后重试

---

## 12. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-01-27 | 初始版本，定义模块结构和开发规范 |
| v1.1 | 2025-12-01 | 新增多语言规范、参数优先级规范、命名规范 |

---

## 13. 参考文档

- [安装指南](./INSTALL.zh.md)
- [README](./README.zh.md)

---

**原稿**：2025-01-27
**更新时间**：2026-10-23
**维护者**：GA Sprite Birds 开发团队

