# GA Sprite Birds Development Guide

This document defines the development standards and conventions for the GA Sprite Birds project, including core development conventions such as module structure, code organization, business processes, and configuration management.

**Project Overview**: GA Sprite Birds is an intelligent audio narration system that converts text (novels, articles) into high-quality audio, supporting both single-voice and multi-voice narration modes.

---

## 1. Project Directory Structure

```
ga-sprite-birds/
├── config/                 # Configuration module (root directory)
│   ├── __init__.py         # Configuration loader
│   └── defaults.py         # Default configuration (if needed)
├── fcgi-bin/               # Unified external entry point
│   ├── api.py              # FastAPI HTTP service entry point
│   └── cli.py              # CLI command-line entry point
├── ga_birds/               # Core business module (CORE_DIR)
│   ├── Common/             # Common infrastructure module
│   ├── Utils/              # General-purpose utilities module
│   ├── Parser/             # Parser module
│   ├── LLM/                # LLM invocation module
│   ├── Audio/              # Audio processing module
│   ├── character_analyzer/ # Character analysis module (multi-voice only)
│   ├── Task/               # Task management module (API only)
│   └── Sprite/             # Sprite management module (API only)
├── cache/                  # Cache directory
│   ├── audio_temp/         # Temporary audio files
│   ├── dialogue/           # Dialogue parsing cache
│   └── role/               # Character template cache
├── output/                 # Output directory
├── models/                 # AI model files
├── logs/                   # Log directory
├── tests/                  # Unit tests
├── help/                   # Development documentation
├── .env                    # Environment configuration file
└── requirements.txt        # Python dependencies
```

---

## 2. Module Classification and Responsibilities

### 2.1 Common Infrastructure Module (Common)

**Location**: `ga_birds/Common/`

**Responsibility**: Provides the infrastructure shared by both the CLI and the API, and **does not contain business logic**.

**Included modules**:

| Module | File | Responsibility | Usage Scenario |
|--------|------|----------------|----------------|
| ConfigManager | `config_manager.py` | Configuration management wrapper | All modules reading configuration |
| ParamManager | `param_manager.py` | Parameter merging and validation | CLI/API parameter handling |
| ChapterProcessor | `chapter_processor.py` | Intro/outro handling | Common to single-voice/multi-voice |
| ChapterTextSaver | `text_saver.py` | Text saving | Common to single-voice/multi-voice |

**Design principles**:
- ✅ Only contains cross-business shared infrastructure
- ❌ Does not contain business logic (e.g., dialogue parsing, character analysis)
- ✅ Usable in both single-voice and multi-voice modes
- ✅ No external business dependencies

**Example**:
```python
from ga_birds.Common import ChapterProcessor, ChapterTextSaver

# Prepare intro/outro (common to single-voice/multi-voice)
intro, outro = ChapterProcessor.prepare_intro_outro(1, "Chapter 1")

# Save text (single-voice mode)
ChapterTextSaver.save_single_voice_text(audio_path, content)
```

---

### 2.2 Utilities Module (Utils)

**Location**: `ga_birds/Utils/`

**Responsibility**: Provides standalone utility functions, **with no business logic**.

**Included modules**:

| Module | File | Responsibility |
|--------|------|----------------|
| File handling | `file_utils.py` | File read/write, encoding detection, text preprocessing |
| Token utilities | `token_utils.py` | Token calculation, intelligent text segmentation |
| Model management | `model_manager.py` | AI model download and management |

**Design principles**:
- ✅ Pure utility functions, stateless
- ✅ Independently testable
- ❌ Does not depend on business modules

**Example**:
```python
from ga_birds.Utils import read_file, preprocess_text

# Intelligently read a file (auto-detects .txt/.pdf)
content = read_file("novel.txt")

# Text preprocessing
content = preprocess_text(content, remove_extra_newlines=True)
```

---

### 2.3 Business Modules

#### Parser

**Location**: `ga_birds/Parser/`

**Responsibility**: Chapter splitting

| Module | File | Responsibility |
|--------|------|----------------|
| ChapterParser | `chapter_parser.py` | Identifies chapter titles using regular expressions and splits chapters |

---

#### LLM (Large Language Model)

**Location**: `ga_birds/LLM/`

**Responsibility**: LLM invocation and text processing

| Module | File | Responsibility |
|--------|------|----------------|
| LLMManager | `manager.py` | Unified management of LLM invocation in local (Ollama) and API (OpenAI) modes |

**Features**:
- Colloquialization (`colloquialize_text`)
- Automatic segmentation (for overly long text)
- Supports custom `max_tokens`

---

#### Audio

**Location**: `ga_birds/Audio/`

**Responsibility**: TTS generation and audio processing

| Module | File | Responsibility |
|--------|------|----------------|
| TTSManager | `tts_manager.py` | TTS engine management (Edge TTS / local TTS) |
| AudioExporter | `audio_exporter.py` | Audio export path management |
| AudioMerger | `audio_merger.py` | Audio merging (multi-voice mode) |
| Engines | `engines/` | TTS engine implementations |

---

#### character_analyzer

**Location**: `ga_birds/character_analyzer/`

**Responsibility**: Business module dedicated to multi-voice narration

| Module | File | Responsibility |
|--------|------|----------------|
| CharacterAnalyzer | `analyzer.py` | Extracts character information from text |
| DialogueParser | `dialogue_parser.py` | Parses dialogue and identifies speakers |
| VoiceAssigner | `voice_assigner.py` | Assigns voices to characters |
| CharacterListParser | `character_list_parser.py` | Parses a user-provided character list |
| CharacterMerger | `character_merger.py` | Merges duplicate characters |

**Important methods**:
```python
# DialogueParser static method added (multi-voice only)
DialogueParser.add_intro_outro_to_segments(segments, intro, outro)
```

---

#### Task

**Location**: `ga_birds/Task/`

**Responsibility**: Task queue management for API mode

---

#### Sprite

**Location**: `ga_birds/Sprite/`

**Responsibility**: Sprite resource management for API mode

---

## 3. Invocation Methods

### 3.1 CLI Mode

**Entry point**: `fcgi-bin/cli.py`

**How to launch**:
```bash
bash cli.sh -i <file> [parameters]
```

**Characteristics**:
- Runs directly from the command line
- Synchronous processing
- Suitable for local batch generation and debugging

---

### 3.2 API Mode

**Entry point**: `fcgi-bin/api.py`

**How to launch**:
```bash
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000
```

**Characteristics**:
- FastAPI HTTP service
- Asynchronous tasks
- Suitable for web services and remote calls

---

## 4. Retry Mechanism Conventions

The system uses the **tenacity library** to implement a unified retry mechanism, supporting exponential backoff, error classification, and automatic logging.

### 4.1 Retry Utility Module

**File**: `ga_birds/Utils/retry_utils.py`

**Core decorators**:

```python
from ga_birds.Utils.retry_utils import tts_retry, llm_retry, file_io_retry

# TTS retry (up to 5 times, exponential backoff 1s-30s)
@tts_retry
async def generate_tts(text, voice):
    return await edge_tts.communicate(text, voice)

# LLM retry (up to 3 times, exponential backoff 1s-10s)
@llm_retry
def call_llm(prompt):
    return ollama.chat(prompt)

# File I/O retry (up to 3 times, fast retry 100ms-1s)
@file_io_retry
def save_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
```

### 4.2 Custom Retry Decorators

```python
from ga_birds.Utils.retry_utils import create_retry_decorator

# Create a custom retry decorator
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

### 4.3 Retry Strategy Comparison

| Decorator | Max retries | Retry interval | Applicable scenario |
|-----------|-------------|----------------|---------------------|
| `tts_retry` | 5 times | 1s, 2s, 4s, 8s, 16s (max 30s) | TTS API requests |
| `llm_retry` | 3 times | 1s, 2s, 4s (max 10s) | LLM local/API calls |
| `file_io_retry` | 3 times | 100ms, 200ms, 400ms (max 1s) | File read/write operations |

### 4.4 Error Classification

```python
from ga_birds.Utils.retry_utils import RetryableError, NonRetryableError

# Retryable error
raise RetryableError("Network timeout")  # will be retried automatically

# Non-retryable error
raise NonRetryableError("Invalid parameter")  # raised directly, not retried
```

### 4.5 Usage Conventions

**When to use retries**:
- ✅ Network requests (TTS, LLM API)
- ✅ External service calls (Ollama, OpenAI)
- ✅ File I/O operations (may be locked)
- ❌ Business logic errors (invalid parameters, data validation failures)
- ❌ User input errors

**Logging**:
- Automatically logs a WARNING-level message on each retry
- Includes retry count, error message, and wait time
- Example: `WARNING - Attempt 1 failed: Connection timeout, retrying in 1.0s...`

---

## 5. Narration Modes

### 5.1 Single-voice Narration

**Flow**:
```
Text file
  → Chapter splitting (ChapterParser)
  → [Optional] LLM colloquialization (LLMManager)
  → Add intro/outro (ChapterProcessor)
  → TTS audio generation (TTSManager)
  → Save text (ChapterTextSaver)
```

**Characteristics**:
- An entire chapter is generated at once
- Uses a single voice
- Simple flow, fast speed

---

### 5.2 Multi-voice Narration

**Flow**:
```
Text file
  → Chapter splitting (ChapterParser)
  → [Optional] LLM colloquialization (LLMManager)
  → Dialogue parsing (DialogueParser + LLM)
  → Voice assignment (VoiceAssigner)
  → Add intro/outro (DialogueParser.add_intro_outro_to_segments)
  → Per-segment TTS generation (TTSManager)
  → Audio merging (AudioMerger)
  → Save text (ChapterTextSaver)
```

**Characteristics**:
- Requires a character template (`characters.json`)
- Each dialogue segment is generated separately
- Supports multiple voices
- More complex flow, requires LLM dialogue parsing

---

## 6. Configuration Management

### 6.1 Configuration File

**Location**: `.env`

**Loaded by**: `config/__init__.py`

**How it is loaded**:
```python
from dotenv import load_dotenv
import os

load_dotenv()
```

**Configuration categories**:

```env
# ===== Core module path =====
CORE_DIR=ga_birds

# ===== Multilingual configuration =====
LANGUAGE=en_US                  # System language: en_US(English), zh_CN(Simplified Chinese), ja_JP(Japanese)

# ===== TTS configuration =====
TTS_MODE=api                    # api (Edge TTS) / local (local TTS)
TTS_VOICE=zh-CN-XiaoxiaoNeural  # Default voice
TTS_RATE=1.0                    # Speech rate
OUTPUT_BITRATE=192              # Output bitrate

# ===== LLM configuration =====
LLM_MODE=api                    # api / local (Ollama)
LLM_API_KEY=your_key
LLM_API_MODEL=deepseek-chat
LLM_MAX_TOKENS=2048             # Default output limit
LLM_NUM_CTX=8192                # Context window

# ===== Dialogue parsing configuration =====
DIALOGUE_CHUNK_SIZE=3000        # Dialogue parsing chunk size
DIALOGUE_CHUNK_OVERLAP=200      # Chunk overlap

# ===== Chapter configuration =====
CHAPTER_REGEX_PATTERNS=["^第[0-9一二三四五六七八九十百千]+[章回节].*$"]
CHAPTER_MIN_LENGTH=100
CHAPTER_KEEP_TITLE=false
CHAPTER_INTRO_OUTRO_ENABLED=true
CHAPTER_INTRO_TEMPLATE=Chapter {index} begins
CHAPTER_OUTRO_TEMPLATE=This chapter has finished

# ===== Output configuration =====
OUTPUT_BASE_PATH=./output
OUTPUT_FORMAT=mp3
OUTPUT_DUPLICATE_HANDLING=rename  # skip / rename / overwrite
```

### 6.2 Configuration Access

**Method 1: Direct access** (recommended for simple scenarios)
```python
import config

device = config.AI_DEVICE
model_dir = config.MODEL_DIR
```

**Method 2: Via ConfigManager** (recommended for complex scenarios)
```python
from ga_birds.Common import ConfigManager

# Check whether a feature is enabled
if ConfigManager.is_chapter_intro_outro_enabled():
    intro = ConfigManager.get_chapter_intro_template()
```

---

## 7. Development Conventions

### 7.1 Module Responsibility Allocation

| Module type | Responsibility | Example | Forbidden |
|-------------|----------------|---------|-----------|
| **Common** | Common infrastructure | Configuration management, parameter management, intro/outro | Business logic, LLM calls |
| **Utils** | Standalone utility functions | File read/write, token calculation | Depending on business modules |
| **Business modules** | Specific business logic | Dialogue parsing, character analysis, TTS generation | Placing in Common |

### 7.2 Code Organization Principles

1. **Common modules only contain infrastructure**
   - ✅ Configuration management, parameter management
   - ✅ Features common to single-voice/multi-voice
   - ❌ Business logic (e.g., dialogue parsing)
   - ❌ Features used only in a single mode

2. **Business logic goes in the corresponding business module**
   - Multi-voice specific → `character_analyzer/`
   - LLM related → `LLM/`
   - Audio processing → `Audio/`

3. **Avoid circular dependencies**
   - Common does not depend on business modules
   - Utils does not depend on any business module
   - Business modules may depend on Common and Utils

### 7.3 Naming Conventions

#### 7.3.1 File and Directory Naming

**Python files**:
- Use lowercase + underscores: `chapter_processor.py`
- Avoid abbreviations: `manager.py` rather than `mgr.py`

**Directory naming**:
- Core module directory: use `ga_` prefix + project name, e.g., `ga_birds`
- Submodule directories: use PascalCase, e.g., `Common/`, `Utils/`, `Parser/`
- Cache directories: use lowercase + underscores, e.g., `audio_temp/`, `role/`

**Translation files**:
- Format: `<language_code>.json`
- Examples: `en_US.json`, `zh_CN.json`
- Location: `<module>/Langues/` or `<module>/langues/`

#### 7.3.2 Code Naming

**Class naming**:
- Use PascalCase: `ChapterProcessor`
- Manager classes: `XXXManager`
- Parser classes: `XXXParser`

**Function naming**:
- Use lowercase + underscores: `prepare_intro_outro()`
- Boolean functions: `is_enabled()`, `has_content()`

**Constant naming**:
- Use uppercase + underscores: `MAX_TOKENS`, `DEFAULT_VOICE`

**Translation key naming**:
- Use dot-separated notation: `cli.help.input`, `common.success`
- Clear categorization: `<module>.<subcategory>.<key>`
- Example:
  ```json
  {
    "cli": {
      "help": {
        "input": "Input file path"
      }
    }
  }
  ```

#### 7.3.3 Parameter Naming

**CLI parameters**:
- Long parameters: use lowercase + hyphens: `--input-file`, `--log-level`
- Short parameters: use single letters: `-i`, `-o`
- Boolean parameters: use `--no-` prefix for negation: `--no-llm`

**API parameters**:
- Use lowercase + underscores: `task_id`, `output_path`
- Keep consistent with Python naming

**Environment variables**:
- Use uppercase + underscores: `LANGUAGE`, `TTS_VOICE`

### 7.4 Parameter Priority Conventions

The system adopts a **three-tier parameter priority mechanism** to ensure flexibility and configurability.

#### 7.4.1 Priority Order

```
CLI/API parameters > Environment variables (.env) > Code defaults
```

**Example**:
```bash
# .env file
LANGUAGE=zh_CN
TTS_VOICE=zh-CN-XiaoxiaoNeural

# CLI parameters override configuration
python fcgi-bin/cli.py -i input.txt --language en_US --voice zh-CN-YunxiNeural
# Actually used: language=en_US, voice=zh-CN-YunxiNeural
```

#### 7.4.2 Parameter Merging Rules

| Parameter type | CLI parameter | API parameter | Env variable | Default | Notes |
|----------------|---------------|---------------|--------------|---------|-------|
| **Required parameter** | ✅ | ✅ | ❌ | ❌ | Must be provided via CLI/API |
| **Optional parameter** | ✅ | ✅ | ✅ | ✅ | Priority: CLI/API > env variable > default |
| **System config** | ❌ | ❌ | ✅ | ✅ | Can only be configured via env variable |

**Required parameter examples**:
- CLI: `-i/--input` (input file)
- API: `task_id` (task ID)

**Optional parameter examples**:
- `--language` / `language` (UI language)
- `--voice` / `voice` (voice)
- `--output` / `output_path` (output path)

**System config examples**:
- `CORE_DIR` (core module path)
- `LLM_API_KEY` (LLM API key)

#### 7.4.3 Parameter Handling Implementation

**CLI parameter handling**:
```python
# fcgi-bin/cli.py

# 1. Pre-parse the --language parameter (used to set the help text language)
if '--language' in sys.argv:
    try:
        lang_index = sys.argv.index('--language')
        if lang_index + 1 < len(sys.argv):
            _default_language = sys.argv[lang_index + 1]
    except (ValueError, IndexError):
        pass

# 2. Set the locale
_i18n_module.set_locale(_default_language)

# 3. Merge parameters (CLI parameters > config file)
voice = args.voice or config.TTS_VOICE
output_dir = args.output or config.OUTPUT_BASE_PATH
```

**API parameter handling**:
```python
# fcgi-bin/api.py

@app.post("/generate")
async def generate_audio(request: GenerateRequest):
    # 1. Set the language (if provided)
    if request.language:
        _i18n_module.set_locale(request.language)

    # 2. Merge parameters (API parameters > config file)
    voice = request.voice or config.TTS_VOICE
    output_path = request.output_path or config.OUTPUT_BASE_PATH
```

### 7.5 Import Conventions

**Dynamically import the core module**:
```python
import importlib
import config

_core_module_name = config.CORE_DIR.replace('-', '_')
_utils_module = importlib.import_module(f'{_core_module_name}.Utils')
```

**Standard import order**:
```python
# 1. Standard library
import os
import json
from pathlib import Path

# 2. Third-party libraries
from loguru import logger
from fastapi import FastAPI

# 3. Project configuration
import config

# 4. Project modules
from ga_birds.Common import ChapterProcessor
from ga_birds.Utils import read_file
```

---

## 8. Internationalization (i18n) Conventions

### 8.1 Internationalization Architecture

The system adopts a **layered internationalization architecture**, supporting both project-level and utility-level translations.

#### 8.1.1 Project-level Internationalization

**Location**: `ga_birds/Langues/`

**Responsibility**: Translations for the core project (CLI, API, business logic)

**File structure**:
```
ga_birds/Langues/
├── en_US.json          # English translation
└── zh_CN.json          # Simplified Chinese translation
```

**Translation file example**:
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

#### 8.1.2 Utility-level Internationalization

**Location**: `utils/<tool_name>/langues/`

**Responsibility**: Translations for standalone tools (e.g., `utils/try_tts/`)

**Characteristics**:
- ✅ Fully independent, does not depend on project translations
- ✅ Can be used standalone as a third-party tool
- ✅ Supports a three-tier translation fallback mechanism

**Translation priority**:
```
Local translation file > Project internationalization > Hardcoded default value
```

### 8.2 Internationalization Implementation

#### 8.2.1 Project-level i18n Implementation

**File**: `ga_birds/Common/i18n.py`

**Core functionality**:
```python
class I18n:
    def __init__(self, locale: str = "en_US"):
        self.locale = locale
        self.translations = {}
        self._load_translations()

    def t(self, key: str, **kwargs) -> str:
        """Translation function, supports dot-separated keys and placeholders"""
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

# Global singleton
_i18n = None

def t(key: str, **kwargs) -> str:
    """Global translation function"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n.t(key, **kwargs)

def set_locale(locale: str):
    """Set the language"""
    global _i18n
    _i18n = I18n(locale)
```

**Usage**:
```python
from ga_birds.Common.i18n import t, set_locale

# Set the language
set_locale("zh_CN")

# Use translations
print(t('common.success'))  # Output: 成功
print(t('cli.help.input'))  # Output: 输入文件路径（支持 .txt, .pdf）

# Use placeholders
print(t('error.file_not_found', path='/path/to/file'))
# Output: 文件不存在: /path/to/file
```

#### 8.2.2 Utility-level i18n Implementation

**File**: `utils/try_tts/i18n.py`

**Three-tier fallback mechanism**:
```python
class UtilsI18n:
    def _load_translations(self):
        """Load translations (priority: local > project > hardcoded)"""
        # 1. Prefer local translation files (the tool's own translations)
        if self._try_load_from_local():
            return
        # 2. Then try project internationalization (if the tool is integrated into the project)
        if self._try_load_from_project():
            return
        # 3. Finally use hardcoded default translations
        self._load_hardcoded()
```

### 8.3 Internationalization Development Conventions

#### 8.3.1 Translation File Conventions

**File naming**:
- Format: `<language_code>.json`
- Language code uses underscores: `en_US`, `zh_CN` (not `en-US`)

**JSON structure**:
```json
{
  "module_name": {
    "subcategory": {
      "key": "translation text"
    }
  }
}
```

**Placeholder conventions**:
- Use Python `.format()` syntax: `{variable_name}`
- Example: `"Found {count} voices"` → `t('voice_count', count=10)`

#### 8.3.2 Translation Key Naming Conventions

**Clear categorization**:
```json
{
  "common": {},      // General translations
  "cli": {},         // CLI related
  "api": {},         // API related
  "error": {},       // Error messages
  "help": {}         // Help text
}
```

**Reasonable hierarchy**:
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

**Avoid duplication**:
- ✅ `common.success` → reused in multiple places
- ❌ `cli.success`, `api.success` → duplicated definitions

#### 8.3.3 Using Translations in Code

**CLI help text**:
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

**Log messages**:
```python
logger.info(t('processing.start', file=input_file))
logger.error(t('error.file_not_found', path=file_path))
```

**API response**:
```python
return {
    "status": "success",
    "message": t('api.upload_success', task_id=task_id)
}
```

### 8.4 Internationalization Parameter Support

#### 8.4.1 CLI Internationalization Parameter

**Parameter definition**:
```python
parser.add_argument(
    '--language',
    choices=['en_US', 'zh_CN'],
    help=t('cli.help.language')
)
```

**Pre-parsing mechanism**:
```python
# Pre-parse --language before creating the ArgumentParser
if '--language' in sys.argv:
    try:
        lang_index = sys.argv.index('--language')
        if lang_index + 1 < len(sys.argv):
            _default_language = sys.argv[lang_index + 1]
    except (ValueError, IndexError):
        pass

# Set the language before creating the parser (ensures the help text uses the correct language)
set_locale(_default_language)
parser = argparse.ArgumentParser(...)
```

#### 8.4.2 API Internationalization Parameter

**Request model**:
```python
class GenerateRequest(BaseModel):
    task_id: str
    voice: Optional[str] = None
    language: Optional[str] = None  # UI language
```

**Route handling**:
```python
@app.post("/generate")
async def generate_audio(request: GenerateRequest):
    # Set the language
    if request.language:
        _i18n_module.set_locale(request.language)

    # Business logic...
```

### 8.5 Adding a New Language

**Steps**:

1. **Create the translation file**:
   ```bash
   # Project level
   cp ga_birds/Langues/en_US.json ga_birds/Langues/ja_JP.json

   # Utility level
   cp utils/try_tts/langues/en_US.json utils/try_tts/langues/ja_JP.json
   ```

2. **Translate all key-value pairs**:
   ```json
   {
     "common": {
       "success": "成功する",
       "failed": "失敗"
     }
   }
   ```

3. **Update the parameter options**:
   ```python
   # CLI
   parser.add_argument(
       '--language',
       choices=['en_US', 'zh_CN', 'ja_JP'],  # add the new language
       help=t('cli.help.language')
   )

   # API
   class GenerateRequest(BaseModel):
       language: Optional[str] = None  # supports en_US, zh_CN, ja_JP
   ```

4. **Update the documentation**:
   - Update `docs/MULTILINGUAL.md`
   - Update the `.env` configuration description

---

## 9. Business Process Conventions

### 9.1 Single-voice Narration Flow

```python
# 1. Read the file
content = read_file(input_file)

# 2. Split into chapters
parser = ChapterParser()
chapters = parser.parse(content)

# 3. Process each chapter
for chapter in chapters:
    # 3.1 LLM colloquialization (optional)
    if enable_llm:
        content = llm_manager.colloquialize_text(chapter.content)

    # 3.2 Add intro/outro
    intro, outro = ChapterProcessor.prepare_intro_outro(
        chapter.index, chapter.title
    )
    final_content = ChapterProcessor.combine_content_with_intro_outro(
        content, intro, outro
    )

    # 3.3 TTS generation
    await tts_manager.generate_audio(
        text=final_content,
        output_path=audio_path
    )

    # 3.4 Save text
    ChapterTextSaver.save_single_voice_text(
        audio_path, final_content
    )
```

### 9.2 Multi-voice Narration Flow

```python
# 1-2. Same as single-voice (read file, split chapters)

# 3. Process each chapter
for chapter in chapters:
    # 3.1 LLM colloquialization (optional)
    if enable_llm:
        content = llm_manager.colloquialize_text(chapter.content)

    # 3.2 Dialogue parsing
    dialogue_parser = DialogueParser(llm_manager, characters)
    segments = dialogue_parser.parse_chapter(content, chapter.index)

    # 3.3 Add intro/outro
    intro, outro = ChapterProcessor.prepare_intro_outro(
        chapter.index, chapter.title
    )
    segments = DialogueParser.add_intro_outro_to_segments(
        segments, intro, outro
    )

    # 3.4 Per-segment TTS generation
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

    # 3.5 Audio merging
    audio_merger.merge_audio_files(temp_audio_files, audio_path)

    # 3.6 Save text
    ChapterTextSaver.save_multi_voice_text(
        audio_path, segments
    )
```

---

## 10. Testing Conventions

### 10.1 Test Directory Structure

```
tests/
├── unit/                    # Unit tests (FastAPI TestClient)
│   ├── test_root.py         # Test root path
│   ├── test_upload.py       # Test upload endpoint
│   ├── test_parse.py        # Test parse endpoint
│   ├── test_generate.py     # Test generate endpoint
│   └── test_task_status.py  # Test task status
│
├── integration/             # Integration tests (httpx)
│   └── test_full_workflow.py # Full workflow test
│
├── fixtures/                # Test data
│   ├── sample.txt
│   └── sample_multi_chapter.txt
│
├── conftest.py              # pytest global config
├── pytest.ini               # pytest config
└── README.md                # Test docs
```

### 10.2 Unit Tests (API)

**Tech stack**: FastAPI TestClient

**Characteristics**:
- ✅ No need to start a server
- ✅ Fast execution (millisecond level)
- ✅ Suitable for testing individual endpoint logic

**Example**:
```python
# tests/unit/test_upload.py
import pytest
from fastapi.testclient import TestClient
from fcgi-bin.api import app

client = TestClient(app)

@pytest.mark.unit
def test_upload_with_file(sample_text_file):
    """Test file upload"""
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

**Run unit tests**:
```bash
# Run all unit tests
pytest tests/unit -v

# Run a specific test file
pytest tests/unit/test_upload.py -v

# Run a specific test function
pytest tests/unit/test_upload.py::test_upload_with_file -v
```

### 10.3 Integration Tests (API)

**Tech stack**: pytest + httpx

**Characteristics**:
- ✅ Real HTTP requests
- ✅ Tests the complete flow
- ✅ Simulates real user scenarios

**Example**:
```python
# tests/integration/test_full_workflow.py
import pytest
import httpx

@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_workflow(api_base_url, sample_text_file):
    """Test the complete workflow"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # 1. Upload the file
        with open(sample_text_file, "rb") as f:
            response = await client.post(
                "/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )
        task_id = response.json()["task_id"]

        # 2. Parse the text
        await client.post("/parse", json={"task_id": task_id})

        # 3. Generate audio
        await client.post("/generate", json={"task_id": task_id})

        # 4. Query status
        response = await client.get(f"/task/{task_id}/status")
        assert response.status_code == 200
```

**Run integration tests**:
```bash
# Step 1: Start the API server (new terminal)
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000

# Step 2: Run integration tests (another terminal)
pytest tests/integration -v
```

### 10.4 Test Markers

Use pytest markers to filter tests:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

**Marker definitions** (`pytest.ini`):
```ini
markers =
    unit: Unit tests (fast, no server needed)
    integration: Integration tests (requires a running server)
    slow: Slow tests (over 10 seconds)
```

### 10.5 Test Reports

**Generate HTML report**:
```bash
# Install pytest-html
pip install pytest-html

# Generate report
pytest --html=report.html --self-contained-html
```

**Test coverage**:
```bash
# Install pytest-cov
pip install pytest-cov

# Generate coverage report
pytest --cov=ga_birds --cov=fcgi-bin --cov-report=html
```

### 10.6 Functional Tests (CLI)

**Actual functional tests**:
```bash
# Single-voice mode
bash cli.sh -i debug/test.txt --start 1 --end 2

# Multi-voice mode
bash cli.sh -i debug/test.txt --multi-voice true \
  --character-template cache/role/test_characters.json \
  --start 1 --end 2
```

---

## 11. FAQ and Solutions

### 11.1 Incomplete Multi-voice Narration Content

**Cause**: The LLM's output token limit causes the JSON output to be truncated

**Solution**:
- `DialogueParser` automatically calculates the output limit: `max(4096, input_length * 4 / 3)`
- Supports chunked processing: `DIALOGUE_CHUNK_SIZE=3000`

### 11.2 Audio Has Crackling/Popping

**Cause**: The bitrate was not specified when merging audio in multi-voice mode

**Solution**:
- `AudioMerger` uses the configured bitrate: `OUTPUT_BITRATE=192`

### 11.3 Edge TTS Request Failed

**Cause**: Rate-limited due to excessive request frequency

**Solution**:
- The system has an automatic retry mechanism
- Wait a while before retrying

---

## 12. Version History

| Version | Date | Description |
|---------|------|-------------|
| v1.0 | 2025-01-27 | Initial version; defines module structure and development conventions |
| v1.1 | 2025-12-01 | Added internationalization conventions, parameter priority conventions, and naming conventions |

---

## 13. References

- [Project General Development Conventions](../.augment/rules/imported/python.md)
- [Installation Guide](./INSTALL.md)
- [README](../README.md)

---

**Original draft**: 2025-01-27
**Last updated**: 2025-12-01
**Maintainer**: GA Sprite Birds Development Team

---

**Author:** adam
**Email:** dev@ebf.hk
**Website:** http://ebf.cc
**Source:** https://github.com/tiger-sprite/ga-sprite-birds
