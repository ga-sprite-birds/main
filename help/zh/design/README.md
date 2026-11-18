# v2 设计文档 · 开发索引

> English version：[../../en/design/README.md](../../en/design/README.md)
>
> 你是开发者：**严格按本目录文档实现**。
> 本目录是 v2「绝对技术重构」的落地设计；总纲契约在 `.augment/rules/imported/`。
> 冲突时：本目录「已定细节」优先（更具体）；未覆盖处遵循契约。

---

## 1. 文档索引

| 文档 | 内容 | 状态 |
|---|---|---|
| `v2-system-config.md` | env 拆分 / 系统配置：三层配置、`ConfigService`、系统配置 API、TTS 音色校验、GUI 配置页 | ✅ 已定稿 |
| `v2-headless-core.md` | 任务与 API 表现层进程级分离：`engine/` Core、命令通道、`tasks.db`、状态机、恢复、systemd | ✅ 已定稿 |

两份文档共同构成 v2 第一轮重构，**一起落地**。

---

## 2. 两需求关系

```
v2-system-config： ConfigService（读 system.db 默认 + system.json 覆盖）
        │ 被读取
        ▼
v2-headless-core： engine（每个任务开始时读配置）  ── 唯一写 tasks.db
                  api.py（薄控制面，只读 tasks.db）── 只发命令
```

- `system/db.py` 统一提供 `system.db`（配置默认值）与 `tasks.db`（任务状态）两个连接。
- `ConfigService`：**API 写 `system.json`**；**engine 读生效配置**。

---

## 3. 统一约定（两份文档共用，务必遵守）

1. **契约优先**：遵循 `.augment/rules/imported/`（`task-system.md` / `api.md` / `python.md` / `sql.md` / `language.md`）。**非 Python 部分（php/vue/vite）忽略。**
2. **入口**：
   - `python -m server run`（`server/` 包）—— 唯一 API 入口；**本版无 policy**，只有 `/fcgi-bin/api/*`。
   - `fcgi-bin/cli.py` —— CLI，作为 Core 的客户端。
   - `engine/` —— Core 引擎，`python -m engine run`（系统层 systemd / 手动）。
3. **响应**：`{ code: 0 成功, msg, data }`；错误码分段 1000~4999（见 `api.md`）。
4. **命名**：字段 `snake_case`；分页 `list / total / page / page_size`。
5. **i18n**：默认中英（`en_US` / `zh_CN`，可保留 `ja_JP`）；配置分组/项 label、返回文案用 i18n key（`ga_birds/Langues/*.json`）。
6. **目录**：`system/ services/ routers/ models/ engine/ fcgi-bin/ data/ run/ core_module(=ga_birds)/`。
7. **配置分层**：`.env`=部署/密钥；`data/system.db`=默认值；`cache/config/system.json`=用户覆盖；**业务参数走 API / 任务参数**。
8. **数据库**：SQLite + WAL；`data/system.db`、`data/tasks.db`；遵循 `sql.md`（表/字段注释、主键、`created_at/updated_at`、禁止 `SELECT *`、必 `LIMIT`）。
9. **写入归属**：**只有 engine 写 `tasks.db`**；**API 只读**。`ConfigService`：API 写 `system.json`，engine 读。
10. **恢复**：`running`（崩溃中断）→ 自动续跑；`paused`（用户手动停）→ 保持。
11. **不做旧兼容**：弃用 `config.X` 读 env 的方式；旧业务参数不再走 env。
12. **配置生效**：变更仅对**之后新启动**的任务生效；GUI/文档需明示。

---

## 4. 实施顺序与依赖

> 建议顺序；后阶段依赖前阶段产物。

**Phase 0 · 骨架与统一底座**
- 建目录：`system/ services/ routers/ models/ engine/ data/ run/`
- `system/response.py`（统一 `{code,msg,data}`）、`system/db.py`（system.db/tasks.db 连接，WAL）
- `system/config.py`（pydantic-settings，仅部署/密钥）

**Phase 1 · 配置体系（`v2-system-config.md`）**
- `system/config_schema.py`（schema + 种子默认）
- seed `data/system.db` + `ConfigService`（含 `system.json` 覆盖/重置/热更新）
- `routers/system_config.py`、`routers/tts.py`
- TTS 音色缓存与校验

**Phase 2 · 任务引擎（`v2-headless-core.md`）**
- `data/tasks.db` schema + 迁移 + `TaskStore`（Repository）
- 把 `api.py` 的 `_generate_audio_task` 抽到 `engine/handlers` + `engine/scheduler`
- 本地命令 HTTP + token + 运行时发现文件 + 幂等 `command_log`
- 单实例锁、优雅退出、恢复（§12）
- `engine status` / `engine doctor` / `task.cleanup`

**Phase 3 · 薄 API + CLI**
- `api.py` 变薄（命令转发 + 只读查询，去掉业务执行）
- `cli.py` 改为 Core 客户端
- `services/control/` API/CLI 共用

**Phase 4 · GUI**
- 系统配置页（分组渲染、保存/重置、覆盖标记、仅对新任务生效提示）
- 进度用轮询（SSE 后置）

**Phase 5 · 收尾**
- 改造 `ga_birds` 全部读配置方式
- 瘦身 `.env/.env.example` + 更新文档
- systemd 示例 + 手动启动说明
- 单测 + 验收清单

**依赖关系**：Phase 1 ⇐ Phase 0；Phase 2 ⇐ Phase 0（读配置部分依赖 Phase 1）；Phase 3 ⇐ Phase 2；Phase 4 ⇐ Phase 1 + Phase 3。

---

## 5. 决策记录（已确认）

- 许可证：Apache-2.0（见仓库 `LICENSE`）。
- 配置默认值：`data/system.db`；用户覆盖：`cache/config/system.json`（部分覆盖，只记最后一次修改）。
- `*_DIR` 归部署级（API 不干涉）；`OUTPUT_BASE_PATH` 归业务配置（API 管）。
- 命令通道：**localhost HTTP + token + 运行时发现文件**（跨平台，不用 UDS）。
- Core 包名：`engine/`；入口 `python -m engine run`。
- 状态库：`data/tasks.db`（WAL），**engine 单写 / API 只读**。
- API 结构：`python -m server run`（`server/` 包）唯一，**无 policy**。
- 端口：默认 `39300`，占用顺延。
- 运行时目录：可配置（开发 `run/`；systemd `RuntimeDirectory`）。
- 清理：定期自动 + `cli.py clean`（引擎执行 `task.cleanup`）。
- 运维命令：`engine status` / `engine doctor`。
- 进度：本轮**轮询**，SSE 后置。
- 恢复：`running`→续跑；`paused`→保持。
- **parse 异步**：`task.parse` 立即返回（`phase=parsing`），引擎后台 worker 执行，完成 `phase=ready`/失败 `phase=parse_failed`；客户端轮询 `phase`。
- **数据库连接**：`TaskStore` 每线程独立连接、请求结束回收；`engine doctor/status` 只读、不迁移。
- **无 policy**：GUI 使用业务路由 `/dashboard`、`/theme`、`/system/config`；后端仅做 SPA 回退，无 `/policy` API。

---

## 6. 全局验收（端到端）

除两份文档各自的验收清单外，必须满足：

- **杀 API**：正在执行的任务继续（Core 独立）。
- **杀/重启 Core**：`running` 任务续跑；`paused` 保持；已完成可查；无重复消费、无孤儿。
- **Core 停机**：API 仍能查询历史（只读 `tasks.db`）。
- **配置变更**：只对之后新启动的任务生效。
- **幂等**：同一 `command_id` 重复提交返回同一结果。
- **单实例**：不会有两个 Core 同时消费任务。
- **统一响应**：所有 API 返回 `{code,msg,data}`。

---

## 7. 实施状态（v2 落地记录）

五个 Phase 全部完成，`pytest tests/unit` 全绿（101 项）；真实链路集成测试见 `tests/integration/`。

| Phase | 落地物 | 验证方式 |
|-------|--------|----------|
| 0 骨架 | `system/response.py`、`system/db.py`、`system/config.py` | 单测 + `engine doctor` |
| 1 配置 | `system/config_schema.py`（7 组 46 项）、`ConfigService`、`routers/system_config.py`、`routers/tts.py` | `tests/unit/test_config_service.py`、`test_system_config.py`（26 项，含跨实例热重载） |
| 2 引擎 | `engine/`（store/scheduler/service/handlers/lock/runtime/ops）、`tasks.db` 迁移 | `test_engine_store.py`、`test_engine_service.py` |
| 3 薄 API + CLI | `server/`（Control API 启动器）、`fcgi-bin/api.py`、`fcgi-bin/cli.py`、`services/control/`、`services/task_query_service.py` | `test_api_v2.py`（20 项契约测试） |
| 4 GUI | `gui/src/views/system/` + `ConfigField.vue`、路由 `/system/config`、侧栏 7 组、i18n、单文件构建 | `vite build` 通过 + 配置 API 端到端 |
| 5 收尾 | `.env` 瘦身、部署文档（systemd + 运维）、[API 参考](../api.md)、README 重写、测试迁移 | `pytest tests/unit` 101 passed |

### 验收证据

| 验收项 | 结果 |
|--------|------|
| 杀 API，任务继续 | ✅ Core 独立调度，`engine status` 显示 worker 仍在跑 |
| 杀 Core 后重启续跑 | ✅ 强杀于第 3 章执行中：事件 `task.recovered{action:"requeued"}` → `task.started{attempts:2}` → 终态 `task.succeeded{generated:[3,4], skipped:[1,2]}` |
| Core 停机时 API 只读 | ✅ `GET /task/{id}/status` 返回 `code 0`（`running, 2/4`）；`GET /engine` 返回 `503`/`3004` |
| 配置只对新任务生效 | ✅ 任务创建时冻结 `params.config_snapshot`；`ConfigService` 按文件签名自动重载，API 写入后引擎实例立即读到新值 |
| 幂等 | ✅ 同 `Idempotency-Key` 重复上传返回同一 `task_id`（落盘路径由 key 派生）；同 `command_id` 不同输入返回 `3001` |
| 单实例 | ✅ 第二个 `python -m engine run` 立即退出，返回码 `2` |
| 统一响应 | ✅ 全部路由 `{code,msg,data}`；未知路由 `404`+`3002`；引擎不可用 `503`+`3004` |
| 枚举项可解释 | ✅ schema 下发 `options_i18n` / `description_i18n`；GUI 选项带译文 + 灰色说明，选中后字段下方回显该值含义（`off/pause/prosody` 不再漏英文） |

### 与早期契约的两处偏差（已在文档声明）

1. `run/engine.json` 内含 Bearer token（`0600`）。`task-system.md` §3.4 要求发现文件不含凭证；
   v2 选择合并写入，因为命令通道只绑 `127.0.0.1`、token 生命周期与进程一致。
   若需分离，把 `token` 移到 `run/engine.token` 只需改 `engine/runtime.py`。
2. WAL 在 SMB/UNC 共享目录上可能因无法创建 `-shm` 而失败。`system/db.py` 现在对
   `PRAGMA journal_mode=WAL` 做 3 次重试并降级到回滚日志，保证网络盘上也能写入。

### 已知限制

- `vite build` 依赖 rollup 原生模块，Windows 上无法从 UNC 共享目录构建（需本地盘）。
- GUI 未暴露多角色生成与角色分析入口。多角色生成可在 CLI/API 中通过已有的角色模板使用；角色分析不在 v2 的 add 流程中暴露。
- 进度仍是轮询（SSE 后置）。
