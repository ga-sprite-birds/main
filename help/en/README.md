# GA Sprite Birds — Usage Guide

> 中文版：[../zh/README.md](../zh/README.md) · Project landing page: [../../README.md](../../README.md)

GA Sprite Birds turns books and long text into audiobooks: it splits the text into chapters,
optionally rewrites written language into natural speech with an LLM, and synthesizes one MP3
per chapter — with optional per-character voices.

You can drive it from a **web GUI**, a **CLI**, or an **HTTP API**; all three share one engine
and one task state.

- **Input:** `.txt` / `.md` / `.pdf` · **Output:** one `.mp3` per chapter (chapter text optional)
- **TTS:** Edge TTS (free, needs network) · **LLM:** local Ollama or any OpenAI-compatible API

---

## 1. Features

| Feature | What it does |
|---|---|
| Chapter splitting | Detects chapter headings (plain text / Markdown / PDF) and renders per chapter; generate all or only selected chapters |
| Single & multi-character voices | One voice for the whole book, or generate with a per-role voice template |
| LLM colloquialization | Optional rewrite of written text into natural spoken language (Ollama or OpenAI-compatible) |
| Pauses & light prosody | `off` / `pause` / `prosody` — punctuation-driven pauses and optional tone shifts |
| Voice preview | Listen to a cached sample before choosing a voice |
| Pause / resume / cancel / retry | Cooperative control at chapter boundaries; failed tasks can be requeued |
| Crash recovery | Per-chapter checkpoints — a restart never redoes finished chapters |
| Durable tasks | Task state and events live in SQLite; closing the GUI or restarting a process loses nothing |
| System config | Three-layer config (defaults → user overrides → per-task snapshot); edits apply to new tasks only |
| i18n | Chinese and English UI, CLI and API messages |

> The GUI covers single-voice generation and system config. Multi-character generation and
> TTL cleanup are available through the CLI/API. Character analysis is **not** exposed by the
> v2 add flow; provide a character template yourself for multi-voice generation.

---

## 2. Quick start

### 2.1 Docker (recommended)

No Python or FFmpeg is needed on the host; both are inside the image.

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
cp .env.example .env                  # set LLM credentials / deployment settings
mkdir -p data run cache output logs uploads
sudo chown -R 1000:1000 data run cache output logs uploads
docker compose up -d --build
# open http://127.0.0.1:8000/
# if port 8000 is taken: API_HOST_PORT=18080 docker compose up -d --build
```

- Persistent data: `./data`, `./run`, `./cache`, `./output`, `./logs`, `./uploads`.
- The image runs as unprivileged `app` (default `1000:1000`); chown the bind mounts first, or set
  `APP_UID`/`APP_GID` and rebuild for a different host user.
- Published on `127.0.0.1` by default. For LAN access set `API_BIND_HOST=0.0.0.0` and enable
  `API_AUTH_ENABLED=true` + `API_AUTH_TOKEN`; the GUI key button stores the token.
- CORS is off by default; use an explicit origin list if needed.
- `models/` is Python code in the image; model caches go to `./cache/models`.
- Docker and a host engine must not share `data/` or `run/` at the same time (single-instance lock).
- The engine command channel (`127.0.0.1:39300`) is never exposed.

See [Deployment & operations](deployment.md) for systemd, permissions, reverse proxy and upgrades.

### 2.2 venv (native)

Requires Python 3.10+ and FFmpeg.

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
```

Install FFmpeg first (`apt install ffmpeg`, `brew install ffmpeg`, or the Windows build) and verify
with `ffmpeg -version`.

Start the two processes in one of two ways:

**Option A — local GUI quick start (Linux/macOS).** `utils/quick/` starts the engine and API,
picks a free API port, and opens the GUI:

```bash
bash utils/quick/linux-run.sh
./utils/quick/mac-run.command
```

**Option B — start separately (headless / no GUI).** Useful for servers, automation, or when you
only need the CLI/API:

```bash
# Terminal 1 — Core engine (required)
python -m engine run
# Terminal 2 — Control API + GUI (optional)
python -m server run
```

- **CLI only:** start just the engine; the CLI talks to it over the local command channel.
- **GUI / HTTP API:** start both processes.

The API auto-shifts to a free port when `8000` is taken; `--strict-port` fixes it. The engine
listens on `127.0.0.1:39300` by default and writes its port/token to `run/engine.json`.

### 2.3 Development (conda)

Developers can use conda for a reproducible local setup. See
[Development setup](development.md). Production deployments should use Docker or venv, not conda.

---

## 3. Documentation map

| Document | Contents |
|---|---|
| [Development setup](development.md) | conda environment, FFmpeg, `.env`, GUI build, tests, troubleshooting |
| [Developer guide](developer-guide.md) | Contract, module boundaries, config items, i18n sync, command channel, testing |
| [Utils development](utils.md) | Standalone tools under `utils/`: structure, config access, conventions |
| [API reference](api.md) | Every endpoint and the CLI/API parity matrix |
| [Deployment & operations](deployment.md) | venv/Docker, systemd, permissions, reverse proxy, upgrade & rollback |
| [Design specs](design/README.md) | [System config](design/v2-system-config.md) · [Headless core](design/v2-headless-core.md) |
| systemd templates | [`scripts/systemd/`](../../scripts/systemd/) (core/api × user/system) |
| 中文文档 | [../zh/README.md](../zh/README.md) |

---

## 4. Design: one engine, two access modes

### 4.1 Two processes, one engine

```text
GUI / CLI / HTTP clients
        │
        ▼
Control API (python -m server run)            Core engine (python -m engine run)
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

### 4.2 CLI mode — for local batch & scripting

`fcgi-bin/cli.py` is a thin client of the engine, ideal for your own machine and automation:

- One command can chain **upload + parse + generate** (`cli.py add -i book.txt`).
- Human-readable output or machine-readable `--json`; `--follow` streams progress.
- Full control surface: `add / list / get / status / pause / resume / cancel / retry /
  remove / cancel-chapter / events / logs / clean / config / system`.
- No open port needed: the CLI talks to the engine over the local command channel.
- Good for cron jobs, batch conversion and operations.

### 4.3 API mode — for services & integrations

The Control API (`python -m server run`) exposes the same capabilities as `/fcgi-bin/api/*` for
remote clients and the web GUI:

- Step-by-step endpoints with JSON bodies: `upload → parse → generate → status/download`.
- Uniform response envelope `{"code", "msg", "data"}`; event stream pulled incrementally by
  `event_id` cursor.
- Uploads, batch jobs and integrations from other systems.
- Serves the packaged GUI; every click maps to the same endpoints.
- Bind to loopback/private addresses (there is no built-in auth) and put a reverse proxy in
  front when exposing it.

### 4.4 CLI vs API at a glance

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

## 5. How to use

### 5.1 GUI

Open <http://127.0.0.1:8000/>:

1. Drop one or more `.txt` / `.md` / `.pdf` files; each upload creates a task.
2. Set the output root, voice (with preview) and pause mode, then click **Parse**.
3. Check the chapters to generate and click **Start**.
4. **Pause** stops after the current chapter; **Resume** continues the rest. Finished
   chapters can be played or downloaded.
5. **System config** in the sidebar edits business settings in grouped sections, with
   option explanations, override badges and per-section reset.

### 5.2 CLI

```bash
# Upload + parse + queue generation in one call
python fcgi-bin/cli.py add -i book.txt --voice zh-CN-YunxiNeural --rate 1.2 --no-llm --start 1 --end 5

# Multi-character generation with an existing voice template
python fcgi-bin/cli.py add -i novel.txt --multi-voice --character-template cache/role/novel_characters.json

# Control and follow
python fcgi-bin/cli.py list --status running
python fcgi-bin/cli.py pause <task_id> && python fcgi-bin/cli.py resume <task_id>
python fcgi-bin/cli.py events <task_id> --follow

# Business config (same store as the GUI)
python fcgi-bin/cli.py config set TTS_RATE 1.15
```

Run `python fcgi-bin/cli.py --help` for all subcommands. Character analysis is not part of the
v2 `add` flow; prepare the multi-voice template yourself (see the developer guide).

### 5.3 API

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
down → HTTP `503` + `code 3004`. Full details: [API reference](api.md).

### 5.4 Task lifecycle

```text
pending ──▶ queued ──▶ running ──▶ succeeded / failed / canceled
                ▲          │
                │          ├──▶ paused ──▶ queued (resume)
                └──────────┘         failed ──▶ queued (retry)
any state ──▶ removed
```

Pause/cancel take effect at a chapter boundary; running tasks refresh a heartbeat every 10s.

### 5.5 Output layout

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
