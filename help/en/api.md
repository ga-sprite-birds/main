# Control API Reference (v2)

> 中文版：[../zh/api.md](../zh/api.md)

All business endpoints live under the `/fcgi-bin/api` prefix. The Control API is started by `python -m server run` (the `server/` package); the FastAPI app lives in `fcgi-bin/api.py` and is a thin control plane:
**it does not execute tasks** — it only validates parameters, forwards commands, and serves read-only queries.

- Uploads and command forwarding → Core engine (localhost HTTP + Bearer token)
- Status/events/list/chapters → read-only `data/tasks.db` (`PRAGMA query_only=ON`)
- System config → `ConfigService` (`data/system.db` defaults + `cache/config/system.json` overrides)

Unified response envelope:

```json
{"code": 0, "msg": "ok", "data": {}}
```

| Code range | Meaning |
|---------|------|
| `0` | Success |
| `1000~1999` | Parameter/validation errors (missing field, type, range, enum, regex, template) |
| `2000~2999` | Authentication |
| `3000~3999` | Business errors (task not found, invalid state, illegal transition, idempotency conflict) |
| `4000~4999` | System errors (internal exception, config read/write failure) |

Special HTTP statuses: engine not running → `503` + `code 3004`; unknown routes such as docs/Swagger → `404` + `code 3002`; a corrupted/unreadable `data/tasks.db` → HTTP `200` + `code 4001`.
All other business errors are returned as HTTP `200` + non-zero `code`; the frontend only needs to inspect the envelope.

---

## Health and metadata

### `GET /fcgi-bin/api/status`

Does not require the engine; used for liveness checks and frontend default values.

```json
{"code":0,"msg":"ok","data":{
  "name":"GA Sprite Birds","version":"2.0.0","status":"running",
  "defaults":{"voice":"zh-CN-YunjianNeural","rate":1.0,"enable_llm":false,
              "prosody_mode":"off","language":"zh_CN",
              "chapter_intro_outro":true,"chapter_lead_in_enabled":false}
}}
```

### `GET /fcgi-bin/api/engine`

Forwards the engine's `system.stats`: `max_concurrent / active_count / active_task_ids / tasks / schema_version / uptime_seconds`.
Returns `503` + `3004` when the engine is not running.

---

## Task creation and execution

### `POST /fcgi-bin/api/upload`

Query parameters: `path` (server-local path, mutually exclusive with `file`), `output_path` (output root).
Form field: `file` (multipart).
Header: `Idempotency-Key` (optional; passed through as `command_id` and the idempotency key).

```bash
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/upload" \
  -F "file=@book.txt" -H "Idempotency-Key: book-v1"
```

- The client filename is stripped of paths (`..\..\evil\a.txt` → `a.txt`) before being written to `API_UPLOAD_DIR/<uuid>_<name>`.
- Extension allowlist: `.txt` / `.md` / `.pdf`; anything else returns `code 1000`.
- Exceeding `API_MAX_UPLOAD_SIZE` (MB; 0 means unlimited) returns `code 1003`.
- On success returns the task view (`task_id`, `status`, `phase`, …).

### `POST /fcgi-bin/api/parse`

```json
{"task_id": "<id>", "command_id": "parse-1"}
```

The engine parses chapters in the background. On success the task reaches `phase=ready` and `total_chapters` is populated; on failure it becomes `phase=parse_failed`. The command returns immediately; clients poll `phase`.

> Parse uses the task's configuration snapshot (`LANGUAGE`). The optional `language` request field is reserved and currently ignored.

### `POST /fcgi-bin/api/generate`

```json
{
  "task_id": "<id>",
  "command_id": "gen-1",
  "chapter_indexes": [1, 2, 5],
  "voice": "zh-CN-YunjianNeural",
  "rate": 1.2,
  "prosody_mode": "prosody",
  "enable_llm": false,
  "chapter_intro_outro": true,
  "chapter_lead_in_enabled": false,
  "multi_voice": false,
  "character_template": "cache/role/novel_characters.json"
}
```

| Field | Constraint |
|------|------|
| `chapter_indexes` | Non-empty array of positive integers; omit to generate all chapters; unknown chapter numbers return `1001` (never queued) |
| `rate` | `0.5 ~ 2.0` |
| `prosody_mode` | `off` / `pause` / `prosody` |
| `voice` | Non-empty string (voice ShortName) |
| `enable_llm` / `multi_voice` | Boolean |
| `chapter_intro_outro` | Whether this run uses chapter intro/outro; omit to use the task snapshot (system config) |
| `chapter_lead_in_enabled` | Whether this run generates/uses a lead-in chapter; omit to use the task snapshot (system config) |
| `output_path` | Optional output root for this run |
| `character_template` | Path to the character voice template (used with `multi_voice`) |

Any out-of-range field is rejected at the model layer with `1001` and never enters the engine queue. `chapter_intro_outro` / `chapter_lead_in_enabled` apply to this run only and are **not written back to system config**.

---

## Task control

| Method | Path | Description | CLI equivalent |
|------|------|------|----------|
| `POST` | `/task/{id}/pause` | Pause after the current chapter | `pause <id>` |
| `POST` | `/task/{id}/resume` | Continue remaining chapters | `resume <id>` |
| `POST` | `/task/{id}/cancel` | Cancel the task | `cancel <id>` |
| `POST` | `/task/{id}/retry` | Re-queue a failed task (completed chapters are skipped) | `retry <id>` |
| `DELETE` | `/task/{id}?delete_outputs=false` | Remove the task record; artifacts are kept by default | `remove <id> [--delete-outputs]` |
| `DELETE` | `/task/{id}/chapter/{index}` | Cancel/remove a single chapter | `cancel-chapter <id> <index>` |

Control endpoints accept an optional body `{"command_id": "..."}` for idempotent retries.

---

## Queries

### `GET /task/{id}/status`

Returns the task view with `Cache-Control: no-store`.

```json
{"code":0,"msg":"ok","data":{
  "task_id":"...","type":"audiobook","status":"running","phase":"generating",
  "progress":0.42,"total_chapters":12,"completed_chapters":5,"attempts":1,
  "error":null,"created_at":"...","queued_at":"...","started_at":"...",
  "finished_at":null,"heartbeat_at":"...","control":{"pause_requested":false},
  "chapters":[{"index":1,"title":"Chapter 1","status":"succeeded",
               "audio_path":"...","error":null,"completed_at":"..."}]
}}
```

A missing task returns `code 3002` (HTTP 200); the frontend uses this to detect an invalidated task.

### `GET /task/{id}/events`

Parameters: `after_id` (cursor, default 0), `limit` (1~500, default 100).

```json
{"code":0,"msg":"ok","data":{"events":[
  {"event_id":12,"task_id":"...","type":"task.parsed",
   "created_at":"...","payload":{"total_chapters":2}}
]}}
```

Event types: `task.created / task.parsed / task.queued / task.started / task.progress /
task.paused / task.resumed / task.recovered / task.succeeded / task.failed / task.canceled /
task.removed`. Chapter-level progress is conveyed by the `task.progress` payload and the `chapters` array in `status`.

### `GET /tasks`

Parameters: `status`, `type`, `page` (≥1), `page_size` (1~100, default 20).
Returns `{list, total, page, page_size, has_more}`.

### `GET /task/{id}/chapter/{index}`

Serves chapter audio directly (`audio/mpeg`, etc.). Availability checks: chapter exists → has `audio_path` → file exists → non-empty, mapping to `3002 / 3002 / 3002 / 3003` respectively.

### `POST /tasks/cleanup`

```json
{"ttl_seconds": 86400, "dry_run": true, "delete_outputs": false}
```

Deletes **terminal** task records older than the TTL. `dry_run` only returns the `task_ids` that would be removed.
The engine also runs cleanup hourly (plus once at startup), removing terminal records older than `TASK_RESULT_TTL`.

---

## System config

| Method | Path | Description |
|------|------|------|
| `GET` | `/system-config` | Returns the schema in 7 sections (current value, default, overridden flag, range/enum/template metadata) |
| `PUT` | `/system-config` | Body `{"values": {"TTS_RATE": 1.15}}`; submit only changed keys |
| `POST` | `/system-config/reset` | `{"section": "tts"}` to reset one section, or `{"all": true}` to reset everything |
| `GET` | `/tts/voices` | Edge voice list (TTL-cached; returns cached data with a warning when offline) |
| `GET` | `/tts/preview` | Voice preview: `?voice=zh-CN-YunxiNeural[&text=...]`; success returns raw `audio/mpeg` (**no envelope**), failure still returns `{code,msg,data}`; results are cached by `voice+text` in `cache/tts/preview/` |

`/tts/preview` failure codes: `1000` voice ShortName not found, `4000` synthesis failed (network/edge-tts error).

Error responses (including the global 404) always carry `Cache-Control: no-store`. **Do not remove this header**: 404 is a status code browsers may cache heuristically, and once cached, a later existing route would replay the stale 404 for the same URL (the preview endpoint once returned 404 for a long time because of this). Frontend `fetch` also explicitly uses `cache: "no-store"` as a second safeguard.

The shape of one `GET /system-config` item:

```json
{
  "key": "TTS_RATE",
  "label_i18n": "config.item.TTS_RATE",
  "type": "float",
  "value": 1.0,
  "default": 1.0,
  "overridden": false,
  "ge": 0.5,
  "le": 2.0
}
```

Enum items additionally expose two i18n key prefixes (optional fields; absence means no translation for that part):

```json
{
  "key": "TTS_PROSODY_MODE",
  "label_i18n": "config.item.TTS_PROSODY_MODE",
  "type": "enum",
  "value": "off",
  "default": "off",
  "overridden": false,
  "options": ["off", "pause", "prosody"],
  "options_i18n": "config.option.TTS_PROSODY_MODE",
  "description_i18n": "config.desc.TTS_PROSODY_MODE"
}
```

- `options_i18n`: option labels come from `config.option.<KEY>.<value>`; option hints come from
  `config.option.<KEY>.<value>_hint` (e.g. `config.option.TTS_PROSODY_MODE.pause_hint`).
  When a translation is missing the frontend falls back to the raw value, never a blank option.
- `description_i18n`: field-level description shown under the control in the GUI, explaining the difference between similar options.

When adding an enum value you must add the copy under `config.option.<KEY>` in both
`ga_birds/Langues/{zh_CN,en_US}.json`;
`tests/unit/test_system_config.py::test_every_enum_option_has_translation_in_all_languages` catches missing translations. After editing, run `python scripts/sync_config_i18n.py` to sync to the GUI.

Validation failures return an error with `key` so the frontend can locate the field directly:

```json
{"code":1003,"msg":"config.error.out_of_range",
 "data":{"ge":0.5,"le":2.0,"gt":null,"lt":null,"key":"TTS_RATE"}}
```

Cross-field constraints: `LLM_MAX_TOKENS < LLM_NUM_CTX`, `DIALOGUE_CHUNK_OVERLAP < DIALOGUE_CHUNK_SIZE` (`code 1006`).
Changing `TTS_VOICE` validates against the Edge voice list; a voice outside the list returns `1005`. When offline it is allowed with a warning
(`config.warning.tts_voices_unavailable`).

---

## CLI / API parity

| Capability | API | CLI |
|------|-----|-----|
| Create task | `POST /upload` | `add -i file.txt` |
| Parse | `POST /parse` | performed internally by `add` |
| Generate | `POST /generate` | performed internally by `add` |
| List | `GET /tasks` | `list` |
| Details | `GET /task/{id}/status` | `get` / `status` |
| Events | `GET /task/{id}/events` | `events <id> [--follow]` / `logs` |
| Pause/resume/cancel/retry | `POST /task/{id}/…` | `pause` / `resume` / `cancel` / `retry` |
| Remove task | `DELETE /task/{id}` | `remove [--delete-outputs]` |
| Cancel one chapter | `DELETE /task/{id}/chapter/{n}` | `cancel-chapter` |
| Cleanup | `POST /tasks/cleanup` | `clean` |
| Read config | `GET /system-config` | `config get [KEY]` |
| Write config | `PUT /system-config` | `config set KEY value` |
| Engine status | `GET /engine` | `system info` / `system stats` |

**Declared differences**

1. **Character analysis** is **not exposed** by the v2 `add` flow: `--analyze-characters` exits with an error,
   and there is no HTTP endpoint for it. Prepare a character template yourself and use multi-voice generation.
2. **Multi-voice generation**: the API supports it through `multi_voice` + `character_template` (the template must exist); the GUI has no toggle.
3. **Manager-style operations** (`system doctor`, `engine status`) exist only on the CLI side; they read processes and the filesystem directly and do not go through the API — keeping the operational surface off HTTP.
4. **Chapter text download** has no HTTP endpoint; read the artifacts from the output directory.
