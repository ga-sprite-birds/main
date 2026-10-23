# GA Sprite Birds

> Convert books and long text into chapter-based audio with Edge TTS, optional LLM colloquialization, and a local web GUI.

GA Sprite Birds splits a text file into chapters, optionally rewrites each chapter into natural spoken language, and generates one MP3 per chapter. It ships with a web GUI, a CLI, and a local FastAPI service. Single-voice generation works in the GUI, CLI, and API; multi-character voice generation is CLI-only.

---

## Features

| Feature | Description | GUI | CLI | API |
|---------|-------------|:---:|:---:|:---:|
| **Single-voice narration** | One voice for the whole book | ✅ | ✅ | ✅ |
| **Multi-character voice** | Detect dialogue and assign voices per character | ❌ | ✅ | ❌ |
| **Character analysis** | Extract characters and build a voice template | ❌ | ✅ | ❌ |
| **LLM colloquialization** | Rewrite written text into natural speech | ✅ | ✅ | ✅ |
| **Chapter splitting** | Detect chapter headings and generate separately | ✅ | ✅ | ✅ |
| **Chapter selection** | Generate only checked chapters | ✅ | ✅ | ✅ |
| **Punctuation pauses** | Sentence-level pauses and optional light tone | ✅ | ✅ | ✅ |
| **Pause / resume** | Stop after the current chapter and continue later | ✅ | ❌ | ✅ |
| **Task persistence** | Restore interrupted or paused tasks after a restart | ✅ | — | ✅ |
| **Multilingual UI** | Chinese and English | ✅ | ✅ | ✅ |
| **TTS preview tool** | Browse and preview Edge TTS voices | ❌ | ✅ | ❌ |

**Input formats:** `.txt`, `.md`, `.pdf`  
**Output format:** `.mp3`  
**TTS engine:** Edge TTS (free, no API key; requires network access)  
**LLM backends:** Ollama (local) or any OpenAI-compatible API

---

## Quick start

### 1. Install

Requires Python 3.10+ and FFmpeg.

```bash
git clone https://github.com/ga-sprite-birds/main.git
cd main

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Debian/Ubuntu example
sudo apt install ffmpeg
```

Or create a Conda environment:

```bash
conda env create -f environment.yml
conda activate ga-sprite-birds
```

### 2. Configure

```bash
cp .env.example .env
```

The defaults use Edge TTS and enable the LLM. To use a local LLM:

```env
LLM_MODE=local
LLM_LOCAL_HOST=http://localhost:11434
LLM_LOCAL_MODEL=deepseek-r1:7b
```

To use an OpenAI-compatible API:

```env
LLM_MODE=api
LLM_API_TYPE=openai
LLM_API_ENDPOINT=https://api.deepseek.com/v1
LLM_API_KEY=your_api_key_here
LLM_API_MODEL=deepseek-chat
```

See [Configuration](#configuration) for the options that matter most.

### 3. Run

**Web GUI + local API**

```bash
bash api.sh
```

The script starts FastAPI, chooses a free port starting at `API_PORT` (default `8000`), and opens `http://127.0.0.1:<port>/` in the browser. Interactive API docs are at `/docs`.

**CLI**

```bash
bash cli.sh -i input.txt
```

**GUI source development**

The built GUI is served from the repository root. To edit it:

```bash
cd gui
npm install
npm run dev      # Vite dev server on :5173
npm run build    # writes ../index.html
```

---

## GUI workflow

1. Drop one or more `.txt`, `.md`, or `.pdf` files into the upload area.
2. Set the output root, voice, and pause/tone mode, then click **Parse**.
3. Select the chapters to generate (all chapters are checked by default) and click **Start**.
4. Use **Pause** to stop after the current chapter; use **Resume** to continue the remaining selected chapters.
5. Completed chapters can be played or downloaded. **Clear task** removes all chapter audio, companion text files, the parsed chapter list, and the task record after confirmation. Uploaded source files are kept; upload again to start over.

Only the latest task is kept in the browser. Task records live in `cache/tasks/` and are deleted automatically when a task completes.

---

## CLI usage

### Single voice

```bash
# Basic
bash cli.sh -i input.txt

# Choose a voice and speech rate (0.5-2.0)
bash cli.sh -i input.txt --voice zh-CN-YunxiNeural --rate 1.2

# Add punctuation pauses (pause) or pauses plus light tone (prosody)
bash cli.sh -i input.txt --prosody pause

# Skip LLM colloquialization (faster)
bash cli.sh -i input.txt --no-llm

# Generate only chapters 1-5
bash cli.sh -i input.txt --start 1 --end 5

# Custom output directory
bash cli.sh -i input.txt -o ./my_output

# English interface
bash cli.sh -i input.txt --language en_US
```

The CLI uses `ENABLE_MULTI_VOICE` from `.env`. If it is `true`, pass `--multi-voice false` for single-voice generation. `--prosody` also applies to multi-character output.

### Multi-character voice

This is a two-step CLI-only workflow.

**Step 1: analyze characters**

```bash
bash cli.sh -i novel.txt --analyze-characters

# Hybrid mode with a user-provided character list
bash cli.sh -i novel.txt --analyze-characters \
  --analysis-mode hybrid \
  --character-list characters.txt
```

Example `characters.txt`:

```text
张三 male
李四 female
王五
```

The analysis writes a template such as `cache/role/novel_characters.json`.

**Step 2: generate**

```bash
# Use the auto-generated template
bash cli.sh -i novel.txt --multi-voice true

# Use a specific template and generate chapters 1-3
bash cli.sh -i novel.txt --multi-voice true \
  --character-template cache/role/custom_characters.json \
  --start 1 --end 3
```

Multi-character output includes a `.txt` file next to each MP3 with the dialogue and voice annotations.

### TTS preview

```bash
# List Chinese voices
python utils/try_tts/cli.py list --lang zh-CN

# Generate previews for all Chinese voices
python utils/try_tts/cli.py generate --lang zh-CN

# Preview one voice with custom text
python utils/try_tts/cli.py generate \
  --voice zh-CN-XiaoxiaoNeural \
  --text "这是我的试听文本"
```

Previews are written to `output/tts_samples/`.

---

## API usage

Start the service with `bash api.sh`, or directly:

```bash
PYTHONPATH=. python fcgi-bin/api.py
```

The API is intended for local use and has no authentication. Do not expose it directly to the public internet. The examples below use port `8000`; replace it with the port printed by `api.sh` if different.

### 1. Upload

`file`, `path`, `output_path`, and `language` are query parameters; the file itself is multipart form data. `output_path` is the output root; the source filename is appended as a subdirectory.

```bash
# Upload a file
curl -X POST "http://localhost:8000/upload?output_path=./my_output" \
  -F "file=@input.txt"

# Or point at a file already on the server
curl -X POST "http://localhost:8000/upload?path=/absolute/path/input.txt"
```

Response:

```json
{"task_id":"<id>","status":"pending","message":"File uploaded, task ID: <id>"}
```

Uploads are limited by `API_MAX_UPLOAD_SIZE` (MB, default `100`). Files are stored under `API_UPLOAD_DIR` with a unique prefix.

### 2. Parse

```bash
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<id>","language":"en_US"}'
```

### 3. Generate

```bash
# All chapters
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<id>","voice":"zh-CN-YunxiNeural","enable_llm":true}'

# Selected chapters, with a speech rate
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<id>",
    "chapter_indexes": [1, 2, 5],
    "rate": 1.2,
    "prosody_mode": "prosody",
    "enable_llm": false
  }'
```

`chapter_indexes` must be a non-empty list of existing chapter numbers when supplied. Omit it to generate all chapters. `enable_llm` defaults to `ENABLE_LLM` from `.env`; `rate` must be between `0.5` and `2.0`. `prosody_mode` is `off` (default), `pause`, or `prosody`; omit it to use `TTS_PROSODY_MODE` from `.env`.

The API supports single-voice generation only. Use the CLI for multi-character voice generation.

### 4. Status, pause, resume, clear

```bash
# Task progress and per-chapter status
curl "http://localhost:8000/task/<id>/status"

# Stop after the current chapter
curl -X POST "http://localhost:8000/task/<id>/pause"

# Continue the remaining chapters from the saved selection
curl -X POST "http://localhost:8000/task/<id>/resume"

# Download a chapter
curl "http://localhost:8000/task/<id>/chapter/1" --output chapter_1.mp3

# Clear the whole task: parsed chapters, all audio, and the task record
curl -X DELETE "http://localhost:8000/task/<id>"

# Optional: delete only one chapter's audio and companion text files
curl -X DELETE "http://localhost:8000/task/<id>/chapter/1"

# API defaults and health
curl "http://localhost:8000/api/status"
```

Pausing finishes the current chapter first. Remaining chapters in the selected scope are marked `paused`; resuming treats them as pending. Task options and the selected chapter scope are persisted, so a paused task can be resumed after a service restart. Clearing a task removes its parsed chapter list, all generated audio, and the task record; the uploaded source file is kept.

### Output layout

Each source file gets its own directory under the output root, using the source filename without its extension. With the default `OUTPUT_STRATEGY=by_role`:

```text
output/
└── 示例书名/
    ├── 001-第一章.mp3
    ├── 001-第一章.txt
    ├── 002-第二章.mp3
    └── ...
```

A custom output root still gets the source directory appended: `abc` becomes `abc/示例书名/`. Multi-character output uses `abc/示例书名/multi/`.

Front-matter titles matching `OUTPUT_FRONT_MATTER_MARKERS` (default `导读,前言`) are written with a `000` prefix and a `<marker>篇` label. Later chapter numbers are not renumbered.

---

## Configuration

Copy `.env.example` to `.env`. The most useful settings:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LANGUAGE` | `en_US` | Default UI/API language (`en_US` or `zh_CN`) |
| `ENABLE_LLM` | `true` | Default for LLM colloquialization |
| `LLM_MODE` | `local` | `local` (Ollama) or `api` (OpenAI-compatible) |
| `TTS_VOICE` | `zh-CN-YunxiNeural` | Default Edge TTS voice |
| `TTS_RATE` | `1.0` | Default speech rate |
| `TTS_CHUNK_MAX_CHARS` | `2000` | Split long chapters into chunks at sentence boundaries |
| `TTS_CHUNK_TIMEOUT` | `180` | Timeout per TTS chunk in seconds |
| `TTS_PROSODY_MODE` | `off` | `off`, `pause`, or `prosody` |
| `TTS_PROSODY_MAX_UNIT_CHARS` | `120` | Maximum characters per pause unit; smaller means more requests |
| `OUTPUT_BASE_PATH` | `./output` | Output root; source filename is appended as a subdirectory |
| `OUTPUT_FRONT_MATTER_MARKERS` | `导读,前言` | Comma-separated front-matter title prefixes; empty disables 000 handling |
| `OUTPUT_DUPLICATE_HANDLING` | `rename` | `skip`, `rename`, or `overwrite` |
| `OUTPUT_STRATEGY` | `by_role` | `by_role`, `by_model`, `by_date`, or flat |
| `CHAPTER_NORMALIZE_ENABLED` | `true` | Normalize Markdown/bold chapter headings |
| `API_MAX_UPLOAD_SIZE` | `100` | Upload limit in MB (`0` disables) |
| `API_UPLOAD_DIR` | `./uploads` | Upload storage directory |
| `TASK_CACHE_DIR` | `./cache/tasks` | Persisted task records |
| `TASK_RESULT_TTL` | `86400` | Stale record retention in seconds (`0` = never expire) |

`TTS_PROSODY_MAX_UNIT_CHARS=120` matches the preview samples. For long books, raise it to `200`-`300` to reduce the number of TTS requests, at the cost of fewer internal pauses.

`OUTPUT_FORMAT` and `OUTPUT_BITRATE` currently control the MP3 export settings; see `config/__init__.py` for the full list.

---

## Project layout

```text
fcgi-bin/            CLI and FastAPI entry points
ga_birds/
  Audio/             TTS engines, chapter generator, exporter, merger
  Common/            Shared config, i18n, chapter loader, text saver
  LLM/               Ollama/OpenAI clients
  Parser/            Chapter parser
  character_analyzer/ Multi-voice character and dialogue analysis
  Task/              In-memory task manager and JSON persistence
  Utils/             File, text, retry, and token helpers
gui/                 Vue 3 + Element Plus frontend
help/                Installation and development guides
output/              Generated audio (ignored by git)
uploads/             Uploaded source files (ignored by git)
cache/tasks/         Persisted task records (ignored by git)
```

---

## Reference documentation

- [Development guide](./help/development-guide.md)
- [Installation guide](./help/INSTALL.md)
- [中文说明](./help/README.zh.md)

---

**Last updated:** 2026-10-23  
**Maintainer:** GA Sprite Birds Development Team

**Author:** adam  
**Email:** dev@ebf.hk  
**Website:** http://ebf.cc  
**Source:** https://github.com/ga-sprite-birds/main
