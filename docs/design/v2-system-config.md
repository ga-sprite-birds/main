# v2 设计：env 拆分 / 系统配置

> 状态：需求已定稿，待开发（本文只做设计，不含实现）
> 适用版本：v2 绝对技术重构
> 原则：按新契约（`python.md` / `api.md`）实现，不做旧版兼容
> 关联文档：`v2-headless-core.md`（任务引擎/持久化）；契约总纲见 `.augment/rules/imported/`

---

## 1. 需求概述

把「业务配置」从 `.env` 剥离，改为**三层配置体系**：

1. **部署级/密钥**：留在 `.env`（`pydantic-settings` 读取），运维维护。
2. **默认值**：`data/system.db`（SQLite）——由代码种子首次灌入。
3. **用户覆盖**：`cache/config/system.json`——只记录用户最后一次修改的键（部分覆盖）。

- 生效值 = **DB 默认值 ← system.json 覆盖**。
- 修改入口推荐走 **API + GUI【系统配置】**；`.env` 不再支持修改这些业务配置。
- 例外：`OUTPUT_BASE_PATH`（输出目录）属于业务配置，归 API 管；其余 `*_DIR` 归部署级。

---

## 2. 架构与目录

```text
project/
├── fcgi-bin/
│   ├── api.py                  # 唯一 API 入口（本版无 policy）
│   └── cli.py                  # CLI 入口
├── routers/
│   ├── system_config.py        # /fcgi-bin/api/system-config
│   └── tts.py                  # /fcgi-bin/api/tts/voices
├── services/
│   └── config_service.py       # 业务配置服务
├── models/
│   └── config.py               # ConfigItem / ConfigSection / 请求响应模型
├── system/
│   ├── config.py               # pydantic-settings：仅部署级/密钥
│   ├── config_schema.py        # 代码定义的 schema + 种子默认值
│   ├── response.py             # success()/fail() → {code,msg,data}
│   ├── db.py                   # SQLite 连接（system.db / tasks.db）
│   └── deps.py                 # 依赖注入
├── core_module/ (= ga_birds)   # 业务核心，读取 config_service
├── data/
│   └── system.db               # 配置默认值 + 系统元数据
├── cache/
│   ├── config/system.json      # 用户覆盖
│   └── tts/voices.json         # edge 音色表缓存
├── logs/  output/  ...
└── .env                        # 仅部署级/密钥
```

- **入口**：`fcgi-bin/api.py` 唯一入口，所有 API 走它；本版**没有 policy**，不建 `/fcgi-bin/policy/*`。
- **路由前缀**：统一 `/fcgi-bin/api/*`。
- **响应结构**：统一 `{code, msg, data}`，`code=0` 成功（见 `api.md`）。

---

## 3. 配置分层

| 层 | 位置 | 内容 | 谁能改 |
|---|---|---|---|
| 部署/密钥 | `.env` → `system/config.py` | 见附录保留清单 | 运维 |
| 默认值 | `data/system.db` | 下方 schema 的 default | 系统（seed/迁移） |
| 用户覆盖 | `cache/config/system.json` | 仅改过的键 | API/GUI |

优先级：**API 覆盖值 > DB 默认值**；`.env` 不参与业务配置。

---

## 4. 配置项 schema（代码定义，灌库种子）

元数据：`key / 分组(菜单) / 类型 / 默认 / 可选或范围 / 校验`。label 用 i18n key（中英）。

### 多语言配置
| key | 类型 | 默认 | 可选/范围 |
|---|---|---|---|
| LANGUAGE | enum | zh_CN | en_US / zh_CN / ja_JP |

### LLM 配置
| key | 类型 | 默认 | 校验 |
|---|---|---|---|
| ENABLE_LLM | bool | false | |
| LLM_TEMPERATURE | float | 0.9 | 0.0–2.0 |
| LLM_MAX_TOKENS | int | 2048 | >0，且 < LLM_NUM_CTX |
| LLM_NUM_CTX | int | 8192 | >0 |
| LLM_TIMEOUT | int | 600 | >0 秒 |

### TTS 配置
| key | 类型 | 默认 | 可选/范围 |
|---|---|---|---|
| TTS_ENGINE | enum | edge | edge（当前仅此） |
| TTS_VOICE | dynamic-select | zh-CN-YunjianNeural | 校验 edge 音色表（见 §6） |
| TTS_RATE | float | 1.0 | 0.5–2.0 |
| TTS_VOLUME | float | 1.0 | 0.0–2.0 |
| TTS_PITCH | int | 0 | -20–20 |
| TTS_CHUNK_MAX_CHARS | int | 2000 | >0 |
| TTS_CHUNK_TIMEOUT | int | 180 | >0 秒 |
| TTS_PROSODY_MODE | enum | off | off / pause / prosody（韵律/停顿处理） |
| TTS_PROSODY_MAX_UNIT_CHARS | int | 120 | >0（韵律分片最大字符数） |

### 章节配置
| key | 类型 | 默认 | 校验 |
|---|---|---|---|
| CHAPTER_INTRO_OUTRO | bool | true | |
| CHAPTER_INTRO_TEMPLATE | string | 第{index}章开始 | 仅允许 {index}/{title} |
| CHAPTER_OUTRO_TEMPLATE | string | 本章播讲完毕 | |
| CHAPTER_INTRO_OUTRO_PAUSE | float | 1.0 | ≥0 |
| CHAPTER_REGEX_PATTERNS | list[str] | 见下注 | 每项须能 `re.compile` |
| CHAPTER_MIN_LENGTH | int | 10 | ≥0 |
| CHAPTER_KEEP_TITLE | bool | true | |
| CHAPTER_NORMALIZE_ENABLED | bool | true | |

> 注：`CHAPTER_REGEX_PATTERNS` 默认两条，按**原始字符串**存储，避免 JSON 破坏 `\u4e00`：
> `^第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节](?![\u4e00-\u9fff])`
> `^#+\s*第\s*[零一二三四五六七八九十百千万0-9]+\s*[章回卷节](?![\u4e00-\u9fff])`

### 输出配置
| key | 类型 | 默认 | 可选/范围 |
|---|---|---|---|
| OUTPUT_BASE_PATH | string | ./output | 路径 |
| OUTPUT_STRATEGY | enum | by_role | by_role / by_model / by_date |
| OUTPUT_FORMAT | enum | mp3 | mp3 / m4a / wav |
| OUTPUT_BITRATE | int | 192 | 建议 128 / 192 / 320 |
| OUTPUT_FILENAME_TEMPLATE | string | {index:03d}-{title}.{format} | 仅允许 {index}/{title}/{role}/{date}/{format} |
| OUTPUT_FRONT_MATTER_MARKERS | list[str] | ["导读","前言"] | 前置内容识别标记（用于跳过非正文） |
| OUTPUT_KEEP_TEMP_FILES | bool | false | |
| OUTPUT_DUPLICATE_HANDLING | enum | rename | overwrite / rename / skip |
| OUTPUT_SAVE_CHAPTER_TEXT | bool | true | |
| OUTPUT_CHAPTER_TEXT_ENCODING | string | utf-8 | 建议 utf-8 / gbk |

### 文本预处理配置
| key | 类型 | 默认 |
|---|---|---|
| TEXT_PREPROCESSING_ENABLED | bool | true |

### 角色分析配置
| key | 类型 | 默认 | 可选/范围 |
|---|---|---|---|
| ENABLE_MULTI_VOICE | bool | true | |
| CHARACTER_ANALYSIS_MODE | enum | auto | auto / hybrid |
| CHARACTER_MAX_CONTENT_LENGTH | int | 3000 | >0 |
| DIALOGUE_CHUNK_SIZE | int | 3000 | >0 |
| DIALOGUE_CHUNK_OVERLAP | int | 200 | ≥0，且 < DIALOGUE_CHUNK_SIZE |
| SEGMENT_ENABLE_LANGUAGE_ANALYSIS | bool | true | 分段语言分析开关 |
| SEGMENT_ENABLE_EMOTION_ANALYSIS | bool | true | 分段情绪分析开关 |
| SEGMENT_MAX_RATE_DELTA | float | 0.25 | ≥0（段落语速微调上限） |
| SEGMENT_MAX_PITCH_DELTA | int | 8 | ≥0（段落音调微调上限） |
| SEGMENT_MAX_VOLUME_DELTA | float | 0.15 | ≥0（段落音量微调上限） |
| VOICE_PREFER_REGION_MATCH | bool | true | 音色优先匹配地区/语言 |

> 说明：`TTS_PROSODY_*`、`OUTPUT_FRONT_MATTER_MARKERS`、`SEGMENT_*`、`VOICE_PREFER_REGION_MATCH` 为 v2 开发期新增的增强功能配置（韵律、前置内容跳过、分段情绪/语言分析、地区音色匹配），已纳入系统配置统一管理与校验。

---

## 5. 数据层设计

### 5.1 `data/system.db`（SQLite）
```sql
CREATE TABLE config_defaults (
  key         TEXT PRIMARY KEY,
  value_json  TEXT NOT NULL,      -- JSON 编码，保类型（bool/int/float/str/list）
  updated_at  TEXT NOT NULL
);

CREATE TABLE schema_meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  config_schema_version INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
```
- 首次启动按 `config_schema.py` **幂等 seed**（缺哪个补哪个）。
- 本轮迁移策略：**只补缺失键**，已有键不覆盖。

### 5.2 `cache/config/system.json`（部分覆盖）
```json
{ "LANGUAGE": "en_US", "TTS_VOICE": "zh-CN-XiaoxiaoNeural" }
```
- 只存用户改过的键；分组成员关系来自 schema，用于"按菜单重置"。

### 5.3 `data/tasks.db`
- 由 `system/db.py` 统一提供连接端口（读写交给 engine，API 只读）。
- 表结构与任务持久化细节见 **`v2-headless-core.md` §4**（两个需求一起落地）。

---

## 6. TTS 音色校验

- 来源：`edge_tts.list_voices()`（网络调用）。
- 缓存：`cache/tts/voices.json`（带 TTL），避免每次校验联网。
- 校验：`PUT` 时校验 `TTS_VOICE` ∈ 缓存 `ShortName` 列表。
- 只读接口：`GET /fcgi-bin/api/tts/voices`（支持按 locale / gender 过滤），供 GUI 下拉。
- **离线策略**：无缓存且 fetch 失败时——**放行 + 返回 warning**（不阻塞配置）。

---

## 7. 接口契约（统一 `{code,msg,data}`）

### GET `/fcgi-bin/api/system-config`
返回按菜单分组的配置：
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
- 部分更新：仅把改动键写入 `system.json`。
- 逐项按 schema 校验；失败返回业务错误码（参数类 1000~1999）。
- 成功返回最新生效值；可附带 warning（如音色离线放行）。

### POST `/fcgi-bin/api/system-config/reset`
```json
{ "section": "tts" }      // 按菜单重置
{ "all": true }           // 一键全部重置
```

### GET `/fcgi-bin/api/tts/voices`
- Query：`locale`、`gender`（可选）
- 返回 edge 音色列表（ShortName / Locale / Gender / FriendlyName 等）。

---

## 8. 服务层 ConfigService

- 启动：`schema → seed system.db → load defaults(DB) → load overrides(json) → 合并进内存`。
- `get(key)` / `get_all()` / `get_schema()`（含分组、label、类型、当前值、默认值、是否覆盖）。
- `set(values)`：按 schema 校验 → 仅改动键写 `system.json` → 热更新内存。
- `reset(section)` / `reset_all()`：从 `system.json` 删对应键 → 重新合并。
- 并发：单进程 + 内存锁。
- 业务代码不再 `import config`；业务项走 `config_service.get(...)`，部署项走 `settings`。
- 同一个 `ConfigService` 由 **API（读写：提供/编辑配置）** 与 **engine（每个任务开始时读取生效配置）** 共用。

---

## 9. 内部改造点

1. `.env` / `.env.example` 删除所有业务配置项，仅留部署/密钥（见附录）。
2. `system/config.py` 用 `pydantic-settings` 只定义部署项。
3. `ga_birds` 各模块：`config.TTS_*` / `CHAPTER_*` / `OUTPUT_*` / `ENABLE_*` 等改为 `config_service.get(...)`；`*_DIR` 等改读 `settings`。
4. 废弃 `config/__init__.py` 的 env 读取逻辑。
5. 所有 API 输出改走 `system/response.py` 统一信封。

---

## 10. GUI「系统配置」页

- 左侧新增 **【系统配置】**，按 `menu` 生成子项：多语言 / LLM / TTS / 章节 / 输出 / 文本预处理 / 角色分析。
- 表单按类型渲染：bool→开关，enum→下拉，dynamic-select→远程下拉(TTS 音色)，int/float→数字(min/max)，string→输入框，正则/模板→多行文本，list→标签/多行。
- 每项显示：当前值、默认值、是否被覆盖（徽标）。
- 操作：保存（PUT 改动键）、按菜单重置、一键全部重置。
- 文案走 i18n（中英）。

---

## 11. 实施步骤

1. 搭 `system/ services/ routers/ models/ data/` 骨架 + `system/response.py`
2. `config_schema.py`（schema + 种子默认值）
3. `system/db.py` + seed `system.db`
4. `ConfigService` + `system.json`
5. `routers/system_config.py`、`routers/tts.py` + 挂载到 `api.py`
6. 改造 `ga_birds` 读取方式
7. 瘦身 `.env/.env.example` + 更新文档
8. GUI 系统配置页
9. 单测（校验 / 覆盖 / 重置 / 热更新 / 音色校验）

---

## 12. 验收清单

- `.env` 中不再存在业务配置项；`.env.example` 同步。
- 首次启动后 `data/system.db` 含全部配置默认值（缺键补齐）。
- `GET /fcgi-bin/api/system-config` 返回按菜单分组，含默认值 / 当前值 / 覆盖标记。
- `PUT` 仅把改动键写入 `cache/config/system.json`；非法值被拒绝（业务错误码）。
- 按菜单重置 / 全部重置后，生效值回到 `system.db` 默认。
- `TTS_VOICE` 走音色表校验；离线（无缓存且 fetch 失败）放行并返回 warning。
- `GET /fcgi-bin/api/tts/voices` 可返回并按 locale / gender 过滤。
- `ga_birds` 业务读取均来自 `ConfigService`，不再读 env 业务项。
- 全部 API 输出为 `{code, msg, data}`。
- GUI【系统配置】按分组渲染，可保存/重置，并提示"仅对新任务生效"。

---

## 附录：`.env` 保留清单（部署级/密钥）

`LLM_MODE`、`LLM_API_TYPE / ENDPOINT / KEY / MODEL`、`LLM_LOCAL_HOST / MODEL`、`LLM_SYSTEM_PROMPT`、
`API_HOST / PORT / DEBUG / CORS_*`、`TASK_*`、`REDIS_*`、`FFMPEG_PATH`、`CORE_DIR`、
`MODEL_CACHE_DIR`、`CHARACTER_CACHE_DIR`、`API_UPLOAD_DIR`、`LOG_*`。

> 注意：`OUTPUT_BASE_PATH`（输出目录）属业务配置，归 API 管，不在此清单。
