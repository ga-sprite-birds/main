# GA Sprite Birds — Development Setup

> 中文版：[../zh/development.md](../zh/development.md) · Usage guide: [README.md](README.md) · Deployment: [deployment.md](deployment.md)

This document is for **developers**: it covers a conda-based local setup, running from source,
building the GUI, tests and troubleshooting.

> Production deployment should use **Docker (recommended)** or a native **venv** install. conda is
> a development convenience and is not used for production. See the root
> [README](../../README.md) and [Deployment & operations](deployment.md).

---

## 1. Requirements

| Item | Requirement | Notes |
|---|---|---|
| OS | Windows 10+ / macOS 10.15+ / Linux | |
| Python | 3.10+ | The conda environment pins 3.10 |
| FFmpeg | **Required** | Included in the conda environment; MP3 export / audio merge |
| Node.js | Optional | Only to build the GUI yourself |
| Memory | 4 GB minimum; 16 GB+ with a local LLM | API-only setups use very little |
| Disk | ~1 GB plus generated audio | Dependencies and caches included |
| Network | Required for Edge TTS / online LLMs | Local Ollama can work offline |

---

## 2. Get the code

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
```

## 3. Create the conda environment

`environment.yml` already includes Python 3.10, FFmpeg and `pip install -r requirements.txt`:

```bash
conda env create -f environment.yml
conda activate ga-sprite-birds
```

If you update `requirements.txt` later:

```bash
pip install -r requirements.txt
```

## 4. Verify FFmpeg

```bash
ffmpeg -version
```

The conda environment ships FFmpeg. If you prefer a system build, install it with your package
manager and leave `FFMPEG_PATH` empty (the app uses `PATH`), or point `FFMPEG_PATH` at the
directory containing the binary.

## 5. (Optional) Local LLM

Only needed for LLM colloquialization without an online API:

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:7b      # default local model; change in .env
```

Windows / macOS installers: <https://ollama.com/download>. You can skip local models and use any
OpenAI-compatible endpoint (`LLM_MODE=api`).

## 6. Configure `.env`

```bash
cp .env.example .env
```

`.env` holds **deployment settings and credentials only**:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_MODE` | `local` | `local` (Ollama) or `api` (OpenAI-compatible) |
| `LLM_API_ENDPOINT` / `LLM_API_KEY` / `LLM_API_MODEL` | — | Endpoint, key, model for `api` mode |
| `LLM_LOCAL_HOST` / `LLM_LOCAL_MODEL` | `http://localhost:11434` / `deepseek-r1:7b` | Local Ollama |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Control API bind address |
| `API_AUTH_ENABLED` / `API_AUTH_TOKEN` | `false` / empty | Optional token auth; enable when the API leaves loopback |
| `API_CORS_ENABLED` / `API_CORS_ORIGINS` | `false` / empty | CORS is off by default; use an explicit origin list if needed |
| `API_MAX_UPLOAD_SIZE` | `100` | Upload cap (MB); `0` unlimited |
| `API_MAX_JSON_BODY_SIZE` | `1` | JSON body cap (MB); `0` unlimited |
| `API_LOCAL_READ_ROOTS` | empty | Extra allowed roots for `/upload?path=`; uploads/ is always allowed |
| `TASK_MAX_CONCURRENT` | `2` | Concurrent tasks in the engine |
| `TASK_RESULT_TTL` | `86400` | Seconds to keep terminal task records; `0` keeps forever |
| `FFMPEG_PATH` | empty | FFmpeg directory; empty uses system `PATH` |
| `MODEL_CACHE_DIR` | `./cache/models` | Downloaded model cache (kept out of the `models/` code package) |
| `LOG_LEVEL` / `LOG_FILE` | `INFO` / `./logs/app.log` | Logging |

> Path safety: `/upload?path=` is restricted to `API_UPLOAD_DIR` plus
> `API_LOCAL_READ_ROOTS`; `output_path` must stay under `OUTPUT_BASE_PATH`; the
> output filename template cannot contain `/`, `\` or `..`; and
> `character_template` must stay under `CHARACTER_CACHE_DIR`. Symlink escapes and
> `..` traversal are rejected.

> **Business settings are not in `.env`.** Language, voice, rate, chapter rules, output strategy
> and the new per-task toggles come from `data/system.db` (defaults) + `cache/config/system.json`
> (overrides). Edit them in the GUI **System config** page or with
> `python fcgi-bin/cli.py config set …`; changes apply to new tasks without a restart.

## 7. Verify the environment

```bash
python -m engine doctor --json   # directories, permissions, DBs, ffmpeg, discovery, config
python -m pytest tests/unit -q   # unit tests need no running services
```

`doctor` checks that the data/run directories are writable, `tasks.db` integrity, FFmpeg, the
configuration service and the runtime discovery file. It is read-only and never migrates the DB.

---

## 8. Run from source

```bash
# Terminal 1: Core engine (foreground; Ctrl+C = graceful stop)
python -m engine run

# Terminal 2: Control API + GUI
python -m server run
```

Open <http://127.0.0.1:8000/>. On Linux/macOS, `utils/quick/` can start both processes and open
the GUI:

```bash
bash utils/quick/linux-run.sh
./utils/quick/mac-run.command
```

`utils/quick/` is a local GUI convenience. For headless operation, start the processes yourself:

- **CLI only:** start just the engine (`python -m engine run`); the CLI uses the local command
  channel and does not need the API process.
- **GUI / HTTP API:** start both `python -m engine run` and `python -m server run`.

- The engine listens on `127.0.0.1:39300` by default and shifts to a free port when occupied;
  the actual port and token are written to `run/engine.json`.
- The API auto-shifts to a free port and prints a warning; `--strict-port` fixes the port.
- The engine is **single-instance**: a second `python -m engine run` exits immediately (code 2).
- Health checks: `python -m engine status`, `curl -s http://127.0.0.1:8000/fcgi-bin/api/status`.

The CLI is a Core client: `python fcgi-bin/cli.py add -i book.txt ...` uploads, parses and queues
generation in one call.

---

## 9. GUI build (development only)

Releases ship a prebuilt single-file `index.html` at the repository root. To work on the frontend:

```bash
cd gui
npm install
npm run dev      # Vite dev server, proxies /fcgi-bin to the API
npm run build    # writes the single-file ../index.html
```

> **Windows + network shares**: `vite build` loads a native rollup module that fails on SMB/UNC
> paths. Build on a local disk and copy the resulting `index.html` back.

If `npm run build` reports a missing Vite executable (e.g. after copying the tree without
permissions), use:

```bash
node ./node_modules/vite/bin/vite.js build
```

---

## 10. Tests

```bash
# Unit tests (no services required)
python -m pytest tests/unit -q

# All tests; integration tests auto-skip when the API/engine is unreachable
python -m pytest tests

# One file
python -m pytest tests/unit/test_api_v2.py -v
```

- Unit tests live in `tests/unit/`; integration tests live in `tests/integration/`.
- Markers: `unit`, `integration`, `slow`.
- API contract changes must update `tests/unit/test_api_v2.py` and [api.md](api.md) together.

---

## 11. Troubleshooting

**`python -m engine run` exits immediately with code 2?**
An instance is already running (single-instance lock). Check `python -m engine status`, or stop it.

**API answers 503 with code 3004?**
The engine is not running, or the port/token does not match. Start the engine first; the API reads
its address from `run/engine.json`.

**DB integrity / WAL warnings?**
Run `python -m engine doctor` to check `tasks.db` integrity. Keep `data/` on a local disk; SQLite
WAL is unreliable on SMB network drives.

**Voice preview plays nothing?**
Preview uses Edge TTS and needs internet; the first synthesis per voice takes a few seconds
(cached under `cache/tts/preview/`).

**GUI dev server cannot reach the API?**
Check `gui/vite.config.*` proxy settings and that `python -m server run` is listening on the
configured port.

---

## Next steps

- [Developer guide](developer-guide.md): contract, module boundaries, config items, i18n, tests
- [API reference](api.md)
- [Deployment & operations](deployment.md)
- [Design specs](design/README.md)
