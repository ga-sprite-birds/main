# v2 Design: env Split / System Configuration

> 中文版：[../../zh/design/v2-system-config.md](../../zh/design/v2-system-config.md)
>
> Status: implemented (this document retains the design notes)
> Applies to: v2 absolute technical refactor
> Principle: implement against the new contract (`python.md` / `api.md`); no legacy compatibility
> Related document: `v2-headless-core.md` (task engine/persistence); the master contract is in `.augment/rules/imported/`

---

## 1. Requirements overview

Move "business configuration" out of `.env` into a **three-layer configuration system**:

1. **Deployment/secrets**: stays in `.env` (read by `pydantic-settings`), maintained by operations.
2. **Defaults**: `data/system.db` (SQLite) — seeded by code on first run.
3. **User overrides**: `cache/config/system.json` — records only the keys the user last changed (partial override).

- Effective value = **DB defaults ← system.json overrides**.
- The recommended edit path is the **API + GUI [System Config]**; `.env` no longer supports changing these business settings.
- Exception: `OUTPUT_BASE_PATH` (output directory) is business config managed by the API; all other `*_DIR` entries are deployment-level.

---

## 2. Architecture and directories

```text
project/
├── fcgi-bin/
│   ├── api.py                  # sole API entry point (no policy in this version)
│   └── cli.py                  # CLI entry point
├── routers/
│   ├── system_config.py        # /fcgi-bin/api/system-config
│   └── tts.py                  # /fcgi-bin/api/tts/voices
├── services/
│   └── config_service.py       # business config service
├── models/
│   └── config.py               # ConfigItem / ConfigSection / request-response models
├── system/
│   ├── config.py               # pydantic-settings: deployment/secrets only
│   ├── config_schema.py        # code-defined schema + seeded defaults
│   ├── response.py             # success()/fail() → {code,msg,data}
│   ├── db.py                   # SQLite connections (system.db / tasks.db)
│   └── deps.py                 # dependency injection
├── core_module/ (= ga_birds)   # business core, reads config_service
├── data/
│   └── system.db               # config defaults + system metadata
├── cache/
│   ├── config/system.json      # user overrides
│   ├── voices/edge_voices.json # edge voice list cache
│   ├── tts/preview/            # voice preview cache
│   └── models/                 # downloaded model cache
├── logs/  output/  ...
└── .env                        # deployment/secrets only
```

- **Entry point**: `python -m server run` (the `server/` package, loading the app from `fcgi-bin/api.py`) is the only entry point; this version has **no policy** and creates no `/fcgi-bin/policy/*`.
- **API security**: optional `API_AUTH_ENABLED` / `API_AUTH_TOKEN` (Bearer, X-API-Token, or GUI cookie); CORS is off by default. Non-loopback deployment requires auth.
- **Path safety**: local input paths are restricted to `API_UPLOAD_DIR` + `API_LOCAL_READ_ROOTS`; task output paths stay under `OUTPUT_BASE_PATH`; character templates stay under `CHARACTER_CACHE_DIR`.
- **Route prefix**: all under `/fcgi-bin/api/*`.
- **Response structure**: unified `{code, msg, data}`, `code=0` means success (see `api.md`).

---

## 3. Configuration layers

| Layer | Location | Contents | Who can change |
|---|---|---|---|
| Deployment/secrets | `.env` → `system/config.py` | See the appendix list | Operations |
| Defaults | `data/system.db` | `default` values from the schema below | System (seed/migration) |
| User overrides | `cache/config/system.json` | Only changed keys | API/GUI |

Priority: **API override value > DB default**; `.env` does not participate in business config.

---

## 4. Config item schema (code-defined, seeded into the DB)

Metadata: `key / section(menu) / type / default / options-or-range / validation`. Labels use i18n keys (Chinese/English).

### Multi-language
| key | type | default | options/range |
|---|---|---|---|
| LANGUAGE | enum | zh_CN | en_US / zh_CN / ja_JP |

### LLM
| key | type | default | validation |
|---|---|---|---|
| ENABLE_LLM | bool | false | |
| LLM_TEMPERATURE | float | 0.9 | 0.0–2.0 |
| LLM_MAX_TOKENS | int | 2048 | >0, and < LLM_NUM_CTX |
| LLM_NUM_CTX | int | 8192 | >0 |
| LLM_TIMEOUT | int | 600 | >0 seconds |

### TTS
| key | type | default | options/range |
|---|---|---|---|
| TTS_ENGINE | enum | edge | edge (the only engine for now) |
| TTS_VOICE | dynamic-select | zh-CN-YunjianNeural | validated against the edge voice list (see §6) |
| TTS_RATE | float | 1.0 | 0.5–2.0 |
| TTS_VOLUME | float | 1.0 | 0.0–2.0 |
| TTS_PITCH | int | 0 | -20–20 |
| TTS_CHUNK_MAX_CHARS | int | 2000 | >0 |
| TTS_CHUNK_TIMEOUT | int | 180 | >0 seconds |
| TTS_PROSODY_MODE | enum | off | off / pause / prosody (prosody/pause handling) |
| TTS_PROSODY_MAX_UNIT_CHARS | int | 120 | >0 (maximum characters per prosody unit) |

### Chapters
| key | type | default | validation |
|---|---|---|---|
| CHAPTER_INTRO_OUTRO | bool | true | |
| CHAPTER_LEAD_IN_ENABLED | bool | false | When no lead-in exists, the LLM generates one from the body length as chapter 0 (000) |
| CHAPTER_INTRO_TEMPLATE | string | 第{index}章开始 | Only {index}/{title} allowed |
| CHAPTER_OUTRO_TEMPLATE | string | 本章播讲完毕 | |
| CHAPTER_INTRO_OUTRO_PAUSE | float | 1.0 | ≥0 |
| CHAPTER_REGEX_PATTERNS | list[str] | see note below | Each item must compile with `re.compile` |
| CHAPTER_MIN_LENGTH | int | 10 | ≥0 |
| CHAPTER_KEEP_TITLE | bool | true | |
| CHAPTER_NORMALIZE_ENABLED | bool | true | |

> Note: with `CHAPTER_LEAD_IN_ENABLED` enabled, the generate stage uses an existing lead-in if the task already has one (matched via `OUTPUT_FRONT_MATTER_MARKERS`); otherwise the LLM generates a lead-in based on body length (about `body length/300`, 80–500 characters) as chapter 0. If the LLM is unavailable, the lead-in is skipped and generation continues. This switch, together with `CHAPTER_INTRO_OUTRO`, can be overridden per run from the "Audio Generation" panel; the override affects only that run.

> Note: `CHAPTER_REGEX_PATTERNS` defaults to two entries stored as **raw strings** so JSON does not corrupt `\u4e00`:
> `^第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节](?![\u4e00-\u9fff])`
> `^#+\s*第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节](?![\u4e00-\u9fff])`

### Output
| key | type | default | options/range |
|---|---|---|---|
| OUTPUT_BASE_PATH | string | ./output | path |
| OUTPUT_STRATEGY | enum | by_role | by_role / by_model / by_date |
| OUTPUT_FORMAT | enum | mp3 | mp3 / m4a / wav |
| OUTPUT_BITRATE | int | 192 | 128 / 192 / 320 recommended |
| OUTPUT_FILENAME_TEMPLATE | string | {index:03d}-{title}.{format} | Only {index}/{title}/{role}/{date}/{format} allowed; no `/`, `\` or `..` |
| OUTPUT_FRONT_MATTER_MARKERS | list[str] | ["导读","前言"] | Front-matter markers (used to skip non-body content) |
| OUTPUT_KEEP_TEMP_FILES | bool | false | |
| OUTPUT_DUPLICATE_HANDLING | enum | rename | overwrite / rename / skip |
| OUTPUT_SAVE_CHAPTER_TEXT | bool | true | |
| OUTPUT_CHAPTER_TEXT_ENCODING | string | utf-8 | utf-8 / gbk recommended |

### Text preprocessing
| key | type | default |
|---|---|---|
| TEXT_PREPROCESSING_ENABLED | bool | true |

### Character analysis
| key | type | default | options/range |
|---|---|---|---|
| ENABLE_MULTI_VOICE | bool | true | |
| CHARACTER_ANALYSIS_MODE | enum | auto | auto / hybrid |
| CHARACTER_MAX_CONTENT_LENGTH | int | 3000 | >0 |
| DIALOGUE_CHUNK_SIZE | int | 3000 | >0 |
| DIALOGUE_CHUNK_OVERLAP | int | 200 | ≥0, and < DIALOGUE_CHUNK_SIZE |
| SEGMENT_ENABLE_LANGUAGE_ANALYSIS | bool | true | Segment-level language analysis switch |
| SEGMENT_ENABLE_EMOTION_ANALYSIS | bool | true | Segment-level emotion analysis switch |
| SEGMENT_MAX_RATE_DELTA | float | 0.25 | ≥0 (maximum segment rate adjustment) |
| SEGMENT_MAX_PITCH_DELTA | int | 8 | ≥0 (maximum segment pitch adjustment) |
| SEGMENT_MAX_VOLUME_DELTA | float | 0.15 | ≥0 (maximum segment volume adjustment) |
| VOICE_PREFER_REGION_MATCH | bool | true | Prefer voices matching the region/language |

> Note: `TTS_PROSODY_*`, `OUTPUT_FRONT_MATTER_MARKERS`, `SEGMENT_*`, and `VOICE_PREFER_REGION_MATCH` are enhancements added during v2 development (prosody, front-matter skipping, segment emotion/language analysis, region voice matching). They are managed and validated uniformly through system config.

---

## 5. Data layer design

### 5.1 `data/system.db` (SQLite)
```sql
CREATE TABLE config_defaults (
  key         TEXT PRIMARY KEY,
  value_json  TEXT NOT NULL,      -- JSON-encoded to preserve type (bool/int/float/str/list)
  updated_at  TEXT NOT NULL
);

CREATE TABLE schema_meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  config_schema_version INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
```
- On first startup, perform an **idempotent seed** from `config_schema.py` (fill in anything missing).
- Migration strategy for this round: **add missing keys only**; never overwrite existing keys.

### 5.2 `cache/config/system.json` (partial overrides)
```json
{ "LANGUAGE": "en_US", "TTS_VOICE": "zh-CN-XiaoxiaoNeural" }
```
- Stores only keys the user changed; section membership comes from the schema and is used for "reset by menu".

### 5.3 `data/tasks.db`
- Connections are provided uniformly by `system/db.py` (read-write for the engine, read-only for the API).
- Table structure and task persistence details are in **`v2-headless-core.md` §4** (the two requirements ship together).

---

## 6. TTS voice validation

- Source: `edge_tts.list_voices()` (network call).
- Cache: `cache/voices/edge_voices.json` (with TTL) to avoid going online on every validation.
- Validation: on `PUT`, check that `TTS_VOICE` ∈ cached `ShortName` list.
- Read-only endpoint: `GET /fcgi-bin/api/tts/voices` (supports filtering by locale / gender) for the GUI dropdown.
- **Offline policy**: when there is no cache and fetching fails — **allow the change + return a warning** (do not block configuration).

---

## 7. API contract (unified `{code,msg,data}`)

### GET `/fcgi-bin/api/system-config`
Returns config grouped by menu:
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "sections": [
      {
        "section_key": "tts",
        "title_i18n": "config.section.tts",
        "items": [
          {
            "key": "TTS_VOICE",
            "label_i18n": "config.item.TTS_VOICE",
            "type": "dynamic-select",
            "value": "zh-CN-YunjianNeural",
            "default": "zh-CN-YunjianNeural",
            "overridden": false,
            "options_source": "edge_voices"
          }
        ]
      }
    ]
  }
}
```

### PUT `/fcgi-bin/api/system-config`
```json
{ "values": { "TTS_VOICE": "zh-CN-XiaoxiaoNeural", "CHAPTER_MIN_LENGTH": 10 } }
```
- Partial update: write only the changed keys to `system.json`.
- Validate each item against the schema; failures return business error codes (parameter range 1000~1999).
- On success return the latest effective values; may include a warning (e.g. voice allowed while offline).

### POST `/fcgi-bin/api/system-config/reset`
```json
{ "section": "tts" }      // reset one menu
{ "all": true }           // reset everything
```

### GET `/fcgi-bin/api/tts/voices`
- Query: `locale`, `gender` (optional)
- Returns the edge voice list (ShortName / Locale / Gender / FriendlyName, etc.).

---

## 8. ConfigService layer

- Startup: `schema → seed system.db → load defaults (DB) → load overrides (json) → merge into memory`.
- `get(key)` / `get_all()` / `get_schema()` (sections, labels, types, current values, defaults, overridden flags).
- `set(values)`: validate against the schema → write only changed keys to `system.json` → hot-update memory.
- `reset(section)` / `reset_all()`: remove the corresponding keys from `system.json` → merge again.
- Concurrency: single process + in-memory lock.
- Business code reads through the `config` facade (it resolves the task snapshot, then ConfigService); deployment items use `settings`. Do not cache config at import time.
- The same `ConfigService` is shared by the **API (read/write: serve/edit config)** and the **engine (reads effective config at the start of each task)**.

---

## 9. Internal refactor points

1. Remove all business config items from `.env` / `.env.example`; keep only deployment/secrets (see appendix).
2. `system/config.py` defines only deployment items via `pydantic-settings`.
3. In `ga_birds` modules, read business values through the `config` facade (task snapshot → ConfigService); read `*_DIR` etc. from `settings`. Do not capture values at import time.
4. Retire the env-reading logic for business items in `config/__init__.py` (deployment fields delegate to `settings`).
5. Route all API output through `system/response.py` for the unified envelope.

---

## 10. GUI "System Config" page

- Add a **【System Config】** entry on the left, generating sub-items from `menu`: i18n / LLM / TTS / Chapters / Output / Text Preprocessing / Character Analysis.
- Render forms by type: bool→switch, enum→dropdown, dynamic-select→remote dropdown (TTS voices), int/float→number (min/max), string→input, regex/template→multiline text, list→tags/multiline.
- Each item shows: current value, default value, overridden flag (badge).
- Actions: save (PUT changed keys), reset by menu, reset everything.
- Copy goes through i18n (Chinese/English).

---

## 11. Implementation steps

1. Scaffold `system/ services/ routers/ models/ data/` + `system/response.py`.
2. `config_schema.py` (schema + seeded defaults).
3. `system/db.py` + seed `system.db`.
4. `ConfigService` + `system.json`.
5. `routers/system_config.py`, `routers/tts.py` + mount into `api.py`.
6. Refactor how `ga_birds` reads config.
7. Slim `.env/.env.example` + update docs.
8. GUI system config page.
9. Unit tests (validation / override / reset / hot reload / voice validation).

---

## 12. Acceptance checklist

- No business config items remain in `.env`; `.env.example` is in sync.
- After first startup, `data/system.db` contains all config defaults (missing keys are filled in).
- `GET /fcgi-bin/api/system-config` returns menu-grouped data with defaults / current values / override flags.
- `PUT` writes only changed keys to `cache/config/system.json`; illegal values are rejected (business error codes).
- After reset-by-menu / reset-all, effective values return to `system.db` defaults.
- `TTS_VOICE` is validated against the voice list; when offline (no cache and fetch fails) it is allowed with a warning.
- `GET /fcgi-bin/api/tts/voices` returns the list and filters by locale / gender.
- All `ga_birds` business reads come from `ConfigService`, never env business items.
- All API output is `{code, msg, data}`.
- The GUI 【System Config】 renders by section, supports save/reset, and states "applies only to new tasks".

---

## Appendix: `.env` keep-list (deployment/secrets)

- LLM: `LLM_MODE`, `LLM_API_ENDPOINT / KEY / MODEL`, `LLM_LOCAL_HOST / MODEL`, `LLM_SYSTEM_PROMPT`
- API: `API_HOST / PORT / DEBUG / UPLOAD_DIR / MAX_UPLOAD_SIZE / MAX_JSON_BODY_SIZE / LOCAL_READ_ROOTS`
- API security: `API_AUTH_ENABLED / API_AUTH_TOKEN / CORS_ENABLED / CORS_ORIGINS`, `API_BIND_HOST` (compose only)
- Tasks: `TASK_MAX_CONCURRENT / GRACE_SECONDS / RESULT_TTL / CACHE_DIR`
- Paths/dependencies: `FFMPEG_PATH`, `CORE_DIR`, `DATA_DIR`, `CACHE_DIR`, `RUN_DIR`, `MODEL_CACHE_DIR`, `CHARACTER_CACHE_DIR`, `TTS_VOICE_CATALOG_CACHE`
- Logging: `LOG_LEVEL / FORMAT / FILE / MAX_FILE_SIZE / BACKUP_COUNT / CONSOLE`

> Note: `OUTPUT_BASE_PATH` (output directory) is business config managed by the API and is not in this list.
