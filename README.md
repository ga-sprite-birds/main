# GA Sprite Birds

> Turn books and long text into audiobooks: split the text into chapters, optionally
> rewrite written language into natural speech with an LLM, and synthesize one MP3 per
> chapter — with optional per-character voices.

GA Sprite Birds is a self-hosted text-to-audiobook engine. It detects chapter boundaries,
can rewrite the text into spoken language, and renders each chapter to audio. You can drive
it from a **web GUI**, a **CLI**, or an **HTTP API** — all three share one engine and one task
state, so a job queued from the CLI is visible in the GUI and controllable from the API.

- **Input:** `.txt` / `.md` / `.pdf` · **Output:** one `.mp3` per chapter (chapter text optional)
- **TTS:** Edge TTS (free, needs network) · **LLM:** local Ollama or any OpenAI-compatible API

---

## 1. Features

| Feature | What it does |
|---|---|
| Chapter splitting | Detects chapter headings (plain text / Markdown / PDF) and renders per chapter; generate all or only selected chapters |
| Single & multi-character voices | One voice for the whole book, or detect characters and assign a voice per role |
| LLM colloquialization | Optional rewrite of written text into natural spoken language (Ollama or OpenAI-compatible) |
| Pauses & light prosody | `off` / `pause` / `prosody` — punctuation-driven pauses and optional tone shifts |
| Voice preview | Listen to a cached sample before choosing a voice |
| Pause / resume / cancel / retry | Cooperative control at chapter boundaries; failed tasks can be requeued |
| Crash recovery | Per-chapter checkpoints — a restart never redoes finished chapters |
| Durable tasks | Task state and events live in SQLite; closing the GUI or restarting a process loses nothing |
| System config | Three-layer config (defaults → user overrides → per-task snapshot); edits apply to new tasks only |
| i18n | Chinese and English UI, CLI and API messages |

> The GUI currently covers single-voice generation and system config. Multi-character
> generation, character analysis and TTL cleanup are available through the CLI/API.

---

## 2. Install & documentation

**Requirements:** Python 3.10+ and FFmpeg. Node.js is only needed to build the GUI yourself.

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start the engine and the API, then open <http://127.0.0.1:8000/>:

```bash
python -m engine run        # terminal 1 — Core engine
python fcgi-bin/api.py      # terminal 2 — Control API + GUI
```

**Documentation navigation**

| Document | Contents |
|---|---|
| [Install guide](./help/INSTALL.md) · [安装指南](./help/INSTALL.zh.md) | Runtime requirements, first-time setup, local & API deployment, troubleshooting |
| [API reference](./docs/api.md) | Every endpoint and the CLI/API parity matrix |
| [Deployment & operations](./docs/deploy/README.md) | systemd, permissions, reverse proxy, upgrade & rollback |
| [Development guide](./help/development-guide.md) · [开发规范](./help/development-guide.zh.md) | Architecture boundaries, adding config items, i18n sync, tests |
| Design specs | [System config](./docs/design/v2-system-config.md) · [Headless core](./docs/design/v2-headless-core.md) |
| systemd unit templates | [`scripts/systemd/`](./scripts/systemd/) (core/api × user/system) |

---

## 3. Design: one engine, two access modes

### 3.1 Two processes, one engine

```text
GUI / CLI / HTTP clients
        │
        ▼
Control API (fcgi-bin/api.py)          Core engine (python -m engine run)
· accepts uploads, serves the GUI      · the only executor
· forwards commands (idempotent)  ───▶ · the only writer of task state
· read-only task queries          ◀─── · per-chapter checkpoints, recovery
        │                                   │
        └────── read-only ────▶ data/tasks.db ◀──── writes ─────┘
```

- **The engine is the single writer.** Task state, chapters and events are written by the
  engine only; the API and CLI never write `tasks.db`. Stopping the API does not stop running
  tasks.
- **Recovery is built in.** On engine restart, `running` tasks resume from the last succeeded
  chapter; `paused` tasks stay paused.
- **Config is snapshotted per task.** Editing config never disturbs a running task; changes
  apply to the next task started.

### 3.2 CLI mode — for local batch & scripting

`fcgi-bin/cli.py` is a thin client of the engine, ideal for your own machine and automation:

- One command can chain **upload + parse + generate** (`cli.py add -i book.txt`).
- Human-readable output or machine-readable `--json`; `--follow` streams progress.
- Full control surface: `add / list / get / status / pause / resume / cancel / retry /
  remove / events / clean / config / system`.
- No open port needed: the CLI talks to the engine over the local command channel.
- Good for cron jobs, batch conversion and operations.

### 3.3 API mode — for services & integrations

`fcgi-bin/api.py` exposes the same capabilities as `/fcgi-bin/api/*` for remote clients and
the web GUI:

- Step-by-step endpoints with JSON bodies: `upload → parse → generate → status/download`.
- Uniform response envelope `{"code", "msg", "data"}`; event stream pulled incrementally by
  `event_id` cursor.
- Uploads, batch jobs and integrations from other systems.
- Serves the packaged GUI; every click maps to the same endpoints.
- Bind to loopback/private addresses (there is no built-in auth) and put a reverse proxy in
  front when exposing it.

### 3.4 CLI vs API at a glance

| | CLI (`fcgi-bin/cli.py`) | HTTP API (`/fcgi-bin/api/*`) |
|---|---|---|
| Best for | Scripting, cron, batch, ops | Integrations, remote clients, GUI |
| Invocation | One command does upload + parse + generate | Step-by-step endpoints with JSON |
| Transport | Local command channel only | HTTP over a bound address |
| Output | Human-readable or `--json` | Uniform `{code, msg, data}` envelope |
| Needs a running API server | No | Yes |

Both submit the **same idempotent commands** to the same engine, so anything one can do, the
other can do.

---

## 4. How to use

### 4.1 Start

```bash
python -m engine run        # terminal 1 — Core engine (Ctrl+C = graceful stop)
python fcgi-bin/api.py      # terminal 2 — Control API + GUI
```

Engine status / discovery: `python -m engine status` (PID, port, task counters). The engine
listens on `127.0.0.1:39300` by default and writes its port and token to `run/engine.json`.

### 4.2 GUI

Open <http://127.0.0.1:8000/>:

1. Drop one or more `.txt` / `.md` / `.pdf` files; each upload creates a task.
2. Set the output root, voice (with preview) and pause mode, then click **Parse**.
3. Check the chapters to generate and click **Start**.
4. **Pause** stops after the current chapter; **Resume** continues the rest. Finished
   chapters can be played or downloaded.
5. **System config** in the sidebar edits business settings in grouped sections, with
   option explanations, override badges and per-section reset.

### 4.3 CLI

```bash
# Upload + parse + queue generation in one call
python fcgi-bin/cli.py add -i book.txt --voice zh-CN-YunxiNeural --rate 1.2 --no-llm --start 1 --end 5

# Multi-character: analyze characters, then generate with the template
python fcgi-bin/cli.py add -i novel.txt --analyze-characters --analysis-mode hybrid --character-list characters.txt
python fcgi-bin/cli.py add -i novel.txt --multi-voice --character-template cache/role/novel_characters.json

# Control and follow
python fcgi-bin/cli.py list --status running
python fcgi-bin/cli.py pause <task_id> && python fcgi-bin/cli.py resume <task_id>
python fcgi-bin/cli.py events <task_id> --follow

# Business config (same store as the GUI)
python fcgi-bin/cli.py config set TTS_RATE 1.15
```

`characters.txt` lists one `name [gender]` per line (`张三 male`, `李四 female`).
Run `python fcgi-bin/cli.py --help` for all subcommands.

### 4.4 API

```bash
# Upload (idempotent)
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/upload" \
  -F "file=@book.txt" -H "Idempotency-Key: book-v1"

# Parse (runs in the background), then generate selected chapters
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/parse" \
  -H "Content-Type: application/json" -d '{"task_id":"<id>","command_id":"parse-1"}'
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<id>","chapter_indexes":[1,2],"rate":1.2,"prosody_mode":"prosody"}'

# Progress, and a voice preview (audio/mpeg)
curl "http://127.0.0.1:8000/fcgi-bin/api/task/<id>/status"
curl -o preview.mp3 "http://127.0.0.1:8000/fcgi-bin/api/tts/preview?voice=zh-CN-YunxiNeural"
```

Error-code ranges: `1000` arguments, `2000` auth, `3000` business, `4000` system; engine
down → HTTP `503` + `code 3004`. Full details: [docs/api.md](./docs/api.md).

### 4.5 Task lifecycle

```text
pending ──▶ queued ──▶ running ──▶ succeeded / failed / canceled
                ▲          │
                │          ├──▶ paused ──▶ queued (resume)
                └──────────┘         failed ──▶ queued (retry)
any state ──▶ removed
```

Pause/cancel take effect at a chapter boundary; running tasks refresh a heartbeat every 10s.

### 4.6 Output layout

Each source file gets a directory named after it under the output root:

```text
output/sample-book/
    ├── 001-chapter-one.mp3
    ├── 001-chapter-one.txt
    └── 002-chapter-two.mp3
```

Front matter (`导读,前言` by default) uses a `000` prefix; multi-character output goes under
`sample-book/multi/`.

---

**Author:** adam · dev@ebf.hk · <http://ebf.cc>
**Source:** <https://github.com/tiger-sprite/ga-sprite-birds>
