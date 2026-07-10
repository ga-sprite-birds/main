# GA Sprite Birds - 使用指南

> 将文本转换为高质量音频，支持单角色/多角色配音、LLM 口语化、章节拆分

---

## 📋 功能列表

| 功能 | 说明 | CLI | API |
|------|------|:---:|:---:|
| **单角色配音** | 整章统一音色，快速生成 | ✅ | ✅ |
| **多角色配音** | 智能识别对话，为每个角色分配不同音色 | ✅ | ✅ |
| **角色分析** | 自动提取小说角色，生成配音模板 | ✅ | ✅ |
| **LLM 口语化** | 将书面语转换为自然口语 | ✅ | ✅ |
| **章节拆分** | 自动识别章节标题，独立生成 | ✅ | ✅ |
| **多语言界面** | 支持中文/英文界面切换 | ✅ | ✅ |
| **TTS 试听工具** | 快速试听 Edge TTS 所有音色 | ✅ | ✅ |

**支持格式**：
- 📄 输入：`.txt`, `.pdf`
- 🎵 输出：`.mp3`
- 🌐 TTS：Edge TTS（免费，550+ 音色）
- 🤖 LLM：Ollama（本地）/ OpenAI API（云端）

---

## 1️⃣ 单角色配音

最简单的使用方式，整本书使用同一个音色。

### CLI 使用

```bash
# 基本使用（使用配置文件的默认音色）
python fcgi-bin/cli.py -i input.txt

# 指定音色
python fcgi-bin/cli.py -i input.txt --voice zh-CN-YunxiNeural

# 禁用 LLM 处理（更快，但不口语化）
python fcgi-bin/cli.py -i input.txt --no-llm

# 只生成第 1-5 章
python fcgi-bin/cli.py -i input.txt --start 1 --end 5

# 指定输出目录
python fcgi-bin/cli.py -i input.txt -o ./my_output
```

### API 使用

```bash
# 1. 启动服务
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000

# 2. 上传文件
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input.txt"
# 返回: {"task_id": "abc123", "status": "pending"}

# 3. 解析章节
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "abc123"}'

# 4. 生成音频
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "voice": "zh-CN-YunxiNeural",
    "enable_llm": true
  }'

# 5. 查询进度
curl "http://localhost:8000/task/abc123/status"

# 6. 下载音频
curl "http://localhost:8000/task/abc123/chapter/1" --output chapter_1.mp3
```

**输出**：
```
output/input/
├── 001-第一章.mp3
├── 002-第二章.mp3
└── ...
```

---

## 2️⃣ 多角色配音

为小说中的每个角色分配不同音色，让对话更生动。需要两步：**角色分析** → **多角色生成**。

### 步骤 1：角色分析

#### CLI 使用

```bash
# 智能模式：自动分析角色并合并重复角色
python fcgi-bin/cli.py -i novel.txt --analyze-characters

# 混合模式：使用用户提供的角色列表
python fcgi-bin/cli.py -i novel.txt --analyze-characters \
  --analysis-mode hybrid \
  --character-list characters.txt
```

**角色列表文件格式** (`characters.txt`)：
```
张三 male
李四 female
王五
```

#### API 使用

> 注意：角色分析（character analysis）当前版本仅通过 CLI 提供（`--analyze-characters`，见上方「CLI 使用」）。分析完成后会生成角色模板文件 `cache/role/novel_characters.json`，该模板可在下方的「多角色生成」API 中通过 `character_template` 参数引用。

**输出**：生成角色模板文件 `cache/role/novel_characters.json`

```json
{
  "张三": {
    "gender": "male",
    "voice": "zh-CN-YunxiNeural"
  },
  "李四": {
    "gender": "female",
    "voice": "zh-CN-XiaoxiaoNeural"
  }
}
```

### 步骤 2：多角色生成

#### CLI 使用

```bash
# 使用自动生成的角色模板
python fcgi-bin/cli.py -i novel.txt --multi-voice true

# 使用指定的角色模板
python fcgi-bin/cli.py -i novel.txt --multi-voice true \
  --character-template cache/role/custom_characters.json

# 只生成第 1-3 章（测试用）
python fcgi-bin/cli.py -i novel.txt --multi-voice true \
  --start 1 --end 3
```

#### API 使用

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "multi_voice": true,
    "character_template": "cache/role/novel_characters.json",
    "enable_llm": true
  }'
```

**输出**：
```
output/novel/
├── 001-第一章.mp3
├── 001-第一章.txt  # 包含角色对话标注
├── 002-第二章.mp3
└── ...
```

---

## 3️⃣ TTS 试听工具

快速试听 Edge TTS 的 550+ 音色，找到最适合的声音。

### CLI 使用

```bash
# 列出所有中文音色
python utils/try_tts/cli.py list --lang zh-CN

# 列出中文男声
python utils/try_tts/cli.py list --lang zh-CN --gender male

# 列出中文女声
python utils/try_tts/cli.py list --lang zh-CN --gender female

# 生成所有中文音色的试听音频
python utils/try_tts/cli.py generate --lang zh-CN

# 生成指定音色的试听音频
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural

# 自定义试听文本
python utils/try_tts/cli.py generate --lang zh-CN \
  --text "这是我的试听文本"

# 导出音色列表为文档
python utils/try_tts/cli.py list --lang zh-CN --save-doc voices.md

# 英文界面
python utils/try_tts/cli.py list --lang en-US --language en_US
```

### API 使用

TTS 试听工具是独立的 CLI 工具，不提供 API 接口。

**输出**：
```
output/tts_samples/
├── zh-CN-XiaoxiaoNeural.mp3
├── zh-CN-YunxiNeural.mp3
└── ...
```

---

## 4️⃣ 多语言界面

支持中文/英文界面切换，包括帮助文本、日志消息、API 响应等。

### CLI 使用

```bash
# 英文界面
python fcgi-bin/cli.py --help --language en_US

# 中文界面
python fcgi-bin/cli.py --help --language zh_CN

# 使用英文界面生成音频
python fcgi-bin/cli.py -i input.txt --language en_US
```

### API 使用

```bash
# 使用中文界面
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input.txt" \
  -F "language=zh_CN"

# 使用英文界面
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "language": "en_US"
  }'
```

### 配置文件（全局默认）

```env
# .env 文件
LANGUAGE=en_US  # 或 zh_CN
```

**优先级**：CLI/API 参数 > 配置文件 > 默认值（en_US）

---

## 5️⃣ LLM 口语化

将书面语转换为自然口语，让朗读更流畅。支持本地（Ollama）和云端（OpenAI API）两种模式。

### CLI 使用

```bash
# 启用 LLM（默认）
python fcgi-bin/cli.py -i input.txt

# 禁用 LLM（更快，但不口语化）
python fcgi-bin/cli.py -i input.txt --no-llm
```

### API 使用

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "enable_llm": true
  }'
```

### 配置 LLM 引擎

```env
# .env 文件

# 本地模式（Ollama）
LLM_MODE=local
LLM_LOCAL_HOST=http://localhost:11434
LLM_LOCAL_MODEL=deepseek-r1:7b

# API 模式（OpenAI）
LLM_MODE=api
LLM_API_KEY=your_api_key
LLM_API_MODEL=deepseek-chat
LLM_API_ENDPOINT=https://api.deepseek.com/v1
```

---

## 6️⃣ 章节范围控制

只生成指定章节，节省时间和资源。

### CLI 使用

```bash
# 只生成第 1 章
python fcgi-bin/cli.py -i input.txt --start 1 --end 1

# 生成第 1-5 章
python fcgi-bin/cli.py -i input.txt --start 1 --end 5

# 从第 10 章开始生成到最后
python fcgi-bin/cli.py -i input.txt --start 10
```

### API 使用

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "start_chapter": 1,
    "end_chapter": 5
  }'
```

---

## 7️⃣ 音色和语速

自定义音色和语速，打造个性化朗读体验。

### CLI 使用

```bash
# 指定音色
python fcgi-bin/cli.py -i input.txt --voice zh-CN-YunxiNeural

# 指定语速（0.5-2.0，1.0 为正常）
python fcgi-bin/cli.py -i input.txt --rate 1.2

# 同时指定音色和语速
python fcgi-bin/cli.py -i input.txt \
  --voice zh-CN-XiaoxiaoNeural \
  --rate 1.1
```

### API 使用

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "voice": "zh-CN-YunxiNeural",
    "rate": 1.2
  }'
```

### 配置文件（全局默认）

```env
# .env 文件
TTS_VOICE=zh-CN-XiaoxiaoNeural
TTS_RATE=1.0
```

---

## 8️⃣ 输出路径

自定义输出目录和文件格式。

### CLI 使用

```bash
# 指定输出目录
python fcgi-bin/cli.py -i input.txt -o ./my_output

# 输出到绝对路径
python fcgi-bin/cli.py -i input.txt -o /path/to/output
```

### API 使用

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input.txt" \
  -F "output_path=./my_output"
```

### 配置文件（全局默认）

```env
# .env 文件
OUTPUT_BASE_PATH=./output
OUTPUT_FORMAT=mp3
OUTPUT_BITRATE=192
```

---

## 📚 参考文档

- [开发规范](./development-guide.zh.md) - 开发者必读
- [安装指南](./INSTALL.zh.md) - 环境安装说明

---

**更新时间**：2025-12-01
**维护者**：GA Sprite Birds 开发团队

