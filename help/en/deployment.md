# Deployment and Operations

> 中文版：[../zh/deployment.md](../zh/deployment.md) · Usage guide: [README.md](README.md) · Development: [development.md](development.md)

v2 always runs as **two processes**:

```
┌──────────────────────────┐        localhost HTTP + Bearer token
│  Core engine (engine)    │◀──────────────────────────────┐
│  · sole executor         │                               │
│  · sole writer of        │                               │
│    data/tasks.db         │                               │
│  · single-instance lock  │                               │
│    run/engine.lock       │                               │
│  · discovery file        │                               │
│    run/engine.json (0600)│                               │
└──────────────────────────┘                               │
                                                           │
┌──────────────────────────┐       read-only data/tasks.db │
│  Control API (api.py)    │───────────────────────────────┘
│  · receives uploads,     │
│    forwards commands     │
│  · read-only task queries│
│  · serves GUI + config UI│
└──────────────────────────┘
```

Stopping the API does not interrupt running tasks. After an engine restart, `running` tasks
resume from the last successful chapter, while `paused` tasks stay paused until a manual
`resume`.

> Production deployment options are **Docker (recommended)** and **venv (native)**. conda is a
> development-only environment (see [development.md](development.md)).

---

## 1. Docker (recommended)

The repo ships a `Dockerfile` + `docker-compose.yml` that run the Core engine and the Control API
in one container (they share loopback, so the API can reach the engine command channel).

```bash
cp .env.example .env          # configure LLM credentials
mkdir -p data run cache output logs uploads
sudo chown -R 1000:1000 data run cache output logs uploads
docker compose up -d --build
# GUI: http://127.0.0.1:8000/
docker compose logs -f
docker compose down
```

- Persistent data: `./data ./run ./cache ./output ./logs ./uploads` (bind mounts).
- Inside the container `API_HOST=0.0.0.0`; the compose file publishes to **127.0.0.1** by default.
  Change the host port with `API_HOST_PORT=18080 docker compose up -d --build`.
- For LAN access set `API_BIND_HOST=0.0.0.0` **and** enable auth:
  ```env
  API_BIND_HOST=0.0.0.0
  API_AUTH_ENABLED=true
  API_AUTH_TOKEN=<a long random token>
  ```
  Clients use `Authorization: Bearer <token>`; the GUI key button stores the token locally.
- CORS is disabled by default. If a separate frontend origin needs it, set
  `API_CORS_ENABLED=true` and an explicit `API_CORS_ORIGINS`; never use `*`.
- The engine command channel (`127.0.0.1:39300`) is never exposed.
- The image runs as the unprivileged `app` user (UID/GID `1000:1000` by default). Before the
  first start, make the bind mounts writable by that user:
  ```bash
  mkdir -p data run cache output logs uploads
  sudo chown -R 1000:1000 data run cache output logs uploads
  ```
  If your host user has a different UID/GID, set `APP_UID`/`APP_GID` in `.env` and rebuild with
  `docker compose up -d --build`; compose passes them as build args.
- The Docker daemon itself normally runs as root; the container process does not. Use rootless
  Docker if you also want to isolate the daemon.
- Compose drops all Linux capabilities and sets `no-new-privileges`; runtime files are `0600`
  and volume directories are `0700`.
- `models/` is the Python package inside the image; model caches are written to `./cache/models`.
- Docker and a host engine **must not share** `data/` or `run/` at the same time (single-instance
  lock): stop the host `engine`/`server` before switching, or run compose from a separate
  directory.
- No Python or FFmpeg is needed on the host; both live in the image.
- To split horizontally, turn it into two services (`engine` / `api`) and use
  `network_mode: service:engine` so the API shares the engine's loopback.

---

## 2. venv (native)

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env

# Terminal 1: Core engine (foreground; Ctrl+C exits gracefully)
python -m engine run

# Terminal 2: Control API + GUI
python -m server run
```

`python -m server run` is optional for **CLI-only** use: the CLI talks to the engine directly.
Start only `python -m engine run` when you do not need the GUI or HTTP API; start both processes
when you do.

API auth is optional but mandatory when binding beyond loopback. Set
`API_AUTH_ENABLED=true` + `API_AUTH_TOKEN` in `.env`; clients use
`Authorization: Bearer <token>`, and the GUI key button stores the token in the browser.

Install FFmpeg first (`apt install ffmpeg`, `brew install ffmpeg`, or the Windows build) and verify
with `ffmpeg -version`; alternatively set `FFMPEG_PATH`.

Health checks:

```bash
python -m engine status          # pid / port / task counts
python -m engine doctor --json   # directories, permissions, tasks.db, ffmpeg, discovery
curl -s http://127.0.0.1:8000/fcgi-bin/api/status
```

The engine listens on `127.0.0.1:39300` by default and falls forward when the port is taken; the
actual port is written to `run/engine.json`. The API listens on `127.0.0.1:8000` by default,
controlled by `API_HOST` / `API_PORT`; it auto-shifts to a free port unless `--strict-port` is set.

### Routine operations

```bash
# Engine status and self-check
python -m engine status
python -m engine doctor

# CLI and API are peers: every command goes through the engine
python fcgi-bin/cli.py list --status running
python fcgi-bin/cli.py status <task_id>
python fcgi-bin/cli.py pause <task_id>
python fcgi-bin/cli.py resume <task_id>
python fcgi-bin/cli.py cancel <task_id>
python fcgi-bin/cli.py remove <task_id> --delete-outputs
python fcgi-bin/cli.py events <task_id> --follow
python fcgi-bin/cli.py clean --ttl-seconds 86400 --dry-run

# System config (same ConfigService as the GUI)
python fcgi-bin/cli.py config get TTS_VOICE
python fcgi-bin/cli.py config set TTS_RATE 1.15
python fcgi-bin/cli.py system info
```

---

## 3. systemd

Unit templates live in [`scripts/systemd/`](../../scripts/systemd/):
`ga-sprite-birds-core.{user,system}.service` and `ga-sprite-birds-api.{user,system}.service`.
The system variants include hardening and expect `/opt/ga-sprite-birds` with a `.venv`.

User-level (no root; starts with your login session):

```bash
mkdir -p ~/.config/systemd/user
cp scripts/systemd/ga-sprite-birds-core.user.service ~/.config/systemd/user/ga-sprite-birds-core.service
cp scripts/systemd/ga-sprite-birds-api.user.service  ~/.config/systemd/user/ga-sprite-birds-api.service
systemctl --user daemon-reload
systemctl --user enable --now ga-sprite-birds-core ga-sprite-birds-api
```

To keep user services running after logout: `sudo loginctl enable-linger "$USER"`.

System-level (starts at boot, independent of login):

```bash
sudo useradd --system --create-home --home-dir /opt/ga-sprite-birds gasprite
sudo cp -r . /opt/ga-sprite-birds
# edit User/Group/WorkingDirectory/ExecStart inside the units first
sudo cp scripts/systemd/ga-sprite-birds-core.system.service /etc/systemd/system/ga-sprite-birds-core.service
sudo cp scripts/systemd/ga-sprite-birds-api.system.service  /etc/systemd/system/ga-sprite-birds-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now ga-sprite-birds-core ga-sprite-birds-api
```

Inspect and troubleshoot:

```bash
systemctl status ga-sprite-birds-core
journalctl -u ga-sprite-birds-core -f
journalctl -u ga-sprite-birds-api -f
```

Single-instance protection: when two Core processes contend for the same `run/engine.lock`, the
later one exits immediately with code `2`, so `tasks.db` is never double-written.

### 3.1 Windows — NSSM

```powershell
nssm install GASpriteBirds-Core "C:\path\to\repo\.venv\Scripts\python.exe" "-m engine run"
nssm set GASpriteBirds-Core AppDirectory "C:\path\to\repo"
nssm install GASpriteBirds-API "C:\path\to\repo\.venv\Scripts\python.exe" "-m server run --strict-port"
nssm set GASpriteBirds-API AppDirectory "C:\path\to\repo"
nssm start GASpriteBirds-Core; nssm start GASpriteBirds-API
```

### 3.2 Upgrade and rollback

```bash
# Upgrade: stop the API first (frontend 503), then stop Core after the current chapter finishes; replace the code and start them in order
sudo systemctl stop ga-sprite-birds-api
sudo systemctl stop ga-sprite-birds-core     # forced kill only after TimeoutStopSec
sudo -u gasprite git -C /opt/ga-sprite-birds pull
sudo systemctl start ga-sprite-birds-core
sudo systemctl start ga-sprite-birds-api
```

`data/tasks.db` migrations ship with the code: the engine runs versioned migrations at startup
(`engine/migrations/`); upgrades only move forward. Back up `data/` and
`cache/config/system.json` before rolling back code.

---

## 4. Paths and permissions

| Path | Writer | Description |
|------|--------|------|
| `data/tasks.db` | Core only | Tasks, chapters, events, command idempotency log; WAL; mode `0600` |
| `data/system.db` | Core/API seed + migrations | Config defaults; both processes seed missing keys on first start; mode `0600` |
| `cache/config/system.json` | API / Core (atomic replace) | User overrides; both sides reload automatically based on the file signature |
| `run/engine.json` | Core | Discovery file (host/port/token/pid), mode `0600` |
| `run/engine.lock` | Core | Single-instance lock |
| `uploads/` | API | Uploaded source files (directory `0700`, files `0600`) |
| `output/` | Core | Generated audio and chapter text |
| `logs/` | Both | Rotating per-process logs |

`run/engine.json` contains the Bearer token (`0600`, readable only by the owner). This conflicts
with the early contract statement that "the discovery file contains no credentials"; v2
deliberately keeps the token in that file because the command channel binds only to
`127.0.0.1` and the token lifetime matches the process. Splitting it into another file would add
another synchronization failure point. If your environment requires credentials to be separated
from discovery data, move the `token` field to `run/engine.token` (also `0600`); clients only need
to change the reader in `engine/runtime.py`.

---

## 5. Reverse proxy (optional)

The GUI and API share an origin, so the proxy only needs to pass requests through:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_read_timeout 600s;   # large uploads
    client_max_body_size 100m; # match API_MAX_UPLOAD_SIZE
}
```

**Do not** expose `127.0.0.1:39300` (the engine command channel).
