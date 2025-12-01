# Edge TTS 配音试听工具

## 📋 概述

Edge TTS 配音试听工具用于获取 Microsoft Edge TTS 支持的所有音色列表，并生成试听音频文件。

## 🎯 功能特性

- ✅ 获取所有可用音色列表
- ✅ 支持按语言筛选（如 zh-CN, en-US）
- ✅ 支持按性别筛选（男/女）
- ✅ 生成单个音色试听音频
- ✅ 批量生成多个音色试听音频
- ✅ 自动保存生成结果（JSON + Markdown 双格式）
- ✅ 失败自动重试机制（等待 3 秒后重试一次）
- ✅ 文件重名自动处理（Windows 风格：file.mp3 → file (1).mp3）
- ✅ 导出音色列表为 Markdown 文档
- ✅ **多语言支持**（英语/中文，可通过 CLI 参数或环境变量切换）

## 🚀 快速开始

### 1. 列出所有音色

```bash
# 列出所有音色
python utils/try_tts/cli.py list

# 列出中文音色
python utils/try_tts/cli.py list --lang zh-CN

# 列出中文男声
python utils/try_tts/cli.py list --lang zh-CN --gender male

# 列出中文女声
python utils/try_tts/cli.py list --lang zh-CN --gender female
```

### 2. 生成试听音频

```bash
# 生成指定音色的试听音频
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural

# 批量生成所有中文音色的试听音频
python utils/try_tts/cli.py generate --lang zh-CN

# 批量生成中文男声试听音频
python utils/try_tts/cli.py generate --lang zh-CN --gender male

# 使用自定义试听文本
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural --text "这是自定义的试听文本"

# 指定输出目录
python utils/try_tts/cli.py generate --lang zh-CN --output ./my_samples
```

### 3. 导出音色列表文档

```bash
# 导出所有音色列表为 Markdown
python utils/try_tts/cli.py list --save-doc voices.md

# 导出中文音色列表
python utils/try_tts/cli.py list --lang zh-CN --save-doc zh-CN-voices.md
```

## 🌍 多语言支持

工具支持**英语**和**中文**界面输出，可通过以下方式切换：

### 方式 1：环境变量（推荐）

修改项目根目录的 `.env` 文件：

```env
# 英语界面（默认）
LANGUAGE=en_US

# 中文界面
LANGUAGE=zh_CN
```

### 方式 2：CLI 参数

```bash
# 使用英语界面
python utils/try_tts/cli.py list --language en_US

# 使用中文界面
python utils/try_tts/cli.py list --language zh_CN
```

### 方式 3：独立运行（自动检测）

如果工具独立运行（不在项目环境中），会自动使用本地翻译文件：
- 优先级：**本地翻译文件 > 项目多语言 > 硬编码默认翻译**
- 本地翻译文件位置：`utils/try_tts/langues/`
- **说明：** 工具优先使用自己的翻译文件，确保帮助文本等工具专属内容正确显示

### 示例对比

**英语界面**：
```
📡 Fetching voice list...
✓ Fetched successfully, 550 voices available
📋 Filter: Language=zh-CN, Gender=All
```

**中文界面**：
```
📡 正在获取音色列表...
✓ 获取成功，共 550 个音色
📋 筛选条件: 语言=zh-CN, 性别=全部
```

### 注意事项

- `--lang` 参数：筛选**音色的语言**（如 zh-CN, en-US）
- `--language` 参数：设置**界面输出语言**（en_US, zh_CN）
- `.env` 的 `LANGUAGE`：全局设置**界面输出语言**

---

## 📖 命令行参数

### 操作类型

- `list` - 列出音色列表
- `generate` - 生成试听音频

### 筛选参数

- `--lang <语言代码>` - 按音色语言筛选（如 zh-CN, en-US, ja-JP）
- `--gender <性别>` - 按性别筛选
  - `male` 或 `1` - 男声
  - `female` 或 `0` - 女声

### 生成参数

- `--voice <音色名称>` - 指定单个音色（如 zh-CN-XiaoxiaoNeural）
- `--text <文本>` - 自定义试听文本
- `--output <目录>` - 输出目录（默认 `./output/tts_samples`）

### 导出参数

- `--save-doc <文件路径>` - 保存音色列表为 Markdown 文档

### 界面语言参数

- `--language <语言代码>` - 设置界面输出语言（en_US, zh_CN）

## 📁 输出文件

### 试听音频

生成的试听音频文件命名格式：`{音色名称}.mp3`

示例：
```
output/tts_samples/
├── voices.json                      # 生成结果（JSON 格式）
├── voices.md                        # 生成结果（Markdown 格式）
├── zh-CN-XiaoxiaoNeural.mp3
├── zh-CN-YunxiNeural.mp3
├── zh-CN-XiaoyiNeural.mp3
└── ...
```

### 生成结果文件

#### voices.json（JSON 格式）

```json
{
  "code": 1,
  "msg": "全部生成成功",
  "data": {
    "generated_at": "2025-12-01 14:30:00",
    "filter": {
      "language": "zh-CN",
      "gender": "全部"
    },
    "output_dir": "./output/tts_samples",
    "total": 38,
    "success": 34,
    "failed": 4,
    "voices": [
      {
        "name": "zh-CN-XiaoxiaoNeural",
        "gender": "Female",
        "language": "zh-CN",
        "friendly_name": "Microsoft Xiaoxiao Online (Natural) - Chinese (Mainland)",
        "audio_file": "output/tts_samples/zh-CN-XiaoxiaoNeural.mp3",
        "status": "success"
      },
      {
        "name": "zh-CN-XiaoshuangMultilingualNeural",
        "gender": "Female",
        "language": "zh-CN",
        "friendly_name": "Microsoft Xiaoshuang Multilingual Online (Natural)",
        "audio_file": null,
        "status": "failed",
        "error": "No audio was received. Please verify that your parameters are correct."
      }
    ]
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码：1=全部成功，2=部分成功，0=异常错误 |
| `msg` | string | 状态消息 |
| `data.generated_at` | string | 生成时间 |
| `data.filter.language` | string | 筛选的语言 |
| `data.filter.gender` | string | 筛选的性别 |
| `data.output_dir` | string | 输出目录 |
| `data.total` | int | 总音色数 |
| `data.success` | int | 成功数量 |
| `data.failed` | int | 失败数量 |
| `data.voices[].name` | string | 音色名称 |
| `data.voices[].gender` | string | 性别 |
| `data.voices[].language` | string | 语言代码 |
| `data.voices[].friendly_name` | string | 友好名称 |
| `data.voices[].audio_file` | string/null | 音频文件路径（失败时为 null） |
| `data.voices[].status` | string | 状态：success / failed |
| `data.voices[].error` | string | 错误信息（仅失败时存在） |

#### voices.md（Markdown 格式）

包含：
- 生成时间、筛选条件、统计信息
- 生成结果表格（状态、姓名、性别、语言、音频文件）
- 失败详情（如有失败项）

## 🎨 常用音色推荐

### 中文音色

| 音色名称 | 性别 | 特点 |
|---------|------|------|
| zh-CN-XiaoxiaoNeural | 女 | 温柔、自然 |
| zh-CN-YunxiNeural | 男 | 沉稳、清晰 |
| zh-CN-XiaoyiNeural | 女 | 活泼、年轻 |
| zh-CN-YunjianNeural | 男 | 成熟、磁性 |

### 英文音色

| 音色名称 | 性别 | 特点 |
|---------|------|------|
| en-US-JennyNeural | 女 | 标准美音 |
| en-US-GuyNeural | 男 | 标准美音 |
| en-GB-SoniaNeural | 女 | 标准英音 |
| en-GB-RyanNeural | 男 | 标准英音 |

## 💡 使用技巧

1. **快速试听中文音色**
   ```bash
   python utils/try_tts/cli.py generate --lang zh-CN
   # 自动生成 voices.json 和 voices.md
   ```

2. **只试听男声**
   ```bash
   python utils/try_tts/cli.py generate --lang zh-CN --gender male
   ```

3. **导出完整音色列表供参考**
   ```bash
   python utils/try_tts/cli.py list --save-doc all-voices.md
   ```

4. **测试特定音色效果**
   ```bash
   python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural --text "这是一段测试文本，用于评估音色效果。"
   ```

5. **使用中文界面**
   ```bash
   python utils/try_tts/cli.py list --lang zh-CN --language zh_CN
   # 或修改 .env: LANGUAGE=zh_CN
   ```

6. **查看生成结果**
   ```bash
   # 查看 JSON 结果（可用于 API 集成）
   cat output/tts_samples/voices.json

   # 查看 Markdown 结果（人类可读）
   cat output/tts_samples/voices.md
   ```

## 🔧 开发说明

### 目录结构

```
utils/try_tts/
├── __init__.py          # 包初始化
├── cli.py               # 命令行入口
├── voice_fetcher.py     # 音色列表获取器
├── sample_generator.py  # 试听音频生成器
├── doc_exporter.py      # 文档导出器
├── i18n.py              # 多语言管理器
├── langues/             # 本地翻译文件
│   ├── en_US.json       # 英文翻译
│   └── zh_CN.json       # 中文翻译
└── README.md            # 工具说明文档
```

### 核心模块

- **VoiceFetcher**: 从 Edge TTS API 获取音色列表并支持筛选
- **SampleGenerator**: 生成试听音频文件
- **DocExporter**: 导出音色列表为 Markdown 文档
- **UtilsI18n**: 多语言管理器（支持三层回退机制）

## 🔄 自动重试机制

当音频生成失败时，工具会自动：
1. 等待 3 秒
2. 重试一次
3. 如果仍然失败，记录错误信息并继续处理下一个

失败的音色会在 `voices.json` 和 `voices.md` 中标记为 `failed` 状态。

## 📝 注意事项

1. 需要网络连接才能获取音色列表和生成音频
2. 批量生成时会按顺序逐个生成，请耐心等待
3. 生成的音频文件为 MP3 格式
4. 默认试听文本为中文，可通过 `--text` 参数自定义
5. 文件重名会自动处理（如 `file.mp3` → `file (1).mp3`）
6. 每次批量生成都会自动保存 `voices.json` 和 `voices.md`

## 🆘 常见问题

**Q: 如何查看所有支持的语言？**

A: 运行 `python utils/try_tts/cli.py list` 查看所有音色，从 Locale 列可以看到支持的语言代码。

**Q: 生成失败怎么办？**

A: 工具会自动重试一次。如果仍然失败，会在 `voices.json` 和 `voices.md` 中记录失败原因。检查网络连接，确保可以访问 Microsoft Edge TTS 服务。

**Q: 如何切换界面语言？**

A:
- 方式 1：修改 `.env` 文件中的 `LANGUAGE=zh_CN`
- 方式 2：使用 `--language zh_CN` 参数
- 方式 3：工具独立运行时自动使用本地翻译文件

**Q: 如何在项目中使用这些音色？**

A: 在 `.env` 文件中设置 `TTS_VOICE` 参数，或在命令行中使用 `--voice` 参数指定。

**Q: voices.json 可以直接用于 API 吗？**

A: 可以。JSON 格式包含 `code`、`msg`、`data` 字段，符合标准 API 响应格式，可以直接返回给前端。

