# GA Sprite Birds - User Guide

> Convert text into high-quality audio, with support for single-character/multi-character voice acting, LLM-based colloquialization, and chapter splitting.

---

## 📋 Features

| Feature | Description | CLI | API |
|---------|-------------|:---:|:---:|
| **Single-character voice** | Uniform voice across a whole chapter, fast generation | ✅ | ✅ |
| **Multi-character voice** | Intelligently identify dialogue and assign a different voice to each character | ✅ | ✅ |
| **Character analysis** | Automatically extract novel characters and generate a voice-acting template | ✅ | ❌ |
| **LLM colloquialization** | Convert written text into natural spoken language | ✅ | ✅ |
| **Chapter splitting** | Automatically detect chapter titles and generate them independently | ✅ | ✅ |
| **Multilingual interface** | Switch between Chinese/English interfaces | ✅ | ✅ |
| **TTS preview tool** | Quickly preview all Edge TTS voices | ✅ | ❌ |

**Supported formats**:
- 📄 Input: `.txt`, `.pdf`
- 🎵 Output: `.mp3`
- 🌐 TTS: Edge TTS (free, 550+ voices)
- 🤖 LLM: Ollama (local) / OpenAI API (cloud)

---

## 1️⃣ Single-character voice

The simplest way to use it — the entire book uses a single voice.

### CLI usage

```bash
# Basic usage (uses the default voice from the config file)
python fcgi-bin/cli.py -i input.txt

# Specify a voice
python fcgi-bin/cli.py -i input.txt --voice zh-CN-YunxiNeural

# Disable LLM processing (faster, but text is not colloquialized)
python fcgi-bin/cli.py -i input.txt --no-llm

# Generate only chapters 1-5
python fcgi-bin/cli.py -i input.txt --start 1 --end 5

# Specify the output directory
python fcgi-bin/cli.py -i input.txt -o ./my_output
```

### API usage

```bash
# 1. Start the service
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000

# 2. Upload a file
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input.txt"
# Returns: {"task_id": "abc123", "status": "pending"}

# 3. Parse chapters
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "abc123"}'

# 4. Generate audio
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "voice": "zh-CN-YunxiNeural",
    "enable_llm": true
  }'

# 5. Check progress
curl "http://localhost:8000/task/abc123/status"

# 6. Download audio
curl "http://localhost:8000/task/abc123/chapter/1" --output chapter_1.mp3
```

**Output**:
```
output/input/
├── 001-第一章.mp3
├── 002-第二章.mp3
└── ...
```

---

## 2️⃣ Multi-character voice

Assign a different voice to each character in the novel to make the dialogue more vivid. This takes two steps: **character analysis** → **multi-character generation**.

### Step 1: Character analysis

#### CLI usage

```bash
# Smart mode: automatically analyze characters and merge duplicates
python fcgi-bin/cli.py -i novel.txt --analyze-characters

# Hybrid mode: use a user-provided character list
python fcgi-bin/cli.py -i novel.txt --analyze-characters \
  --analysis-mode hybrid \
  --character-list characters.txt
```

**Character list file format** (`characters.txt`):
```
张三 male
李四 female
王五
```

#### API usage

> Note: Character analysis is currently CLI-only (via `--analyze-characters`, see "CLI usage" above). After analysis completes, a character template file `cache/role/*.json` is generated; this template can be referenced in the "Multi-character generation" API below via the `character_template` parameter.

**Output**: generates a character template file `cache/role/novel_characters.json`

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

### Step 2: Multi-character generation

#### CLI usage

```bash
# Use the auto-generated character template
python fcgi-bin/cli.py -i novel.txt --multi-voice true

# Use a specified character template
python fcgi-bin/cli.py -i novel.txt --multi-voice true \
  --character-template cache/role/custom_characters.json

# Generate only chapters 1-3 (for testing)
python fcgi-bin/cli.py -i novel.txt --multi-voice true \
  --start 1 --end 3
```

#### API usage

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

**Output**:
```
output/novel/
├── 001-第一章.mp3
├── 001-第一章.txt  # contains character dialogue annotations
├── 002-第二章.mp3
└── ...
```

---

## 3️⃣ TTS preview tool

Quickly preview the 550+ voices of Edge TTS to find the most suitable one.

If you prefer to try voices directly in the browser first, you can also use the official Edge TTS website:
[https://edge-tts.com](https://edge-tts.com)

### CLI usage

```bash
# List all Chinese voices
python utils/try_tts/cli.py list --lang zh-CN

# List Chinese male voices
python utils/try_tts/cli.py list --lang zh-CN --gender male

# List Chinese female voices
python utils/try_tts/cli.py list --lang zh-CN --gender female

# Generate preview audio for all Chinese voices
python utils/try_tts/cli.py generate --lang zh-CN

# Generate preview audio for a specific voice
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural

# Custom preview text
python utils/try_tts/cli.py generate --lang zh-CN \
  --text "这是我的试听文本"

# Export the voice list as documentation
python utils/try_tts/cli.py list --lang zh-CN --save-doc voices.md

# English interface
python utils/try_tts/cli.py list --lang en-US --language en_US
```

### API usage

The TTS preview tool is a standalone CLI tool and does not provide an API interface.

**Output**:
```
output/tts_samples/
├── zh-CN-XiaoxiaoNeural.mp3
├── zh-CN-YunxiNeural.mp3
└── ...
```

---

## 4️⃣ Multilingual interface

Supports switching between Chinese/English interfaces, including help text, log messages, and API responses.

### CLI usage

```bash
# English interface
python fcgi-bin/cli.py --help --language en_US

# Chinese interface
python fcgi-bin/cli.py --help --language zh_CN

# Generate audio using the English interface
python fcgi-bin/cli.py -i input.txt --language en_US
```

### API usage

```bash
# Use the Chinese interface
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input.txt" \
  -F "language=zh_CN"

# Use the English interface
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "language": "en_US"
  }'
```

### Configuration file (global default)

```env
# .env file
LANGUAGE=en_US  # or zh_CN
```

**Priority**: CLI/API parameter > config file > default value (en_US)

---

## 5️⃣ LLM colloquialization

Convert written text into natural spoken language for smoother narration. Supports both local (Ollama) and cloud (OpenAI API) modes.

### CLI usage

```bash
# Enable LLM (default)
python fcgi-bin/cli.py -i input.txt

# Disable LLM (faster, but text is not colloquialized)
python fcgi-bin/cli.py -i input.txt --no-llm
```

### API usage

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "enable_llm": true
  }'
```

### Configure the LLM engine

```env
# .env file

# Local mode (Ollama)
LLM_MODE=local
LLM_LOCAL_HOST=http://localhost:11434
LLM_LOCAL_MODEL=deepseek-r1:7b

# API mode (OpenAI)
LLM_MODE=api
LLM_API_KEY=your_api_key
LLM_API_MODEL=deepseek-chat
LLM_API_ENDPOINT=https://api.deepseek.com/v1
```

---

## 6️⃣ Chapter range control

Generate only specified chapters to save time and resources.

### CLI usage

```bash
# Generate only chapter 1
python fcgi-bin/cli.py -i input.txt --start 1 --end 1

# Generate chapters 1-5
python fcgi-bin/cli.py -i input.txt --start 1 --end 5

# Generate starting from chapter 10 to the end
python fcgi-bin/cli.py -i input.txt --start 10
```

### API usage

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

## 7️⃣ Voice and speech rate

Customize the voice and speech rate for a personalized narration experience.

### CLI usage

```bash
# Specify a voice
python fcgi-bin/cli.py -i input.txt --voice zh-CN-YunxiNeural

# Specify speech rate (0.5-2.0, 1.0 is normal)
python fcgi-bin/cli.py -i input.txt --rate 1.2

# Specify both voice and speech rate
python fcgi-bin/cli.py -i input.txt \
  --voice zh-CN-XiaoxiaoNeural \
  --rate 1.1
```

### API usage

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "abc123",
    "voice": "zh-CN-YunxiNeural",
    "rate": 1.2
  }'
```

### Configuration file (global default)

```env
# .env file
TTS_VOICE=zh-CN-XiaoxiaoNeural
TTS_RATE=1.0
```

---

## 8️⃣ Output path

Customize the output directory and file format.

### CLI usage

```bash
# Specify the output directory
python fcgi-bin/cli.py -i input.txt -o ./my_output

# Output to an absolute path
python fcgi-bin/cli.py -i input.txt -o /path/to/output
```

### API usage

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input.txt" \
  -F "output_path=./my_output"
```

### Configuration file (global default)

```env
# .env file
OUTPUT_BASE_PATH=./output
OUTPUT_FORMAT=mp3
OUTPUT_BITRATE=192
```

---

## 📚 Reference documentation

- [Development guide](./help/development-guide.md) - Required reading for developers
- [Installation guide](./help/INSTALL.md) - Environment setup instructions

---

**Last updated**: 2025-12-01
**Maintainer**: GA Sprite Birds Development Team

---

**Author:** adam
**Email:** dev@ebf.hk
**Website:** http://ebf.cc
**Source:** https://github.com/tiger-sprite/ga-sprite-birds
