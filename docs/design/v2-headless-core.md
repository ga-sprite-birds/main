# v2 设计：彻底分离任务与 API 表现层（Headless Core）

> 状态：需求已定稿，待开发（本文只做设计，不含实现）
> 适用版本：v2 绝对技术重构
> 依据契约：`task-system.md`（Core/Control API 分离、状态机、事件、恢复、单实例、优雅退出、运行时发现）、`api.md`（响应结构、双入口→本版仅 `/fcgi-bin/api/*`）、`python.md`（分层）
> 核心目标：**引擎（Core）独立常驻，API 只是控制面；杀掉 API 任务照跑；Core 由系统层（systemd）或手动维护。**
> 关联文档：`v2-system-config.md`（配置体系 / ConfigService）；契约总纲见 `.augment/rules/imported/`

---

## 1. 需求概述

- 将「任务执行引擎」与「API 表现层」在**进程级**彻底分离。
- Core 唯一执行任务、唯一写任务状态；API 只发命令 + 只读查询。
- 关闭 FastAPI 不影响正在执行的任务；Core 可 systemd 常驻或手动临时启动。
- `fcgi-bin/` 只保留 API 入口，不放 Core。
- CLI 与 API 对等，均作为 Core 的客户端，不再内联执行任务。

---

## 2. 进程模型与职责

```text
           命令(本地 HTTP)                     只读查询
GUI / CLI ───────────────► Control API(api.py) ─────────┐
                                 │ 命令转发              │ 只读打开
                                 ▼                      ▼
                         Command Channel           tasks.db(SQLite WAL)
                                 │                      ▲ 唯一写
                                 ▼                      │
                         Core 引擎(engine/, 常驻) ───────┘
                          ├─ Scheduler(并发/暂停/取消/重试)
                          ├─ Handlers(parse/generate/merge/export) → ga_birds
                          ├─ TaskStore(tasks.db)
                          ├─ 单实例锁 + 运行时发现文件
                          └─ 恢复 / 优雅退出
```

| 角色 | 职责 | 不做什么 |
|---|---|---|
| Core（engine） | 执行任务、调度、恢复、**唯一写 tasks.db**、本地命令服务 | 不依赖 API/GUI 存活 |
| Control API（api.py） | 收命令、转发给 Core、**只读**查询 tasks.db、托管 GUI | 不执行长任务、不写任务状态、不 import Audio/LLM/Parser |
| Command Channel | localhost HTTP（127.0.0.1）+ token | 不承载业务规则 |
| Client（CLI/GUI） | 发命令、展示状态 | 不直接读写任务存储 |

---

## 3. 命令通道（跨平台）

- **传输**：localhost HTTP，`127.0.0.1:<port>`（避开 UDS 的 Windows 兼容问题）。
- **鉴权**：Core 启动时生成随机 `token`，写入运行时发现文件；API/CLI 以 `Authorization: Bearer <token>` 调用。
- **运行时发现文件**：`run/engine.json`（权限 0600），字段：
  ```json
  { "app":"ga-sprite-birds", "pid":12345, "host":"127.0.0.1", "port":39211,
    "protocol_version":1, "token":"...", "started_at":"..." }
  ```
  不放敏感以外的东西；「token」虽敏感但仅本机可见，文件权限收紧。
- **协议**：JSON。
  - `POST /command`：`{ "command_id":"uuid", "command":"task.add", "payload":{...} }`
  - `GET /system/info`、`GET /system/stats`
- **幂等**：`command_id` 去重，重复提交返回同一结果（见 §4 `command_log`）。
- **命令集**（按 `task-system.md` §4.1）：`task.add / pause / resume / cancel / retry / remove / update_options`、`config.get/set`、`system.info / system.stats`。
- **查询不进命令通道**：状态/历史由 API **只读** `tasks.db`（满足"Core 停机仍可查历史"）。

---

## 4. tasks.db（SQLite WAL，Core 单写 / API 只读）

> 路径：`data/tasks.db`。Core 使用读写连接（WAL）；API 使用只读连接（`?mode=ro` 或 `PRAGMA query_only=1`）。

### 4.1 tasks
| 字段 | 说明 |
|---|---|
| task_id TEXT PK | 任务 ID（全局唯一，不复用） |
| type TEXT | 任务类型（如 audiobook）|
| status TEXT | pending/queued/running/paused/succeeded/failed/canceled/removed |
| phase TEXT | 子阶段（parsing/generating，供 UI；非契约必填） |
| params_json TEXT | 任务参数快照（voice/rate/chapters/enable_llm/output_path/prosody…）|
| result_json TEXT | 结果 |
| error TEXT | 错误信息 |
| total_chapters INT | 总章节 |
| completed_chapters INT | 已完成章节 |
| attempts INT | 尝试次数 |
| heartbeat_at / queued_at / started_at / finished_at | 时间戳 |
| created_at / updated_at | 必备 |
| idempotency_key TEXT | 幂等键 |

### 4.2 task_chapters
| 字段 | 说明 |
|---|---|
| task_id, chapter_index | 复合主键 |
| title / status / audio_path / error | 章节进度 |
| attempts INT | |
| started_at / finished_at | |

### 4.3 task_events
| 字段 | 说明 |
|---|---|
| event_id INTEGER PK AUTOINCREMENT | 单调递增，客户端游标恢复 |
| task_id / type / payload_json / created_at | 事件 |

### 4.4 command_log（幂等）
| 字段 | 说明 |
|---|---|
| command_id TEXT PK | 幂等 |
| command / payload_hash / status / result_json / created_at | |

### 4.5 schema_meta
- `id=1, tasks_schema_version, updated_at`：迁移版本。

> 连接模型：`TaskStore` 为每个线程建立**独立 SQLite 连接**（命令 HTTP 线程与 asyncio 调度线程互不共享），请求结束后由 `close_thread_connection()` 回收；`engine doctor/status` 以只读连接访问，UI 迁移只由 Core 在启动时执行。

> 迁移：迁移脚本版本化、可回滚（遵循 `sql.md`）。

---

## 5. 状态机与事件

- 状态与迁移严格按 `task-system.md` §5：
  ```text
  pending -> queued -> running -> succeeded / failed / canceled
  running -> paused -> queued
  failed  -> queued (retry)
  any     -> removed (tombstone)
  ```
- 非法迁移拒绝并返回错误码。
- `cancel`（停止任务）≠ `remove`（移除记录），语义不混用。
- 事件（§4.2）：`task.created/started/progress/paused/resumed/succeeded/failed/canceled/removed/log`，单调 `event_id`。
- **本轮先轮询**（`GET status` 读 tasks.db）；`task_events` 已持久化，SSE 作为后续增强。

---

## 6. Core / engine 设计

- **入口**：`python -m engine run`（`engine/__main__.py`）；`engine status` 查看。
- **Scheduler**：按 `TASK_MAX_CONCURRENT` 调度 `queued → running`；提供 pause/cancel/retry。
- **Handlers**：`parse / generate / merge / export`，调用 `ga_birds` 业务；章节级循环，每章完成写 checkpoint + 事件。
- **parse 为后台任务**：`task.parse` 命令只把任务入队并立即返回（`phase=parsing`），由引擎的 parse worker 执行；完成后 `phase=ready`，失败 `phase=parse_failed`；客户端轮询 `phase` 判断进度。
- **单实例锁**：`run/engine.lock`（fcntl，Windows 用 msvcrt 兼容），防重复消费。
- **优雅退出**（SIGTERM/SIGINT）：停止收新命令 → 当前章节安全点/checkpoint → 保存 → 释放锁 → 退出；超 grace 强杀并记录，不留孤儿。
- **恢复**（见 §12）。
- **命令服务**：localhost HTTP + token + 幂等（§3）。
- **配置**：每个任务开始时读取最新配置（DB 默认 + system.json 覆盖），见 §9。

---

## 7. API 层（薄）

- **入口**：`python -m server run`（`server/` 包，加载 `fcgi-bin/api.py` 的 app；本版**无 policy**）。
- 路由只做：收参（Pydantic）→ 构造命令发给 Core / 只读查 tasks.db → 统一响应。
- **禁止**：import `Audio/LLM/Parser`、任务循环、写 task 状态。
- 路由集：`upload / parse / generate / pause / resume / cancel / delete / retry / status / chapter / events / system-config / tts-voices / GUI`。
- 响应统一 `{code, msg, data}`（`api.md`）。
- 托管 GUI 静态资源。
- **Core 不可用时**：命令类返回明确错误（"引擎未运行"）；查询类仍可读 tasks.db 历史。

---

## 8. CLI

- 作为 Core 的客户端（`fcgi-bin/cli.py`），走同一 localhost HTTP 命令通道；不再内联执行。
- 能力与 API 对等：`add/list/get/pause/resume/cancel/retry/remove/status/logs/events`；支持 `--follow`（跟随进度）、`--json`。
- 与 API 共享 `services/control/*`（参数校验、命令构造、状态格式化），禁止各写一套业务规则。

---

## 9. 配置跨进程生效

- Core **每个任务开始时**读取 `ConfigService`（`data/system.db` 默认 + `cache/config/system.json` 覆盖）。
- 因此：**配置变更只影响之后新启动的任务，不改变已运行任务**。
- GUI 与文档必须明确提示这一点（避免用户误以为进行中的任务会应用新配置）。

---

## 10. 部署

### 10.1 systemd（推荐常驻）

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
# 环境变量/密钥由 .env 或 EnvironmentFile 提供

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

### 10.2 手动临时启动
```bash
python -m engine run          # 前台常驻引擎
python -m server run        # 另开终端启动 API
```

---

## 11. 目录结构（新增/调整）

```text
project/
├── fcgi-bin/
│   ├── api.py                  # API 唯一入口
│   └── cli.py                  # CLI（Core 客户端）
├── engine/                     # Core 引擎（系统层服务）
│   ├── __main__.py             # python -m engine run
│   ├── server.py               # 本地命令 HTTP + token + 发现文件
│   ├── scheduler.py
│   ├── handlers/               # parse / generate / merge / export
│   ├── store.py                # TaskStore(tasks.db, 读写)
│   ├── recovery.py
│   └── lock.py
├── services/
│   └── control/                # API/CLI 共享控制层
├── routers/                    # API 路由（薄）
├── models/                     # Pydantic
├── system/                     # config / response / db / deps
├── data/
│   ├── system.db               # 配置默认值（上一需求）
│   └── tasks.db                # 任务状态（本需求）
├── run/
│   ├── engine.json             # 运行时发现（端口/token/pid）
│   └── engine.lock
└── ...
```

---

## 12. 恢复策略（对齐 aria2 思路）

Core 启动时按**持久化状态**处理：

| 重启前状态 | 重启后行为 |
|---|---|
| `running`（崩溃/重启中断） | **自动继续**：中断章节 `running→pending` 重跑，已完成章节保留，任务回到 `queued/running` 重新入队 |
| `paused`（用户手动停） | **保持 paused**，不自动运行，等用户 resume |
| `pending` / `queued` | 正常入队执行 |
| `succeeded` / `failed` / `canceled` / `removed` | 保持 |

- 判据：`paused` 仅由用户操作产生；崩溃中断的任务保持 `running`，据此自动续跑。
- 章节级 checkpoint：已 `succeeded` 的章节跳过；被中断的章节从头重跑（覆盖写，幂等）。
- 保证：无重复消费、无孤儿 worker（单实例锁 + 原子领取）。

---

## 13. 验收清单（摘自契约 §13 并落地）

- 关闭 API 后，Core 继续执行任务。
- Core 停止后，API 仍能查询历史状态（只读 tasks.db）。
- Core 重启：`running` 自动续跑、`paused` 保持、已完成可查；无重复消费/孤儿。
- 多客户端并发提交不产生重复任务；同一 `command_id` 重复提交返回同一结果。
- 两个 Core 实例不会同时消费（单实例锁生效）。
- CLI 与 API 返回一致业务结果/错误码；CLI 不内联执行长任务。
- 优雅退出：SIGTERM 后当前章节安全点退出并保存；超时强杀有记录。
- 运行时发现文件存在且不含无关敏感信息。

---

## 14. 实施步骤

1. 建 `engine/` 包 + `system/db.py` 双库连接（system.db 只读配置、tasks.db 读写）+ `run/` 目录。
2. `tasks.db` schema + 迁移（`tasks / task_chapters / task_events / command_log / schema_meta`）。
3. `TaskStore`（Repository）+ 原子领取/心跳。
4. 把 `api.py` 的 `_generate_audio_task` 与编排抽到 `engine/handlers` + `scheduler`。
5. 本地命令 HTTP + token + 运行时发现 + 幂等 `command_log`。
6. 单实例锁 + 优雅退出 + 恢复（§12）。
7. `api.py` 变薄：命令转发 + 只读查询；去掉业务执行。
8. `cli.py` 改为 Core 客户端。
9. 抽 `services/control` 供 API/CLI 共用。
10. systemd unit + 手动启动文档；GUI/文档加"配置仅对新任务生效"提示。
11. 测试：进程分离、重启恢复、幂等、并发、验收清单。

---

## 15. 已定细节

1. **命令服务端口**：默认 `39300`，被占用则**顺延**（39301、39302…），实际端口写入发现文件。
2. **运行时目录**：可配置。开发/手动默认用项目根 `run/`；systemd 用 `RuntimeDirectory=ga-sprite-birds`（即 `/run/ga-sprite-birds`），确保服务用户可写。发现文件权限 0600。
3. **过期清理**：`TASK_RESULT_TTL` 迁移为 DB 清理任务，支持两种方式：
   - **定期自动清理**（引擎内定时器）；
   - **CLI 命令清理**：`cli.py clean` → 向引擎发 `task.cleanup` 命令，由引擎执行（引擎独占写）。
4. **运维命令**：本轮提供 `engine status`（PID/端口/任务计数）与 `engine doctor`（检查目录、权限、ffmpeg、DB、配置、端口）。
5. **进度获取**：本轮**先轮询**（`GET status` 读 tasks.db）；`task_events` 已持久化，**SSE 作为后续增强**，不改数据结构。

### 附：运行时目录说明
- `run/`（或 `/run/ga-sprite-birds/`）保存 `engine.json`（发现文件：host/port/token/pid/协议版本/启动时间）与 `engine.lock`（单实例锁）。
- 手动运行：项目 `run/`；systemd：由 `RuntimeDirectory` 创建，无需手动建、属主即服务用户。
