# GA Sprite Birds Developer Guide (v2)

> 中文版：[../zh/developer-guide.md](../zh/developer-guide.md) · Usage guide: [README.md](README.md) · API: [api.md](api.md)

> **Global contract.** This project is developed strictly against the contract in
> `.augment/rules/imported/` (`task-system.md`, `api.md`, `python.md`, `sql.md`,
> `language.md`). If you build on, fork or extend this project, we strongly recommend
> continuing with the same contract and conventions. The design specs in
> [`design/`](design/README.md) refine the contract; where they conflict, the more
> specific design detail wins.

This guide defines the development standards for the v2 architecture (Core engine + thin
Control API, two processes): module boundaries, configuration, the command channel, i18n, GUI
builds and testing. Read it together with the two specs under [`design/`](design/README.md)
before changing code.

---

## 1. Architecture overview

```
┌─────────┐  commands (localhost HTTP + token)  ┌──────────────┐
│ Control │ ──────────────────────────────────▶ │  Core engine  │
│   API   │                                     │  engine/      │
│ fcgi-bin│ ◀───────────── results/events ───── │  sole executor│
│ api.py  │                                     │  sole writer  │
└────┬────┘                                     └──────┬───────┘
     │ read-only queries (PRAGMA query_only)            │ writes
     ▼                                                  ▼
                  data/tasks.db (WAL, single writer / multi reader)
```

**Inviolable boundaries:**

1. **The engine is the only executor and the only writer**: task state, checkpoints and events
   are written by `engine/` only. The API/CLI never writes `tasks.db`.
2. **The API is a thin control plane**: it accepts uploads, forwards commands (idempotent by
   `command_id`) and runs read-only queries with `PRAGMA query_only=ON`.
3. **CLI/API parity**: the CLI does not call business logic directly — it sends commands through
   `services/control/`, exactly like the API. New capabilities must land on both sides.
4. **Config applies to new tasks only**: a task freezes the relevant snapshot
   (`parse_config_snapshot` for parse, `config_snapshot` for generation); running tasks always
   read the snapshot, never live config.

## 2. Layout and module responsibilities

```text
engine/                 Core engine
  __main__.py           python -m engine run/status/doctor
  server.py             localhost HTTP command service (token auth)
  service.py            dispatch: task.* / config.get|set / system.info|stats
  scheduler.py          concurrency, heartbeats, TTL cleanup
  store.py              TaskStore — the only tasks.db writer
  lock.py               single-instance lock (fcntl/msvcrt)
  handlers/             parse / generate / multi_voice / lead_in executors
  migrations/           versioned tasks.db migrations (with rollbacks)
services/
  config_service.py     three-layer config (read/write/reset/hot reload)
  task_query_service.py read-only queries shared by API/CLI
  tts_service.py        voice catalog, validation, preview synthesis
  control/              command-channel client (API/CLI side)
routers/                FastAPI routers (system_config, tts)
models/                 Pydantic request models, task_view serialization
system/                 settings (deployment only), db, logging, envelope, DI
system/config_schema.py single source of truth for business config (7 sections, 46 items)
fcgi-bin/               api.py (thin API), cli.py (control client)
ga_birds/               domain layer (invoked by engine handlers)
  Parser/  LLM/  Audio/  character_analyzer/  Common/  Utils/
gui/                    Vue 3 + Element Plus (build output: root index.html)
```

**Dependency direction**: `fcgi-bin` / `routers` → `services` → `engine` / `ga_birds`.
`ga_birds/` must not import `engine/` or `services/`; business config is read through the
`config` facade (which wraps `system`).

Standalone developer tools under `utils/` follow the [Utils development guide](utils.md).

## 3. Response and error conventions

- Every API response uses the envelope `{"code": 0, "msg": "ok", "data": {}}`, built only via
  `success()/fail()` in `system/response.py`.
- Error-code ranges: `1000` arguments, `2000` auth, `3000` business, `4000` system. Reuse existing
  ranges; do not invent new ones.
- **Error responses (including global 404s and failed previews) must send `Cache-Control:
  no-store`** — 404 is a heuristically cacheable status, and without this browsers replay stale
  failures. Successful reusable binary responses (e.g. previews) use `private, max-age=86400`.
- When the engine is unreachable the API answers HTTP `503` + `code 3004`; it never falls back to
  in-process execution.

## 4. Configuration management

Three layers, with `system/config_schema.py` as the **single source of truth**:

| Layer | Location | Notes |
|-------|----------|-------|
| Defaults | `data/system.db` | versioned seed |
| Overrides | `cache/config/system.json` | atomic write, diffs only; hot-reloaded by `(mtime_ns, size)` signature |
| Task snapshot | `tasks.db.params.config_snapshot` / `parse_config_snapshot` | frozen when generation / parse starts |

**Per-generation overrides** (voice, rate, prosody, LLM, intro/outro, lead-in) are validated in
`engine/service.py::_validate_generation`. They override the task snapshot for that run only and
are never written back to `system.json`.

### Adding a config item (all steps required)

1. `system/config_schema.py`: add `_item(...)` to the right section; pass `description=True` for
   explanatory text. Enums automatically expose `options_i18n`.
2. `ga_birds/Langues/{zh_CN,en_US}.json`: add the label under `config.item`, option translations
   under `config.option.<KEY>.<value>` (`<value>_hint` for the explanation), and field text under
   `config.desc`. **Every enum value must be translated in both languages** — a test enforces this.
3. Run `python scripts/sync_config_i18n.py` to regenerate `gui/src/i18n/lang/config_*.js`.
4. Read values via `business_config_snapshot()` / `use_config_snapshot()` in `config/__init__.py`.
   **Never** capture config at import time — store values as instance attributes (like
   `DialogueParser`) so snapshots take effect.
5. Declare validation with `_item`'s `gt/ge/lt/le/options`; ConfigService rejects invalid values
   uniformly (parameter-range codes such as `1002/1003/1005/1006`, always with `data.key`). Do not
   scatter validation across callers.

## 5. i18n conventions

- `ga_birds/Langues/{zh_CN,en_US}.json` is the **single source of truth**; the frontend config
  translations are generated by the sync script — never hand-edit
  `gui/src/i18n/lang/config_*.js`.
- GUI page copy lives in `gui/src/i18n/lang/{zh_CN,en_US}.js`; add keys in both languages.
- Error messages may be i18n keys (e.g. `config.error.invalid_voice`); the frontend translates
  them when `te()` matches, otherwise displays them as-is.

## 6. Command channel and idempotency

- Command form: `execute(command_id, command, payload)`; command set: `task.*` / `config.get|set` /
  `system.info|stats`.
- `command_id` is idempotent: resubmission returns the first result (`command_log` table). **New
  commands must design an idempotency key**; uploads use `Idempotency-Key` (the on-disk path
  derives from `sha256(key)`).
- State machine: `pending→queued→running→succeeded/failed/canceled`, `running→paused→queued`,
  any→`removed`. Pause/cancel take effect cooperatively at chapter boundaries.
- Recovery: on startup `running` tasks are requeued (resuming from the last succeeded chapter);
  `paused` tasks stay untouched.

## 7. Retries and external calls

- Retry helpers live in `ga_birds/Utils/retry_utils.py`: `RetryableError` / `NonRetryableError`
  classification and `create_retry_decorator()`.
- Default policies: TTS up to 5 attempts with exponential backoff (1s–30s); LLM up to 3 (1s–10s);
  file I/O up to 3 quick retries. Network/rate-limit/timeout errors are retryable; argument and
  auth errors are not.
- SQLite WAL occasionally fails on SMB: the connection layer already retries 3 times and falls
  back to `delete` journal mode — do not wrap another retry around it.

## 8. GUI development

- Stack: Vue 3 + Vite + Element Plus + Pinia + Vue I18n; built as a **single-file** `index.html`
  (`inlineDynamicImports`).
- **On Windows, build from a local disk** (the rollup native module cannot load from UNC/SMB):
  copy `gui/` locally → `npm run build` → copy `index.html` back to the share.
- Always use `--theme-*` semantic variables for colors; explicitly map Element Plus palette
  variables (e.g. `--el-menu-*`) to theme variables at the usage site — defaults are unreliable
  under dark themes (the hover background `primary-light-9` is nearly white).
- Route all API calls through `gui/src/utils/request.js` (envelope unwrapping, error toasts).

## 9. Testing conventions

```bash
python -m pytest tests          # markers: unit / integration / slow
```

- Unit tests live in `tests/unit/` and need no running services; integration tests live in
  `tests/integration/` and **auto-skip** (never fail) when the engine is unreachable.
- Prefer contract tests: schema payloads, enum-translation completeness, cache headers, envelope
  shape — these are worth locking down more than implementation details.
- API behavior changes must update the contract assertions in `tests/unit/test_api_v2.py` and
  [api.md](api.md) together.

## 10. Pre-commit checklist

1. Config schema changed → add both-language translations + run `sync_config_i18n.py` + run the
   related tests.
2. API/CLI behavior changed → update [api.md](api.md) and the parity matrix.
3. Frontend changed → rebuild on a local disk and copy `index.html` back.
4. `python -m pytest tests` is green.
5. Deployment touched → update [deployment.md](deployment.md).
