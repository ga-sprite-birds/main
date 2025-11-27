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
│   ├── Common/             # 公共基础模块
│   ├── Utils/              # 通用工具模块
│   ├── Parser/             # 解析器模块
│   ├── LLM/                # LLM 调用模块
│   ├── Audio/              # 音频处理模块
│   ├── character_analyzer/ # 角色分析模块（多角色专用）
│   ├── Task/               # 任务管理模块（API 专用）
│   └── Sprite/             # 精灵管理模块（API 专用）
├── cache/                  # 缓存目录
│   ├── audio_temp/         # 临时音频文件
│   ├── dialogue/           # 对话解析缓存
│   └── role/               # 角色模板缓存
├── output/                 # 输出目录
├── models/                 # AI 模型文件
├── logs/                   # 日志目录
├── tests/                  # 单元测试
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
| TTSManager | `tts_manager.py` | TTS 引擎管理（Edge TTS / 本地 TTS） |
| AudioExporter | `audio_exporter.py` | 音频导出路径管理 |
| AudioMerger | `audio_merger.py` | 音频合并（多角色模式） |
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

**职责**：API 模式的任务队列管理

---

#### Sprite（精灵管理）

**位置**：`ga_birds/Sprite/`

**职责**：API 模式的精灵资源管理

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
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000
```

**特点**：
- FastAPI HTTP 服务
- 异步任务
- 适合 Web 服务、远程调用

---

## 4. 配音模式

### 4.1 单角色配音

**流程**：
```
文本文件 
  → 章节拆分（ChapterParser）
  → [可选] LLM 口语化（LLMManager）
  → 添加片头片尾（ChapterProcessor）
  → TTS 生成音频（TTSManager）
  → 保存文本（ChapterTextSaver）
```

**特点**：
- 整章内容一次性生成
- 使用单一音色
- 流程简单，速度快

---

### 4.2 多角色配音

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

## 5. 配置管理

### 5.1 配置文件

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

# ===== TTS 配置 =====
TTS_MODE=api                    # api（Edge TTS）/ local（本地 TTS）
TTS_VOICE=zh-CN-XiaoxiaoNeural  # 默认音色
TTS_RATE=1.0                    # 语速
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
CHAPTER_REGEX_PATTERNS=["^第[0-9一二三四五六七八九十百千]+[章回节].*$"]
CHAPTER_MIN_LENGTH=100
CHAPTER_KEEP_TITLE=false
CHAPTER_INTRO_OUTRO_ENABLED=true
CHAPTER_INTRO_TEMPLATE=第{index}章开始
CHAPTER_OUTRO_TEMPLATE=本章播讲完毕

# ===== 输出配置 =====
OUTPUT_DIR=./output
OUTPUT_FORMAT=mp3
OUTPUT_DUPLICATE_HANDLING=rename  # skip / rename / overwrite
```

### 5.2 配置访问

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

## 6. 开发规范

### 6.1 模块职责划分

| 模块类型 | 职责 | 示例 | 禁止 |
|---------|------|------|------|
| **Common** | 公共基础设施 | 配置管理、参数管理、片头片尾 | 业务逻辑、LLM 调用 |
| **Utils** | 独立工具函数 | 文件读写、Token 计算 | 依赖业务模块 |
| **业务模块** | 具体业务逻辑 | 对话解析、角色分析、TTS 生成 | 放在 Common 中 |

### 6.2 代码组织原则

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

### 6.3 命名规范

**文件命名**：
- 使用小写 + 下划线：`chapter_processor.py`
- 避免缩写：`manager.py` 而非 `mgr.py`

**类命名**：
- 使用大驼峰：`ChapterProcessor`
- 管理器类：`XXXManager`
- 解析器类：`XXXParser`

**函数命名**：
- 使用小写 + 下划线：`prepare_intro_outro()`
- 布尔函数：`is_enabled()`, `has_content()`

**常量命名**：
- 使用大写 + 下划线：`MAX_TOKENS`, `DEFAULT_VOICE`

### 6.4 导入规范

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

## 7. 业务流程规范

### 7.1 单角色配音流程

```python
# 1. 读取文件
content = read_file(input_file)

# 2. 章节拆分
parser = ChapterParser()
chapters = parser.parse(content)

# 3. 处理每章
for chapter in chapters:
    # 3.1 LLM 口语化（可选）
    if enable_llm:
        content = llm_manager.colloquialize_text(chapter.content)

    # 3.2 添加片头片尾
    intro, outro = ChapterProcessor.prepare_intro_outro(
        chapter.index, chapter.title
    )
    final_content = ChapterProcessor.combine_content_with_intro_outro(
        content, intro, outro
    )

    # 3.3 TTS 生成
    await tts_manager.generate_audio(
        text=final_content,
        output_path=audio_path
    )

    # 3.4 保存文本
    ChapterTextSaver.save_single_voice_text(
        audio_path, final_content
    )
```

### 7.2 多角色配音流程

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

## 8. 测试规范

### 8.1 单元测试

**位置**：`tests/`

**命名规范**：
- 测试文件：`test_<模块名>.py`
- 测试类：`Test<类名>`
- 测试方法：`test_<功能描述>`

**示例**：
```python
# tests/test_common/test_chapter_processor.py
class TestChapterProcessor:
    def test_prepare_intro_outro(self):
        intro, outro = ChapterProcessor.prepare_intro_outro(1, "第一章")
        assert intro is not None
        assert outro is not None
```

**运行测试**：
```bash
python -m pytest tests/ -v --tb=short
```

### 8.2 集成测试

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

## 9. 常见问题与解决方案

### 9.1 多角色配音内容不完整

**原因**：LLM 输出 token 限制导致 JSON 输出被截断

**解决方案**：
- `DialogueParser` 自动计算输出限制：`max(4096, 输入长度 * 4 / 3)`
- 支持分块处理：`DIALOGUE_CHUNK_SIZE=3000`

### 9.2 音频有破音

**原因**：多角色模式合并音频时未指定比特率

**解决方案**：
- `AudioMerger` 使用配置的比特率：`OUTPUT_BITRATE=192`

### 9.3 Edge TTS 请求失败

**原因**：请求频率过高被限流

**解决方案**：
- 系统有自动重试机制
- 等待一段时间后重试

---

## 10. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-01-27 | 初始版本，定义模块结构和开发规范 |

---

## 11. 参考文档

- [项目通用开发规范](../.augment/rules/imported/python.md)
- [安装指南](../INSTALL.md)
- [README](../README.md)

---

**原稿**：2025-01-27
**更新时间**：2025-01-27
**维护者**：GA Sprite Birds 开发团队

