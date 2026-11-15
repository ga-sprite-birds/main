# GA Sprite Birds 开发规范（v2）

本文档定义 v2 架构（Core 引擎 + 薄 API 双进程）下的开发标准：模块边界、配置管理、命令通道、i18n、GUI 构建与测试约定。改动代码前先读本文档与 `docs/design/` 两份规格。

---

## 1. 架构总览

```
┌─────────┐  命令（localhost HTTP + token）  ┌──────────────┐
│ Control │ ───────────────────────────────▶ │  Core 引擎    │
│   API   │                                  │  engine/      │
│ fcgi-bin│ ◀──────────── 结果/事件 ──────── │  唯一执行者    │
│ api.py  │                                  │  唯一写状态    │
└────┬────┘                                  └──────┬───────┘
     │ 只读查询（PRAGMA query_only）                 │ 写
     ▼                                               ▼
                 data/tasks.db（WAL，单写多读）
```

**不可违反的边界：**

1. **引擎是唯一执行者、唯一写者**：任务状态、checkpoint、事件只能由 `engine/` 写。API/CLI 绝不直接写 `tasks.db`。
2. **API 是薄控制面**：接收上传、转发命令（`command_id` 幂等）、只读查询。只读连接必须开 `PRAGMA query_only=ON`。
3. **CLI 与 API 对等**：CLI 不直接调业务逻辑，而是和 API 一样通过 `services/control/` 的命令通道向引擎发命令。新增能力必须两侧同时可用。
4. **配置只对新任务生效**：任务启动时冻结 `params.config_snapshot`；运行中任务永远读快照，不读实时配置。

## 2. 目录结构与模块职责

```text
engine/                 Core 引擎
  __main__.py           python -m engine run/status/doctor
  server.py             localhost HTTP 命令服务（token 鉴权）
  service.py            命令分发：task.* / config.get|set / system.info|stats
  scheduler.py          并发调度、心跳、TTL 清理
  store.py              TaskStore，tasks.db 唯一写者
  lock.py               单实例锁（fcntl/msvcrt）
  handlers/             parse / generate / multi_voice 执行器
  migrations/           tasks.db 版本化迁移（含 rollback）
services/
  config_service.py     三层配置（读/写/重置/热重载）
  task_query_service.py API/CLI 共用的只读查询
  tts_service.py        音色目录、音色校验、试听合成
  control/              命令通道客户端（API/CLI 侧）
routers/                FastAPI 路由（system_config、tts）
models/                 Pydantic 请求模型、task_view 序列化
system/                 settings（仅部署项）、db、日志、响应信封、依赖注入
system/config_schema.py 业务配置的唯一事实来源（7 组 45+ 项）
fcgi-bin/               api.py（薄 API）、cli.py（控制客户端）
ga_birds/               领域层（引擎 handler 调用）
  Parser/  LLM/  Audio/  character_analyzer/  Common/  Utils/
gui/                    Vue 3 + Element Plus（构建产物：根目录 index.html）
```

**依赖方向**：`fcgi-bin` / `routers` → `services` → `engine` / `ga_birds`。`ga_birds/` 不得反向依赖 `engine/`、`services/` 或 `system/`。

## 3. 响应与错误约定

- 所有 API 响应统一信封 `{"code": 0, "msg": "ok", "data": {}}`，构造只走 `system/response.py` 的 `success()/fail()`。
- 错误码分段：`1000` 参数、`2000` 认证、`3000` 业务、`4000` 系统。新增错误码先查现有分段，不要发明新段。
- **错误响应（含全局 404、试听失败）必须带 `Cache-Control: no-store`**——404 属于可启发式缓存的状态码，不加就会被浏览器回放陈旧失败。成功且可复用的二进制响应（如试听）用 `private, max-age=86400`。
- 引擎不可用时 API 返回 HTTP `503` + `code 3004`，不做进程内降级执行。

## 4. 配置管理

三层结构，**事实来源是 `system/config_schema.py`**：

| 层 | 位置 | 说明 |
|----|------|------|
| 默认值 | `data/system.db` | 版本化种子 |
| 用户覆盖 | `cache/config/system.json` | 原子写，只存差值；按 `(mtime_ns, size)` 签名热重载 |
| 任务快照 | `tasks.db.params.config_snapshot` | 任务启动时冻结 |

### 新增一个配置项的步骤（全部必须做）

1. `system/config_schema.py`：在对应分组加 `_item(...)`；需要说明文案时传 `description=True`，枚举会自动挂 `options_i18n`。
2. `ga_birds/Langues/{zh_CN,en_US}.json`：在 `config.item` 加标题、`config.option.<KEY>.<值>` 加选项译文（`<值>_hint` 为说明）、`config.desc` 加字段说明。**每个枚举值在两种语言都必须有译文**，有测试强制校验。
3. 运行 `python scripts/sync_config_i18n.py` 重新生成 `gui/src/i18n/lang/config_*.js`。
4. 在消费方读取：`config/__init__.py` 的 `business_config_snapshot()` / `use_config_snapshot()`。**不要**在模块导入期捕获配置值——像 `DialogueParser` 那样把值存为实例属性，快照才能生效。
5. 校验规则用 `_item` 的 `gt/ge/lt/le/options` 声明，非法值由 ConfigService 统一拒绝（`code 1000` + `data.key`），不要在调用方散落校验。

## 5. i18n 约定

- 后端语言文件 `ga_birds/Langues/{zh_CN,en_US}.json` 是**唯一事实来源**；前端配置区文案由脚本同步生成，不手工编辑 `gui/src/i18n/lang/config_*.js`。
- GUI 页面文案在 `gui/src/i18n/lang/{zh_CN,en_US}.js`，新增 key 两种语言都要补。
- 错误消息允许返回 i18n key（如 `config.error.invalid_voice`），前端 `te()` 命中则翻译，否则原样显示。

## 6. 命令通道与幂等

- 命令格式：`execute(command_id, command, payload)`，命令集 `task.*` / `config.get|set` / `system.info|stats`。
- `command_id` 幂等：重复提交返回首次结果（`command_log` 表）。**新增命令必须设计幂等键**，上传用 `Idempotency-Key`（落盘路径由 `sha256(key)` 派生）。
- 状态机：`pending→queued→running→succeeded/failed/canceled`，`running→paused→queued`，任意→`removed`。暂停/取消在章节边界协作生效。
- 恢复语义：启动时 `running` 重新入队（从最后成功章节续跑），`paused` 保持不动。

## 7. 重试与外部调用

- 重试工具集中在 `ga_birds/Utils/retry_utils.py`：`RetryableError` / `NonRetryableError` 分类，`create_retry_decorator()` 构造策略。
- 默认策略：TTS 最多 5 次指数退避（1s–30s）；LLM 最多 3 次（1s–10s）；文件 I/O 最多 3 次快速重试。网络/限流/超时算可重试；参数错误、认证失败算不可重试。
- SQLite WAL 在 SMB 上偶发失败：连接层已做 3 次重试 + 降级 `delete` 日志模式，业务层不要再包一层。

## 8. GUI 开发

- 技术栈：Vue 3 + Vite + Element Plus + Pinia + Vue I18n；构建为**单文件** `index.html`（`inlineDynamicImports`）。
- **Windows 上必须在本地磁盘构建**（rollup 原生模块无法从 UNC/SMB 加载）：把 `gui/` 复制到本地 → `npm run build` → 把 `index.html` 拷回共享目录。
- 主题色一律用 `--theme-*` 语义变量，不要写死颜色；Element Plus 组件的色板变量（如 `--el-menu-*`）在使用处显式覆盖到主题变量，深色主题下默认值不可靠（悬停底色 `primary-light-9` 会近白）。
- API 请求统一走 `gui/src/utils/request.js`（信封解包、错误提示）。

## 9. 测试约定

```bash
python -m pytest tests          # pytest.ini：unit / integration / slow 标记
```

- 单元测试放 `tests/unit/`，不依赖运行中的服务；集成测试放 `tests/integration/`，引擎不可达时**自动 skip**（不 fail）。
- 契约类测试优先：schema 下发字段、枚举译文完整性、缓存头、信封结构，这些比实现细节更值得锁死。
- 改动 API 行为必须同步改 `tests/unit/test_api_v2.py` 的契约断言与 `docs/api.md`。

## 10. 提交前检查单

1. 改了配置 schema → 补两种语言译文 + 跑 `sync_config_i18n.py` + 相关测试。
2. 改了 API/CLI 行为 → 更新 `docs/api.md` 与对等矩阵。
3. 改了前端 → 本地盘重新构建并回拷 `index.html`。
4. `python -m pytest tests` 全绿。
5. 涉及部署 → 更新 `docs/deploy/README.md`。
