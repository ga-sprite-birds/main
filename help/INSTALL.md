# GA Sprite Birds — Installation Guide

> For v2 (Core engine + thin Control API, two processes). 中文版本：[INSTALL.zh.md](INSTALL.zh.md)
> Daily usage: [README](../README.md).

This guide is ordered as: **1) runtime requirements → 2) first-time installation → 3) deployment (local / API)** → 4) GUI build → 5) troubleshooting.

---

## 1. Runtime requirements

| Item | Requirement | Notes |
|---|---|---|
| OS | Windows 10+ / macOS 10.15+ / Linux | |
| Python | 3.10+ | |
| FFmpeg | **Required** | MP3 export / audio merge |
| Node.js | Optional | Only to build the GUI yourself |
| Memory | 4 GB minimum; 16 GB+ with a local LLM | API-only setups use very little |
| Disk | ~1 GB plus generated audio | Dependencies and caches included |
| Network | Required for Edge TTS / online LLMs | Local Ollama can work offline |

---

## 2. Initial installation

### 2.1 Get the code

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
```

### 2.2 Create a Python environment

**venv (portable)**

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -U pip setuptools wheel
pip install -r requirements.txt
```

**Conda**

```bash
conda env create -f environment.yml
conda activate ga-sprite-birds
pip install -r requirements.txt
```

### 2.3 Install FFmpeg

- **Windows**: download from <https://ffmpeg.org/download.html> and add it to `PATH`, or set `FFMPEG_PATH` in `.env`
- **macOS**: `brew install ffmpeg`
- **Debian/Ubuntu**: `sudo apt install ffmpeg`

Verify with `ffmpeg -version`.

### 2.4 (Optional) Install Ollama for local LLM

Only needed for LLM colloquialization without an online API:

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:7b      # default local model; change in .env
```

Windows / macOS installers: <https://ollama.com/download>. You can skip local models entirely
and use any OpenAI-compatible endpoint (`LLM_MODE=api`, see below).

### 2.5 Configure `.env`

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
| `TASK_MAX_CONCURRENT` | `2` | Concurrent tasks in the engine |
| `TASK_RESULT_TTL` | `86400` | Seconds to keep terminal task records; `0` keeps forever |
| `FFMPEG_PATH` | empty | FFmpeg directory; empty uses system `PATH` |
| `LOG_LEVEL` / `LOG_FILE` | `INFO` / `./logs/app.log` | Logging |

> **Business settings are not in `.env`.** Language, voice, rate, chapter rules and output
> strategy come from `data/system.db` (defaults) + `cache/config/system.json` (overrides).
> Edit them in the GUI **System config** page or with `python fcgi-bin/cli.py config set …`;
> they apply to new tasks immediately, no restart needed.

### 2.6 Verify the installation

```bash
python -m engine doctor --json   # dirs, permissions, DBs, ffmpeg, ports
```

`doctor` checks that the data/run/cache directories are writable, SQLite works, FFmpeg is
executable and the default port is free.

---

## 3. Deployment

v2 always runs as **two processes**: the Core engine (sole executor, sole writer of task
state) and the Control API (serves the GUI and endpoints). Only how you supervise them
differs between the two deployment styles below; functionality is identical.

### 3.1 Local deployment (personal machine / development)

Run one process per terminal:

```bash
# Terminal 1: Core engine (foreground; Ctrl+C = graceful stop)
python -m engine run

# Terminal 2: Control API (also serves the GUI)
python fcgi-bin/api.py
```

Open <http://127.0.0.1:8000/>. Health checks:

```bash
python -m engine status                      # pid / port / task counters
curl -s http://127.0.0.1:8000/fcgi-bin/api/status
```

- The engine listens on `127.0.0.1:39300` by default and shifts to a free port when occupied;
  the actual port and token are written to `run/engine.json`.
- The engine is **single-instance**: a second `python -m engine run` exits immediately (code 2).
- Ad-hoc background run (debug only): `nohup python -m engine run > logs/engine.log 2>&1 &`.

### 3.2 API deployment (long-lived / serving the HTTP API)

The API has **no built-in authentication** — bind it to loopback or a private interface, and
put Nginx / an internal gateway in front when exposing it. **Never** expose the engine command
channel `127.0.0.1:39300`.

**Linux — systemd (recommended).** Unit templates ship in [`scripts/systemd/`](../scripts/systemd/):
`ga-sprite-birds-core.{user,system}.service` and `ga-sprite-birds-api.{user,system}.service`.

User-level (no root; starts with your login session):

```bash
mkdir -p ~/.config/systemd/user
cp scripts/systemd/ga-sprite-birds-core.user.service ~/.config/systemd/user/ga-sprite-birds-core.service
cp scripts/systemd/ga-sprite-birds-api.user.service  ~/.config/systemd/user/ga-sprite-birds-api.service
systemctl --user daemon-reload
systemctl --user enable --now ga-sprite-birds-core ga-sprite-birds-api

systemctl --user status ga-sprite-birds-core
journalctl --user -u ga-sprite-birds-core -f
```

To keep user services running after logout: `sudo loginctl enable-linger "$USER"`.

System-level (starts at boot, independent of login):

```bash
sudo cp scripts/systemd/ga-sprite-birds-core.system.service /etc/systemd/system/ga-sprite-birds-core.service
sudo cp scripts/systemd/ga-sprite-birds-api.system.service  /etc/systemd/system/ga-sprite-birds-api.service
# edit User/Group/WorkingDirectory/ExecStart inside the units first
sudo systemctl daemon-reload
sudo systemctl enable --now ga-sprite-birds-core ga-sprite-birds-api

systemctl status ga-sprite-birds-core
journalctl -u ga-sprite-birds-core -f
```

The units auto-restart on failure (`Restart=on-failure`) and stop gracefully (the current
chapter finishes and checkpoints first). Directory permissions, reverse proxy, upgrade &
rollback are covered in [docs/deploy/README.md](../docs/deploy/README.md).

**Windows — NSSM** (keeps the working directory, restarts on crash):

```powershell
nssm install GASpriteBirds-Core "C:\path\to\python.exe" "-m engine run"
nssm set GASpriteBirds-Core AppDirectory "C:\path\to\repo"
nssm install GASpriteBirds-API "C:\path\to\python.exe" "fcgi-bin/api.py"
nssm set GASpriteBirds-API AppDirectory "C:\path\to\repo"
nssm start GASpriteBirds-Core; nssm start GASpriteBirds-API
```

---

## 4. GUI build (development only)

Releases ship a prebuilt single-file `index.html` at the repository root. To work on the
frontend:

```bash
cd gui
npm install
npm run dev      # Vite dev server on :5173, proxies /fcgi-bin to the API
npm run build    # writes the single-file ../index.html
```

> **Windows + network shares**: `vite build` loads a native rollup module that fails on
> SMB/UNC paths. Build on a local disk and copy the resulting `index.html` back.

---

## 5. Troubleshooting

**`python -m engine run` exits immediately with code 2?**
An instance is already running (single-instance lock). Check `python -m engine status`, or stop it first.

**API answers 503 with code 3004?**
The engine is not running, or the port/token does not match. Start the engine first; the API reads its address from `run/engine.json`.

**DB integrity / WAL warnings?**
Run `python -m engine doctor` to check `tasks.db` integrity. Keep `data/` on a local disk; SQLite WAL is unreliable on SMB network drives.

**Voice preview plays nothing?**
Preview uses Edge TTS and needs internet; the first synthesis per voice takes a few seconds (cached under `cache/tts/preview/`).

**How do I run the tests?**

```bash
python -m pytest tests    # integration tests skip when the engine is unreachable
```

---

## Next steps

- Usage: [English README](../README.md) · [中文 README](README.zh.md)
- API endpoints: [docs/api.md](../docs/api.md)
- Operations detail: [docs/deploy/README.md](../docs/deploy/README.md)
