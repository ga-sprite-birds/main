# Control API 参考（v2）

> English version：[../en/api.md](../en/api.md)

所有业务接口挂在 `/fcgi-bin/api` 前缀下。Control API 由 `python -m server run` 启动（`server/` 包），FastAPI 应用在 `fcgi-bin/api.py`，只是薄控制面：
**不执行任务**，只做参数校验、命令转发、只读查询。

- 上传与命令转发 → Core 引擎（localhost HTTP + Bearer token）
- 状态/事件/列表/章节 → 只读 `data/tasks.db`（`PRAGMA query_only=ON`）
- 系统配置 → `ConfigService`（`data/system.db` 默认值 + `cache/config/system.json` 覆盖）

统一响应信封：

```json
{"code": 0, "msg": "ok", "data": {}}
```

| code 段 | 含义 |
|---------|------|
| `0` | 成功 |
| `1000~1999` | 参数/校验错误（缺参、类型、范围、枚举、正则、模板） |
| `2000~2999` | 鉴权 |
| `3000~3999` | 业务错误（任务不存在、状态非法、非法流转、幂等冲突） |
| `4000~4999` | 系统错误（内部异常、配置读写失败） |

特殊 HTTP 状态：引擎未运行 → `503` + `code 3004`；文档/Swagger 等未知路由 → `404` + `code 3002`；`data/tasks.db` 损坏或不可读 → HTTP `200` + `code 4001`。
其余业务错误都以 HTTP `200` + 非零 `code` 返回，前端只需判断信封。

---

## 健康与元信息

### `GET /fcgi-bin/api/status`

不需要引擎，用于探活与前端初始化默认值。

```json
{"code":0,"msg":"ok","data":{
  "name":"GA Sprite Birds","version":"2.0.0","status":"running",
  "defaults":{"voice":"zh-CN-YunjianNeural","rate":1.0,"enable_llm":false,
              "prosody_mode":"off","language":"zh_CN",
              "chapter_intro_outro":true,"chapter_lead_in_enabled":false}
}}
```

### `GET /fcgi-bin/api/engine`

转发引擎的 `system.stats`：`max_concurrent / active_count / active_task_ids / tasks / schema_version / uptime_seconds`。
引擎未运行时返回 `503` + `3004`。

---

## 任务创建与执行

### `POST /fcgi-bin/api/upload`

查询参数：`path`（服务器本地路径，与 `file` 二选一）、`output_path`（输出根目录）。
表单字段：`file`（multipart）。
请求头：`Idempotency-Key`（可选，透传为 `command_id` 与幂等键）。

```bash
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/upload" \
  -F "file=@book.txt" -H "Idempotency-Key: book-v1"
```

- 客户端文件名会被剥离路径（`..\..\evil\a.txt` → `a.txt`）后落盘到 `API_UPLOAD_DIR/<uuid>_<name>`。
- 扩展名白名单：`.txt` / `.md` / `.pdf`，否则 `code 1000`。
- 超过 `API_MAX_UPLOAD_SIZE`（MB，0 表示不限）返回 `code 1003`。
- 成功后返回任务视图（`task_id`、`status`、`phase` …）。

### `POST /fcgi-bin/api/parse`

```json
{"task_id": "<id>", "command_id": "parse-1"}
```

引擎在后台执行章节解析，成功后任务 `phase=ready`、`total_chapters` 就绪；失败为 `phase=parse_failed`。命令本身立即返回，客户端轮询 `phase`。

> 解析使用任务的配置快照（`LANGUAGE`）。可选的 `language` 请求字段目前保留但未生效。

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

| 字段 | 约束 |
|------|------|
| `chapter_indexes` | 非空正整数数组；省略表示全部章节；不存在的章节号返回 `1001`（不会进队列） |
| `rate` | `0.5 ~ 2.0` |
| `prosody_mode` | `off` / `pause` / `prosody` |
| `voice` | 非空字符串（音色 ShortName） |
| `enable_llm` / `multi_voice` | 布尔 |
| `chapter_intro_outro` | 本次生成是否启用章节片头片尾；省略时用任务快照（系统配置） |
| `chapter_lead_in_enabled` | 本次生成是否生成/使用导读篇；省略时用任务快照（系统配置） |
| `output_path` | 本次生成的输出根目录（可选） |
| `character_template` | 角色音色模板路径（配合 `multi_voice` 使用） |

任一字段越界在模型层直接返回 `1001`，不会进引擎队列。`chapter_intro_outro` / `chapter_lead_in_enabled` 只对本次生成生效，**不写回系统配置**。

---

## 任务控制

| 方法 | 路径 | 说明 | 对应 CLI |
|------|------|------|----------|
| `POST` | `/task/{id}/pause` | 当前章节后暂停 | `pause <id>` |
| `POST` | `/task/{id}/resume` | 继续剩余章节 | `resume <id>` |
| `POST` | `/task/{id}/cancel` | 取消任务 | `cancel <id>` |
| `POST` | `/task/{id}/retry` | 失败任务重新排队（已完成章节跳过） | `retry <id>` |
| `DELETE` | `/task/{id}?delete_outputs=false` | 删除任务记录；默认保留产物 | `remove <id> [--delete-outputs]` |
| `DELETE` | `/task/{id}/chapter/{index}` | 取消/移除单章 | `cancel-chapter <id> <index>` |

控制类接口都接受可选 body `{"command_id": "..."}` 用于幂等重试。

---

## 查询

### `GET /task/{id}/status`

返回任务视图，带 `Cache-Control: no-store`。

```json
{"code":0,"msg":"ok","data":{
  "task_id":"...","type":"audiobook","status":"running","phase":"generating",
  "progress":0.42,"total_chapters":12,"completed_chapters":5,"attempts":1,
  "error":null,"created_at":"...","queued_at":"...","started_at":"...",
  "finished_at":null,"heartbeat_at":"...","control":{"pause_requested":false},
  "chapters":[{"index":1,"title":"第一章","status":"succeeded",
               "audio_path":"...","error":null,"completed_at":"..."}]
}}
```

任务不存在返回 `code 3002`（HTTP 200）。前端据此判定任务失效。

### `GET /task/{id}/events`

参数：`after_id`（游标，默认 0）、`limit`（1~500，默认 100）。

```json
{"code":0,"msg":"ok","data":{"events":[
  {"event_id":12,"task_id":"...","type":"task.parsed",
   "created_at":"...","payload":{"total_chapters":2}}
]}}
```

事件类型：`task.created / task.parsed / task.queued / task.started / task.progress /
task.paused / task.resumed / task.recovered / task.succeeded / task.failed / task.canceled /
task.removed`。章节级进度通过 `task.progress` 的 payload 与 `status` 里的 `chapters` 反映。

### `GET /tasks`

参数：`status`、`type`、`page`（≥1）、`page_size`（1~100，默认 20）。
返回 `{list, total, page, page_size, has_more}`。

### `GET /task/{id}/chapter/{index}`

章节音频直出（`audio/mpeg` 等）。可用性判断：章节存在 → 有 `audio_path` → 文件存在 → 非空，
分别对应 `3002 / 3002 / 3002 / 3003`。

### `POST /tasks/cleanup`

```json
{"ttl_seconds": 86400, "dry_run": true, "delete_outputs": false}
```

删除超过 TTL 的**终态**任务记录。`dry_run` 只返回将被删的 `task_ids`。
引擎自身也会每小时执行一次清理（启动时先跑一次），删除超过 `TASK_RESULT_TTL` 的终态记录。

---

## 系统配置

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/system-config` | 返回 7 个分组的 schema（含当前值、默认值、是否覆盖、范围/枚举/模板元数据） |
| `PUT` | `/system-config` | body `{"values": {"TTS_RATE": 1.15}}`，只提交改动键 |
| `POST` | `/system-config/reset` | `{"section": "tts"}` 按组重置，或 `{"all": true}` 全部重置 |
| `GET` | `/tts/voices` | Edge 音色表（带 TTL 缓存；离线时返回缓存并附 warning） |
| `GET` | `/tts/preview` | 音色试听：`?voice=zh-CN-YunxiNeural[&text=...]`，成功返回 `audio/mpeg` 二进制（**不使用信封**），失败仍返回 `{code,msg,data}`；合成结果按 `voice+text` 缓存在 `cache/tts/preview/` |

`/tts/preview` 失败码：`1000` 音色 ShortName 不存在，`4000` 合成失败（网络/edge-tts 异常）。

错误响应（含全局 404）统一带 `Cache-Control: no-store`。**不要去掉这个头**：404 属于浏览器可
启发式缓存的状态码，一旦缓存，之后路由即使存在也会对同一个 URL 回放旧 404（试听接口曾因此
长时间报 404）。前端 fetch 也显式使用 `cache: "no-store"` 双保险。

`GET /system-config` 的单项形状：

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

枚举项额外下发两个 i18n key 前缀（可选字段，缺失表示该字段没有译文）：

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

- `options_i18n`：选项文案取 `config.option.<KEY>.<值>`；选项补充说明取
  `config.option.<KEY>.<值>_hint`（例如 `config.option.TTS_PROSODY_MODE.pause_hint`）。
  译文缺失时前端回退显示原始值，不会出现空白选项。
- `description_i18n`：字段级说明文案，GUI 显示在控件下方，用于解释近似选项的差别。

新增枚举值时必须同步在 `ga_birds/Langues/{zh_CN,en_US}.json` 的 `config.option.<KEY>` 下补文案，
`tests/unit/test_system_config.py::test_every_enum_option_has_translation_in_all_languages`
会拦住漏翻；改完执行 `python scripts/sync_config_i18n.py` 同步到 GUI。

校验失败返回带 `key` 的错误，前端可直接定位到字段：

```json
{"code":1003,"msg":"config.error.out_of_range",
 "data":{"ge":0.5,"le":2.0,"gt":null,"lt":null,"key":"TTS_RATE"}}
```

跨字段约束：`LLM_MAX_TOKENS < LLM_NUM_CTX`、`DIALOGUE_CHUNK_OVERLAP < DIALOGUE_CHUNK_SIZE`（`code 1006`）。
`TTS_VOICE` 变更会向 Edge 音色表校验，不在表内返回 `1005`；离线时放行并返回 warning
（`config.warning.tts_voices_unavailable`）。

---

## CLI 与 API 对等

| 能力 | API | CLI |
|------|-----|-----|
| 创建任务 | `POST /upload` | `add -i file.txt` |
| 解析 | `POST /parse` | `add` 内部自动执行 |
| 生成 | `POST /generate` | `add` 内部自动执行 |
| 列表 | `GET /tasks` | `list` |
| 详情 | `GET /task/{id}/status` | `get` / `status` |
| 事件 | `GET /task/{id}/events` | `events <id> [--follow]` / `logs` |
| 暂停/继续/取消/重试 | `POST /task/{id}/…` | `pause` / `resume` / `cancel` / `retry` |
| 删除任务 | `DELETE /task/{id}` | `remove [--delete-outputs]` |
| 取消单章 | `DELETE /task/{id}/chapter/{n}` | `cancel-chapter` |
| 清理 | `POST /tasks/cleanup` | `clean` |
| 读配置 | `GET /system-config` | `config get [KEY]` |
| 写配置 | `PUT /system-config` | `config set KEY value` |
| 引擎状态 | `GET /engine` | `system info` / `system stats` |

**差异声明**

1. **角色分析**在 v2 的 `add` 流程中**未暴露**：`--analyze-characters` 会直接报错，也没有对应的 HTTP 端点。
   请自行准备角色模板后使用多角色生成。
2. **多角色生成**：API 通过 `multi_voice` + `character_template` 支持（模板文件必须存在）；GUI 未提供开关。
3. **管理器类操作**（`system doctor`、`engine status`）只在 CLI 侧实现，直接读进程与文件系统，
   不经 API——避免把运维面暴露到 HTTP。
4. **章节文本下载**未提供 HTTP 端点，产物在输出目录直接读取。
