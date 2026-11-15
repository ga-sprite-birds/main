# GA Sprite Birds

> 把书籍或长文本变成有声书：自动拆分章节，可选地让 LLM 把书面语改写为自然口语，逐章合成 MP3；支持为不同角色分配不同音色。

GA Sprite Birds 是一个可自托管的有声书生成引擎。它识别章节边界，可把文本改写为口语，再把每一章渲染成音频。你可以用 **Web 界面**、**CLI** 或 **HTTP API** 驱动它——三种方式共享同一个引擎和同一份任务状态，CLI 排的任务能在界面里看到，也能用 API 控制。

- **输入：** `.txt` / `.md` / `.pdf` · **输出：** 每章一个 `.mp3`（可选章节文本）
- **TTS：** Edge TTS（免费，需联网） · **LLM：** 本地 Ollama 或任意 OpenAI 兼容接口

---

## 1. 功能特点

| 功能 | 说明 |
|---|---|
| 章节拆分 | 识别章节标题（纯文本 / Markdown / PDF），逐章生成；可全选或只生成勾选章节 |
| 单角色 / 多角色配音 | 整本书一个音色，或识别角色并为每个角色分配音色 |
| LLM 口语化 | 可选地把书面语改写为自然口语（Ollama 或 OpenAI 兼容接口） |
| 停顿与轻语气 | `off` / `pause` / `prosody`，按标点插入停顿、可选语气变化 |
| 音色试听 | 选定前先听一段缓存样音 |
| 暂停 / 继续 / 取消 / 重试 | 在章节边界协作生效；失败任务可重新入队 |
| 崩溃恢复 | 章节级 checkpoint：重启绝不重做已完成的章节 |
| 任务持久化 | 任务状态与事件存于 SQLite；关页面、重启进程都不丢进度 |
| 系统配置 | 三层配置（默认值 → 用户覆盖 → 任务快照），修改只对新任务生效 |
| 多语言 | 中文 / 英文界面、CLI 与 API 消息 |

> 界面当前覆盖单角色生成与系统配置；多角色生成、角色分析、TTL 清理通过 CLI/API 提供。

---

## 2. 安装与文档导航

**环境要求：** Python 3.10+ 和 FFmpeg。只有要自己构建前端时才需要 Node.js。

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

启动引擎和 API，打开 <http://127.0.0.1:8000/>：

```bash
python -m engine run        # 终端 1 — Core 引擎
python fcgi-bin/api.py      # 终端 2 — Control API + GUI
```

**文档导航**

| 文档 | 内容 |
|---|---|
| [安装指南](./INSTALL.zh.md) · [Install guide](./INSTALL.md) | 运行环境、初始安装、本地与 API 部署、故障排查 |
| [API 参考](../docs/api.md) | 全部端点、CLI/API 对等矩阵 |
| [部署与运维](../docs/deploy/README.md) | systemd、目录权限、反向代理、升级回滚 |
| [开发规范](./development-guide.zh.md) · [Development guide](./development-guide.md) | 架构边界、新增配置项、i18n 同步、测试 |
| 设计规格 | [系统配置](../docs/design/v2-system-config.md) · [无头 Core](../docs/design/v2-headless-core.md) |
| systemd 单元模板 | [`scripts/systemd/`](../scripts/systemd/)（core/api × user/system） |

---

## 3. 设计原理：一个引擎，两种接入方式

### 3.1 两个进程，一个引擎

```text
GUI / CLI / HTTP 客户端
        │
        ▼
Control API（fcgi-bin/api.py）          Core 引擎（python -m engine run）
· 接收上传、托管 GUI                    · 唯一的任务执行者
· 转发命令（幂等）                 ───▶ · 任务状态的唯一写者
· 只读查询任务状态                 ◀─── · 章节级 checkpoint、崩溃恢复
        │                                    │
        └────── 只读 ────▶ data/tasks.db ◀──── 写入 ────┘
```

- **引擎是唯一写者。** 任务状态、章节、事件只能由引擎写入，API 和 CLI 绝不直接写 `tasks.db`；停掉 API 不影响正在运行的任务。
- **恢复是内置能力。** 引擎重启后，`running` 任务从最后一个成功章节续跑，`paused` 任务保持暂停。
- **配置按任务冻结快照。** 改配置不影响运行中的任务，只对之后新启动的任务生效。

### 3.2 CLI 模式 —— 面向本地批处理与脚本

`fcgi-bin/cli.py` 是引擎的轻客户端，适合本机与自动化：

- 一条命令即可串起**上传 + 解析 + 生成**（`cli.py add -i book.txt`）。
- 人类可读输出或 `--json`；`--follow` 持续输出进度。
- 完整控制面：`add / list / get / status / pause / resume / cancel / retry / remove / events / clean / config / system`。
- 无需开放端口：CLI 通过本地命令通道与引擎通信。
- 适合 cron、批量转换与运维。

### 3.3 API 模式 —— 面向服务与集成

`fcgi-bin/api.py` 以 `/fcgi-bin/api/*` 暴露同样的能力，供远程客户端与 Web 界面使用：

- 分步端点 + JSON 请求体：`upload → parse → generate → status/下载`。
- 统一响应信封 `{"code", "msg", "data"}`；事件流按 `event_id` 游标增量拉取。
- 供其他系统上传、批处理与集成。
- 托管打包好的 GUI；界面每次点击都映射到同样的端点。
- 无内置鉴权，暴露时请绑定回环/内网地址并在前面加反向代理。

### 3.4 CLI 与 API 对比

| | CLI（`fcgi-bin/cli.py`） | HTTP API（`/fcgi-bin/api/*`） |
|---|---|---|
| 适合 | 脚本、cron、批处理、运维 | 集成、远程客户端、GUI |
| 调用 | 一条命令完成上传 + 解析 + 生成 | 分步端点、JSON 请求体 |
| 传输 | 仅本地命令通道 | 绑定地址上的 HTTP |
| 输出 | 人类可读或 `--json` | 统一 `{code, msg, data}` 信封 |
| 需要 API 服务 | 否 | 是 |

两者向同一个引擎提交**同样的幂等命令**，能力对等。

---

## 4. 如何使用

### 4.1 启动

```bash
python -m engine run        # 终端 1 — Core 引擎（Ctrl+C 优雅停止）
python fcgi-bin/api.py      # 终端 2 — Control API + GUI
```

引擎状态：`python -m engine status`（PID、端口、任务计数）。默认监听 `127.0.0.1:39300`，端口和 token 写入 `run/engine.json`。

### 4.2 界面（GUI）

打开 <http://127.0.0.1:8000/>：

1. 拖入一个或多个 `.txt` / `.md` / `.pdf`，每个上传创建一个任务。
2. 设置输出目录、音色（可试听）和停顿模式，点击**解析**。
3. 勾选要生成的章节，点击**开始**。
4. **暂停**在当前章节完成后停下；**继续**生成剩余章节。已完成章节可在线播放或下载。
5. 侧边栏**系统配置**按分组编辑业务配置，带选项说明、覆盖徽标与按组重置。

### 4.3 CLI

```bash
# 上传 + 解析 + 排队生成，一步完成
python fcgi-bin/cli.py add -i book.txt --voice zh-CN-YunxiNeural --rate 1.2 --no-llm --start 1 --end 5

# 多角色：先分析角色，再按模板生成
python fcgi-bin/cli.py add -i novel.txt --analyze-characters --analysis-mode hybrid --character-list characters.txt
python fcgi-bin/cli.py add -i novel.txt --multi-voice --character-template cache/role/novel_characters.json

# 控制与跟踪
python fcgi-bin/cli.py list --status running
python fcgi-bin/cli.py pause <task_id> && python fcgi-bin/cli.py resume <task_id>
python fcgi-bin/cli.py events <task_id> --follow

# 业务配置（与 GUI 同一份存储）
python fcgi-bin/cli.py config set TTS_RATE 1.15
```

`characters.txt` 每行一个 `名字 [性别]`（如 `张三 male`、`李四 female`）。全部子命令见 `python fcgi-bin/cli.py --help`。

### 4.4 API

```bash
# 上传（幂等）
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/upload" \
  -F "file=@book.txt" -H "Idempotency-Key: book-v1"

# 解析（后台执行），然后生成选中章节
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/parse" \
  -H "Content-Type: application/json" -d '{"task_id":"<id>","command_id":"parse-1"}'
curl -X POST "http://127.0.0.1:8000/fcgi-bin/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<id>","chapter_indexes":[1,2],"rate":1.2,"prosody_mode":"prosody"}'

# 进度查询；音色试听（audio/mpeg）
curl "http://127.0.0.1:8000/fcgi-bin/api/task/<id>/status"
curl -o preview.mp3 "http://127.0.0.1:8000/fcgi-bin/api/tts/preview?voice=zh-CN-YunxiNeural"
```

错误码分段：`1000` 参数、`2000` 认证、`3000` 业务、`4000` 系统；引擎不可用时 HTTP `503` + `code 3004`。全部端点见 [docs/api.md](../docs/api.md)。

### 4.5 任务生命周期

```text
pending ──▶ queued ──▶ running ──▶ succeeded / failed / canceled
                ▲          │
                │          ├──▶ paused ──▶ queued (resume)
                └──────────┘         failed ──▶ queued (retry)
任意状态 ──▶ removed
```

暂停/取消在章节边界生效；运行中任务每 10 秒刷新心跳。

### 4.6 输出目录

每个源文件在输出根目录下得到同名子目录：

```text
output/示例书名/
    ├── 001-第一章.mp3
    ├── 001-第一章.txt
    └── 002-第二章.mp3
```

前置章节（默认匹配 `导读,前言`）使用 `000` 前缀；多角色输出在 `示例书名/multi/` 下。

---

**作者：** adam · dev@ebf.hk · <http://ebf.cc>
**源码：** <https://github.com/tiger-sprite/ga-sprite-birds>
