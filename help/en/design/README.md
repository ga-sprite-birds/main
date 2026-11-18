# v2 Design Docs · Developer Index

> 中文版：[../../zh/design/README.md](../../zh/design/README.md)
>
> You are the developer: **implement strictly according to the documents in this directory.**
> This directory is the implementation design for the v2 "absolute technical refactor"; the master contract lives in `.augment/rules/imported/`.
> On conflict: the "settled details" in this directory win (they are more specific); anything not covered follows the contract.

---

## 1. Document index

| Document | Contents | Status |
|---|---|---|
| `v2-system-config.md` | env split / system config: three-layer configuration, `ConfigService`, system-config API, TTS voice validation, GUI config page | ✅ Final |
| `v2-headless-core.md` | Process-level separation of task execution and API presentation: `engine/` Core, command channel, `tasks.db`, state machine, recovery, systemd | ✅ Final |

Together the two documents form the first v2 refactor round and **ship as one unit**.

---

## 2. Relationship between the two requirements

```
v2-system-config： ConfigService (reads system.db defaults + system.json overrides)
        │ read by
        ▼
v2-headless-core： engine (reads config at the start of each task)  ── sole writer of tasks.db
                  api.py (thin control plane, read-only tasks.db) ── only sends commands
```

- `system/db.py` provides both connections: `system.db` (config defaults) and `tasks.db` (task state).
- `ConfigService`: **the API writes `system.json`**; **the engine reads the effective config**.

---

## 3. Shared conventions (both documents; must be followed)

1. **Contract first**: follow `.augment/rules/imported/` (`task-system.md` / `api.md` / `python.md` / `sql.md` / `language.md`). **Ignore non-Python parts (php/vue/vite).**
2. **Entry points**:
   - `python -m server run` (the `server/` package) — the only API entry point; **no policy in this version**, only `/fcgi-bin/api/*`.
   - `fcgi-bin/cli.py` — CLI, acting as a Core client.
   - `engine/` — Core engine, `python -m engine run` (systemd at the system layer, or manual).
3. **Responses**: `{ code: 0 for success, msg, data }`; error codes are segmented 1000~4999 (see `api.md`).
4. **Naming**: fields use `snake_case`; pagination uses `list / total / page / page_size`.
5. **i18n**: Chinese and English by default (`en_US` / `zh_CN`; `ja_JP` may be retained); config section/item labels and response copy use i18n keys (`ga_birds/Langues/*.json`).
6. **Directories**: `system/ services/ routers/ models/ engine/ fcgi-bin/ data/ run/ core_module(=ga_birds)/`.
7. **Config layering**: `.env` = deployment/secrets; `data/system.db` = defaults; `cache/config/system.json` = user overrides; **business parameters go through the API / task options**.
8. **Database**: SQLite + WAL; `data/system.db`, `data/tasks.db`; follow `sql.md` (table/column comments, primary keys, `created_at/updated_at`, no `SELECT *`, always `LIMIT`).
9. **Write ownership**: **only the engine writes `tasks.db`**; **the API is read-only**. `ConfigService`: the API writes `system.json`; the engine reads it.
10. **Recovery**: `running` (crashed/interrupted) → resume automatically; `paused` (user-stopped) → stay paused.
11. **No legacy compatibility**: drop the old `config.X` env-reading style; old business parameters no longer come from env.
12. **Config effect**: changes apply only to tasks **started afterwards**; the GUI and docs must state this explicitly.

---

## 4. Implementation order and dependencies

> Suggested order; later phases depend on earlier outputs.

**Phase 0 · Skeleton and shared foundation**
- Create directories: `system/ services/ routers/ models/ engine/ data/ run/`
- `system/response.py` (unified `{code,msg,data}`), `system/db.py` (system.db/tasks.db connections, WAL)
- `system/config.py` (pydantic-settings, deployment/secrets only)

**Phase 1 · Config system (`v2-system-config.md`)**
- `system/config_schema.py` (schema + seeded defaults)
- Seed `data/system.db` + `ConfigService` (including `system.json` overrides/reset/hot reload)
- `routers/system_config.py`, `routers/tts.py`
- TTS voice cache and validation

**Phase 2 · Task engine (`v2-headless-core.md`)**
- `data/tasks.db` schema + migrations + `TaskStore` (Repository)
- Extract `_generate_audio_task` from `api.py` into `engine/handlers` + `engine/scheduler`
- Local command HTTP + token + runtime discovery file + idempotent `command_log`
- Single-instance lock, graceful shutdown, recovery (§12)
- `engine status` / `engine doctor` / `task.cleanup`

**Phase 3 · Thin API + CLI**
- `api.py` becomes thin (command forwarding + read-only queries, business execution removed)
- `cli.py` becomes a Core client
- `services/control/` shared by API and CLI

**Phase 4 · GUI**
- System config page (grouped rendering, save/reset, override badges, "applies only to new tasks" notice)
- Progress via polling (SSE later)

**Phase 5 · Wrap-up**
- Refactor every `ga_birds` config read
- Slim down `.env/.env.example` + update docs
- systemd examples + manual-start instructions
- Unit tests + acceptance checklist

**Dependencies**: Phase 1 ⇐ Phase 0; Phase 2 ⇐ Phase 0 (config reading depends on Phase 1); Phase 3 ⇐ Phase 2; Phase 4 ⇐ Phase 1 + Phase 3.

---

## 5. Decision log (confirmed)

- License: Apache-2.0 (see `LICENSE` in the repo).
- Config defaults: `data/system.db`; user overrides: `cache/config/system.json` (partial override; only the last modification of each key is kept).
- `*_DIR` belongs to deployment (the API does not interfere); `OUTPUT_BASE_PATH` belongs to business config (managed by the API).
- Command channel: **localhost HTTP + token + runtime discovery file** (cross-platform, no UDS).
- Core package name: `engine/`; entry point `python -m engine run`.
- State database: `data/tasks.db` (WAL), **engine single-writer / API read-only**.
- API structure: `python -m server run` (the `server/` package) is the only entry point, **no policy**.
- Port: `39300` by default; falls forward when occupied.
- Runtime directory: configurable (development `run/`; systemd `RuntimeDirectory`).
- Cleanup: periodic automatic + `cli.py clean` (the engine executes `task.cleanup`).
- Operational commands: `engine status` / `engine doctor`.
- Progress: **polling** in this round; SSE later.
- Recovery: `running` → resume; `paused` → stay paused.
- **Async parse**: `task.parse` returns immediately (`phase=parsing`); an engine background worker performs the parse and finishes with `phase=ready` / `phase=parse_failed`; clients poll `phase`.
- **Database connections**: `TaskStore` uses one connection per thread, released at request end; `engine doctor/status` are read-only and do not migrate.
- **No policy**: the GUI uses business routes `/dashboard`, `/theme`, `/system/config`; the backend only does SPA fallback and has no `/policy` API.

---

## 6. Global acceptance (end-to-end)

In addition to each document's own acceptance checklist, all of the following must hold:

- **Kill the API**: running tasks continue (Core is independent).
- **Kill/restart Core**: `running` tasks resume; `paused` tasks stay paused; completed tasks remain queryable; no duplicate consumption, no orphans.
- **Core down**: the API can still query history (read-only `tasks.db`).
- **Config change**: applies only to tasks started afterwards.
- **Idempotency**: re-submitting the same `command_id` returns the same result.
- **Single instance**: two Core instances never consume tasks simultaneously.
- **Unified response**: every API returns `{code,msg,data}`.

---

## 7. Implementation status (v2 delivery record)

All five phases are complete; `pytest tests/unit` is green (101 tests); real end-to-end integration tests live under `tests/integration/`.

| Phase | Deliverables | Verification |
|-------|--------|----------|
| 0 Skeleton | `system/response.py`, `system/db.py`, `system/config.py` | Unit tests + `engine doctor` |
| 1 Config | `system/config_schema.py` (7 sections, 46 items), `ConfigService`, `routers/system_config.py`, `routers/tts.py` | `tests/unit/test_config_service.py`, `test_system_config.py` (26 tests, including cross-instance hot reload) |
| 2 Engine | `engine/` (store/scheduler/service/handlers/lock/runtime/ops), `tasks.db` migrations | `test_engine_store.py`, `test_engine_service.py` |
| 3 Thin API + CLI | `server/` (Control API launcher), `fcgi-bin/api.py`, `fcgi-bin/cli.py`, `services/control/`, `services/task_query_service.py` | `test_api_v2.py` (20 contract tests) |
| 4 GUI | `gui/src/views/system/` + `ConfigField.vue`, route `/system/config`, 7 sidebar groups, i18n, single-file build | `vite build` passes + config API end-to-end |
| 5 Wrap-up | Slim `.env`, deployment docs (systemd + operations), [API reference](../api.md), README rewrite, test migration | `pytest tests/unit` 101 passed |

### Acceptance evidence

| Acceptance item | Result |
|--------|------|
| Kill the API, tasks continue | ✅ Core schedules independently; `engine status` still shows the worker running |
| Restart Core and resume | ✅ Killed during chapter 3: event `task.recovered{action:"requeued"}` → `task.started{attempts:2}` → terminal `task.succeeded{generated:[3,4], skipped:[1,2]}` |
| API read-only while Core is down | ✅ `GET /task/{id}/status` returns `code 0` (`running, 2/4`); `GET /engine` returns `503`/`3004` |
| Config applies only to new tasks | ✅ `params.config_snapshot` is frozen when the task is created; `ConfigService` reloads by file signature, so the engine instance sees new values immediately after the API writes them |
| Idempotency | ✅ The same `Idempotency-Key` returns the same `task_id` (the on-disk path is derived from the key); the same `command_id` with different input returns `3001` |
| Single instance | ✅ A second `python -m engine run` exits immediately with code `2` |
| Unified response | ✅ Every route returns `{code,msg,data}`; unknown routes `404`+`3002`; engine unavailable `503`+`3004` |
| Enum options are explained | ✅ The schema exposes `options_i18n` / `description_i18n`; GUI options show translations + grey descriptions, and the selected value's meaning appears below the field (`off/pause/prosody` no longer leak English) |

### Two deviations from the early contract (declared in the docs)

1. `run/engine.json` contains the Bearer token (`0600`). `task-system.md` §3.4 requires discovery files to be credential-free;
   v2 merges them because the command channel binds only to `127.0.0.1` and the token lifetime equals the process lifetime.
   To separate them, move `token` to `run/engine.token`; only `engine/runtime.py` needs to change.
2. WAL may fail on SMB/UNC shares because `-shm` cannot be created. `system/db.py` now retries `PRAGMA journal_mode=WAL` three times and degrades to a rollback journal, so writes still work on network drives.

### Known limitations

- `vite build` depends on rollup native modules; on Windows it cannot build from a UNC share (use a local disk).
- The GUI does not expose multi-voice generation or character analysis. Multi-voice generation is available through the CLI/API with a supplied character template; character analysis is not exposed by the v2 add flow.
- Progress is still polling (SSE later).
