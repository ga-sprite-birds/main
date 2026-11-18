# v2 Design: Fully Separate Task Execution from the API Presentation Layer (Headless Core)

> 中文版：[../../zh/design/v2-headless-core.md](../../zh/design/v2-headless-core.md)
>
> Status: implemented (this document retains the design notes)
> Applies to: v2 absolute technical refactor
> Contract basis: `task-system.md` (Core/Control API separation, state machine, events, recovery, single instance, graceful shutdown, runtime discovery), `api.md` (response structure, dual entry points → this version only `/fcgi-bin/api/*`), `python.md` (layering)
> Core goal: **the engine (Core) runs as an independent daemon; the API is only a control plane. Killing the API does not stop tasks; Core is maintained by the system layer (systemd) or manually.**
> Related document: `v2-system-config.md` (config system / ConfigService); the master contract is in `.augment/rules/imported/`

---

## 1. Requirements overview

- Separate the "task execution engine" and the "API presentation layer" at the **process level**.
- Core is the sole executor and the sole writer of task state; the API only sends commands and performs read-only queries.
- Closing FastAPI does not affect running tasks; Core can run under systemd or be started manually and temporarily.
- `fcgi-bin/` keeps only the API entry point; no Core code lives there.
- CLI and API are peers, both acting as Core clients; they no longer execute tasks inline.

---

## 2. Process model and responsibilities

```text
            commands (local HTTP)              read-only queries
GUI / CLI ───────────────► Control API(api.py) ─────────┐
                                  │ command forwarding   │ read-only open
                                  ▼                      ▼
                          Command Channel           tasks.db(SQLite WAL)
                                  │                      ▲ sole writer
                                  ▼                      │
                          Core engine(engine/, daemon) ──┘
                           ├─ Scheduler(concurrency/pause/cancel/retry)
                           ├─ Handlers(parse/generate/multi_voice/lead_in) → ga_birds
                           ├─ TaskStore(tasks.db)
                           ├─ single-instance lock + runtime discovery file
                           └─ recovery / graceful shutdown
```

| Role | Responsibilities | Does not do |
|---|---|---|
| Core (engine) | Execute tasks, schedule, recover, **sole writer of tasks.db**, serve the local command channel | Does not depend on the API/GUI being alive |
| Control API (api.py) | Receive commands, forward to Core, **read-only** tasks.db queries, serve the GUI | No long-running tasks, no task-state writes, no imports of Audio/LLM/Parser |
| Command Channel | localhost HTTP (127.0.0.1) + token | Carries no business rules |
| Client (CLI/GUI) | Send commands, display status | Never reads/writes task storage directly |

---

## 3. Command channel (cross-platform)

- **Transport**: localhost HTTP, `127.0.0.1:<port>` (avoids UDS compatibility problems on Windows).
- **Authentication**: Core generates a random `token` at startup and writes it to the runtime discovery file; API/CLI call with `Authorization: Bearer <token>`.
- **Runtime discovery file**: `run/engine.json` (mode 0600), fields:
  ```json
  { "app":"ga-sprite-birds", "pid":12345, "host":"127.0.0.1", "port":39211,
    "protocol_version":1, "token":"...", "started_at":"..." }
  ```
  Nothing beyond what is needed; the token is sensitive but visible only on the local machine, and file permissions are tightened.
- **Protocol**: JSON.
  - `POST /command`: `{ "command_id":"uuid", "command":"task.add", "payload":{...} }`
  - `GET /system/info`, `GET /system/stats`
- **Idempotency**: deduplicate by `command_id`; re-submitting returns the same result (see `command_log` in §4).
- **Command set** (per `task-system.md` §4.1, plus v2 additions): `task.add / parse / generate / pause / resume / cancel / retry / remove / cleanup / update_options / chapter.remove`, `config.get/set`, `system.info / system.stats`.
- **Queries do not go through the command channel**: status/history are read **directly** from `tasks.db` by the API (satisfying "history remains queryable while Core is down").

---

## 4. tasks.db (SQLite WAL, Core single-writer / API read-only)

> Path: `data/tasks.db`. Core uses a read-write connection (WAL); the API uses a read-only connection (`?mode=ro` or `PRAGMA query_only=1`).

### 4.1 tasks
| Column | Description |
|---|---|
| task_id TEXT PK | Task ID (globally unique, never reused) |
| type TEXT | Task type (e.g. audiobook) |
| status TEXT | pending/queued/running/paused/succeeded/failed/canceled/removed |
| phase TEXT | Sub-phase (parsing/generating, for UI; not contract-required) |
| params_json TEXT | Task parameter snapshot (voice/rate/chapters/enable_llm/output_path/prosody…) |
| result_json TEXT | Result |
| error TEXT | Error message |
| total_chapters INT | Total chapters |
| completed_chapters INT | Completed chapters |
| attempts INT | Attempt count |
| heartbeat_at / queued_at / started_at / finished_at | Timestamps |
| created_at / updated_at | Required |
| idempotency_key TEXT | Idempotency key |

### 4.2 task_chapters
| Column | Description |
|---|---|
| task_id, chapter_index | Composite primary key |
| title / status / audio_path / error | Chapter progress |
| attempts INT | |
| started_at / finished_at | |

### 4.3 task_events
| Column | Description |
|---|---|
| event_id INTEGER PK AUTOINCREMENT | Monotonic; clients resume with a cursor |
| task_id / type / payload_json / created_at | Event |

### 4.4 command_log (idempotency)
| Column | Description |
|---|---|
| command_id TEXT PK | Idempotency |
| command / payload_hash / status / result_json / created_at | |

### 4.5 schema_meta
- `id=1, tasks_schema_version, updated_at`: migration version.

> Connection model: `TaskStore` opens an **independent SQLite connection per thread** (the command HTTP thread and the asyncio scheduler thread never share one), released by `close_thread_connection()` at request end; `engine doctor/status` access with read-only connections, and schema migrations run only in Core at startup.

> Migrations: versioned and reversible (per `sql.md`).

---

## 5. State machine and events

- States and transitions strictly follow `task-system.md` §5:
  ```text
  pending -> queued -> running -> succeeded / failed / canceled
  running -> paused -> queued
  failed  -> queued (retry)
  any     -> removed (tombstone)
  ```
- Illegal transitions are rejected with an error code.
- `cancel` (stop a task) ≠ `remove` (delete the record); the semantics are never mixed.
- Events (§4.2): `task.created/started/progress/paused/resumed/succeeded/failed/canceled/removed/log`, monotonic `event_id`.
- **Polling first in this round** (`GET status` reads tasks.db); `task_events` is already persisted, and SSE is a later enhancement.

---

## 6. Core / engine design

- **Entry point**: `python -m engine run` (`engine/__main__.py`); inspect with `engine status`.
- **Scheduler**: dispatches `queued → running` according to `TASK_MAX_CONCURRENT`; provides pause/cancel/retry.
- **Handlers**: `parse / generate / multi_voice / lead_in`, calling `ga_birds` business logic; chapter-level loops, writing a checkpoint + event after each chapter.
- **Parse is a background task**: the `task.parse` command only enqueues the task and returns immediately (`phase=parsing`); an engine parse worker performs it. On completion `phase=ready`; on failure `phase=parse_failed`; clients poll `phase`.
- **Lead-in generation**: if `CHAPTER_LEAD_IN_ENABLED` is enabled (overridable per run by the `chapter_lead_in_enabled` generation option) and the task has no lead-in chapter, the generate stage calls the LLM to produce one and inserts it as chapter 0 (`000-导读篇`). If the LLM is unavailable, it is skipped and generation continues.
- **Per-run intro/outro override**: `CHAPTER_INTRO_OUTRO` can be overridden by the `chapter_intro_outro` generation option for the current run only.
- **Single-instance lock**: `run/engine.lock` (fcntl, with msvcrt compatibility on Windows) prevents duplicate consumption.
- **Graceful shutdown** (SIGTERM/SIGINT): stop accepting new commands → reach a safe point/checkpoint in the current chapter → save → release the lock → exit; force-kill after the grace period is logged, leaving no orphans.
- **Recovery** (see §12).
- **Command service**: localhost HTTP + token + idempotency (§3).
- **Config**: read the latest config (DB defaults + system.json overrides) at the start of each task, see §9.

---

## 7. API layer (thin)

- **Entry point**: `python -m server run` (the `server/` package, loading the app from `fcgi-bin/api.py`; **no policy** in this version).
- Routes only: parse input (Pydantic) → build a command for Core / read-only tasks.db query → unified response.
- **Forbidden**: importing `Audio/LLM/Parser`, task loops, task-state writes.
- Route set: `upload / parse / generate / pause / resume / cancel / delete / retry / status / chapter / events / tasks / cleanup / system-config / tts-voices / tts-preview / GUI`.
- Unified response `{code, msg, data}` (`api.md`).
- Serves GUI static assets.
- **When Core is unavailable**: command endpoints return an explicit error ("engine not running"); query endpoints can still read history from tasks.db.

---

## 8. CLI

- Acts as a Core client (`fcgi-bin/cli.py`) over the same localhost HTTP command channel; no inline execution.
- Feature parity with the API: `add/list/get/pause/resume/cancel/retry/remove/status/logs/events`; supports `--follow` (follow progress) and `--json`.
- Shares `services/control/*` with the API (parameter validation, command construction, status formatting); never duplicate business rules.

---

## 9. Config across processes

- Core reads `ConfigService` (`data/system.db` defaults + `cache/config/system.json` overrides) **at the start of each task**.
- Therefore: **config changes affect only tasks started afterwards; running tasks are unchanged**.
- The GUI and docs must state this explicitly (so users do not expect new config to apply to in-flight tasks).

---

## 10. Deployment

### 10.1 systemd (recommended daemon)

`ga-sprite-birds-core.service`
```ini
[Unit]
Description=GA Sprite Birds Core Engine
After=network.target

[Service]
WorkingDirectory=/opt/ga-sprite-birds
ExecStart=/opt/ga-sprite-birds/.venv/bin/python -m engine run
Restart=on-failure
User=ga
# Environment variables/secrets come from .env or EnvironmentFile

[Install]
WantedBy=multi-user.target
```

`ga-sprite-birds-api.service`
```ini
[Unit]
Description=GA Sprite Birds API
After=network.target ga-sprite-birds-core.service

[Service]
WorkingDirectory=/opt/ga-sprite-birds
ExecStart=/opt/ga-sprite-birds/.venv/bin/python -m server run
Restart=on-failure
User=ga

[Install]
WantedBy=multi-user.target
```

### 10.2 Manual temporary start
```bash
python -m engine run          # foreground daemon
python -m server run          # start the API in another terminal
```

---

## 11. Directory structure (new/adjusted)

```text
project/
├── fcgi-bin/
│   ├── api.py                  # sole API entry point
│   └── cli.py                  # CLI (Core client)
├── engine/                     # Core engine (system-layer service)
│   ├── __main__.py             # python -m engine run
│   ├── server.py               # local command HTTP + token + discovery file
│   ├── scheduler.py
│   ├── handlers/               # parse / generate / multi_voice / lead_in
│   ├── store.py                # TaskStore(tasks.db, read-write; recovery lives here)
│   └── lock.py
├── services/
│   └── control/                # control layer shared by API/CLI
├── routers/                    # API routes (thin)
├── models/                     # Pydantic
├── system/                     # config / response / db / deps
├── data/
│   ├── system.db               # config defaults (previous requirement)
│   └── tasks.db                # task state (this requirement)
├── run/
│   ├── engine.json             # runtime discovery (port/token/pid)
│   └── engine.lock
└── ...
```

---

## 12. Recovery strategy (aligned with aria2's approach)

At startup Core handles tasks according to their **persisted state**:

| State before restart | Behavior after restart |
|---|---|
| `running` (crash/restart interruption) | **Resume automatically**: the interrupted chapter goes `running→pending` and reruns; completed chapters are kept; the task returns to `queued/running` |
| `paused` (user-stopped) | **Stay paused**, do not run automatically; wait for a user `resume` |
| `pending` / `queued` | Enqueue and run normally |
| `succeeded` / `failed` / `canceled` / `removed` | Keep as is |

- Criterion: `paused` is produced only by user action; a crashed task remains `running`, which is the signal to resume.
- Chapter-level checkpoint: chapters already `succeeded` are skipped; interrupted chapters rerun from the start (overwrite, idempotent).
- Guarantees: no duplicate consumption, no orphan workers (single-instance lock + atomic claim).

---

## 13. Acceptance checklist (from contract §13, implemented)

- After closing the API, Core continues executing tasks.
- After Core stops, the API can still query historical status (read-only tasks.db).
- Core restart: `running` resumes, `paused` stays paused, completed tasks remain queryable; no duplicate consumption/orphans.
- Concurrent submissions from multiple clients do not create duplicate tasks; the same `command_id` returns the same result.
- Two Core instances never consume simultaneously (single-instance lock works).
- CLI and API return consistent business results/error codes; the CLI does not execute long tasks inline.
- Graceful shutdown: after SIGTERM the current chapter exits at a safe point and saves; forced kills are logged.
- The runtime discovery file exists and contains no unrelated sensitive information.

---

## 14. Implementation steps

1. Create the `engine/` package + `system/db.py` dual-database connections (system.db read-only config, tasks.db read-write) + the `run/` directory.
2. `tasks.db` schema + migrations (`tasks / task_chapters / task_events / command_log / schema_meta`).
3. `TaskStore` (Repository) + atomic claim/heartbeat.
4. Extract `_generate_audio_task` and orchestration from `api.py` into `engine/handlers` + `scheduler`.
5. Local command HTTP + token + runtime discovery + idempotent `command_log`.
6. Single-instance lock + graceful shutdown + recovery (§12).
7. Make `api.py` thin: command forwarding + read-only queries; remove business execution.
8. Turn `cli.py` into a Core client.
9. Extract `services/control` shared by API/CLI.
10. systemd units + manual-start docs; add the "config applies only to new tasks" notice to the GUI/docs.
11. Tests: process separation, restart recovery, idempotency, concurrency, acceptance checklist.

---

## 15. Settled details

1. **Command service port**: `39300` by default; when occupied it **falls forward** (39301, 39302…); the actual port is written to the discovery file.
2. **Runtime directory**: configurable via `RUN_DIR`. Development/manual and the shipped systemd units keep the project-root `run/` (writable via `ReadWritePaths`). If you prefer a tmpfs runtime directory, set `RUN_DIR=/run/ga-sprite-birds` and add `RuntimeDirectory=ga-sprite-birds` to the unit. Discovery file mode 0600.
3. **Expiry cleanup**: `TASK_RESULT_TTL` becomes a DB cleanup task, supporting two modes:
   - **Periodic automatic cleanup** (timer inside the engine);
   - **CLI cleanup**: `cli.py clean` → sends `task.cleanup` to the engine, which executes it (the engine has exclusive write access).
4. **Operational commands**: this round provides `engine status` (PID/port/task counts) and `engine doctor` (checks directories, permissions, ffmpeg, DB, config, port).
5. **Progress retrieval**: **polling first** in this round (`GET status` reads tasks.db); `task_events` is already persisted, and **SSE is a later enhancement** that does not change the data structure.

### Appendix: runtime directory notes
- `run/` (or the directory configured by `RUN_DIR`) stores `engine.json` (discovery file: host/port/token/pid/protocol version/start time) and `engine.lock` (single-instance lock).
- Manual runs and the shipped systemd units use the project `run/`. If `RUN_DIR` points to `/run/...`, systemd can create it with `RuntimeDirectory`.
