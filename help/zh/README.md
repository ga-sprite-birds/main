# GA Sprite Birds — 使用指南

> English version: [../en/README.md](../en/README.md) · 项目主页：[../../README.md](../../README.md)

GA Sprite Birds 把书籍或长文本变成有声书：自动拆分章节，可选地让 LLM 把书面语改写为自然口语，
逐章合成 MP3；支持按角色分配不同音色。

你可以用 **Web 界面**、**CLI** 或 **HTTP API** 驱动它——三种方式共享同一个引擎和同一份任务状态。

- **输入：** `.txt` / `.md` / `.pdf` · **输出：** 每章一个 `.mp3`（可选章节文本）
- **TTS：** Edge TTS（免费，需联网） · **LLM：** 本地 Ollama 或任意 OpenAI 兼容接口

---

## 1. 功能特点

| 功能 | 说明 |
|---|---|
| 章节拆分 | 识别章节标题（纯文本 / Markdown / PDF），逐章生成；可全选或只生成勾选章节 |
| 单角色 / 多角色配音 | 整本书一个音色，或按角色音色模板生成 |
| LLM 口语化 | 可选地把书面语改写为自然口语（Ollama 或 OpenAI 兼容接口） |
| 停顿与轻语气 | `off` / `pause` / `prosody`，按标点插入停顿、可选语气变化 |
| 音色试听 | 选定前先听一段缓存样音 |
| 暂停 / 继续 / 取消 / 重试 | 在章节边界协作生效；失败任务可重新入队 |
| 崩溃恢复 | 章节级 checkpoint：重启绝不重做已完成的章节 |
| 任务持久化 | 任务状态与事件存于 SQLite；关页面、重启进程都不丢进度 |
| 系统配置 | 三层配置（默认值 → 用户覆盖 → 任务快照），修改只对新任务生效 |
| 多语言 | 中文 / 英文界面、CLI 与 API 消息 |

> 界面覆盖单角色生成与系统配置；多角色生成、TTL 清理通过 CLI/API 提供。
> **角色分析不在 v2 的 add 流程中暴露**；多角色生成需要自行准备角色音色模板。

---

## 2. 快速开始

### 2.1 Docker（强烈推荐）

宿主机不需要 Python 或 FFmpeg，二者都在镜像内。

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
cp .env.example .env                  # 配置 LLM 凭据与部署参数
mkdir -p data run cache output logs uploads
sudo chown -R 1000:1000 data run cache output logs uploads
docker compose up -d --build
# 打开 http://127.0.0.1:8000/
# 8000 被占用时：API_HOST_PORT=18080 docker compose up -d --build
```

- 持久化数据：`./data`、`./run`、`./cache`、`./output`、`./logs`、`./uploads`。
- 镜像以非 root 的 `app` 用户运行（默认 `1000:1000`）；首次启动前先 `chown` 绑定目录，
  宿主机 UID/GID 不同时设置 `APP_UID`/`APP_GID` 并重建。
- 默认只发布到 `127.0.0.1`。局域网访问需设置 `API_BIND_HOST=0.0.0.0`，并启用
  `API_AUTH_ENABLED=true` + `API_AUTH_TOKEN`；GUI 顶部钥匙按钮保存令牌。
- CORS 默认关闭；需要时配置明确的来源列表。
- `models/` 是镜像内的 Python 代码包；模型缓存写到 `./cache/models`。
- Docker 与宿主机引擎不能同时共用 `data/`、`run/`（单实例锁）。
- 引擎命令通道（`127.0.0.1:39300`）不对外暴露。

systemd、目录权限、反向代理与升级回滚见[部署与运维](deployment.md)。

### 2.2 venv（原生方式）

需要 Python 3.10+ 和 FFmpeg。

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
```

先安装 FFmpeg（`apt install ffmpeg`、`brew install ffmpeg` 或 Windows 构建），用
`ffmpeg -version` 验证。

两种启动方式：

**方式 A — 本地 GUI 一键启动（Linux/macOS）。** `utils/quick/` 会拉起引擎与 API、
自动选择空闲 API 端口并打开界面：

```bash
bash utils/quick/linux-run.sh
./utils/quick/mac-run.command
```

**方式 B — 引擎与 API 分别启动（无 GUI / 后台模式）。** 适合服务器、自动化，
或只需要 CLI/API 的场景：

```bash
# 终端 1 —— Core 引擎（必需）
python -m engine run
# 终端 2 —— Control API + GUI（可选）
python -m server run
```

- **只用 CLI：** 只启动引擎即可；CLI 通过本地命令通道与引擎通信。
- **需要 GUI / HTTP API：** 两个进程都要启动。

API 端口被占用时会自动顺延；`--strict-port` 可固定端口。引擎默认监听 `127.0.0.1:39300`，
实际端口与 token 写入 `run/engine.json`。

### 2.3 开发环境（conda）

开发者可用 conda 搭建可复现的本地环境，见[开发文档](development.md)。
生产部署请使用 Docker 或 venv，不要使用 conda。

---

## 3. 文档导航

| 文档 | 内容 |
|---|---|
| [开发文档](development.md) | conda 环境、FFmpeg、`.env`、GUI 构建、测试、故障排查 |
| [开发者指南](developer-guide.md) | 全局契约、模块边界、新增配置项、i18n 同步、命令通道、测试 |
| [Utils 开发规范](utils.md) | `utils/` 下独立工具的结构、配置读取与约定 |
| [API 参考](api.md) | 全部端点、CLI/API 对等矩阵 |
| [部署与运维](deployment.md) | venv/Docker、systemd、目录权限、反向代理、升级回滚 |
| [设计规格](design/README.md) | [系统配置](design/v2-system-config.md) · [无头 Core](design/v2-headless-core.md) |
| systemd 模板 | [`scripts/systemd/`](../../scripts/systemd/)（core/api × user/system） |
| English docs | [../en/README.md](../en/README.md) |

---

## 4. 设计原理：一个引擎，两种接入方式

### 4.1 两个进程，一个引擎

```text
GUI / CLI / HTTP 客户端
        │
        ▼
Control API（python -m server run）            Core 引擎（python -m engine run）
· 接收上传、托管 GUI                    · 唯一的任务执行者
· 转发命令（幂等）                 ───▶ · 任务状态的唯一写者
· 只读查询任务状态                 ◀─── · 章节级 checkpoint、崩溃恢复
        │                                    │
        └────── 只读 ────▶ data/tasks.db ◀──── 写入 ────┘
```

- **引擎是唯一写者。** 任务状态、章节、事件只能由引擎写入，API 和 CLI 绝不直接写
  `tasks.db`；停掉 API 不影响正在运行的任务。
- **恢复是内置能力。** 引擎重启后，`running` 任务从最后一个成功章节续跑，`paused` 任务保持暂停。
- **配置按任务冻结快照。** 改配置不影响运行中的任务，只对之后新启动的任务生效。

### 4.2 CLI 模式 —— 面向本地批处理与脚本

`fcgi-bin/cli.py` 是引擎的轻客户端，适合本机与自动化：

- 一条命令即可串起**上传 + 解析 + 生成**（`cli.py add -i book.txt`）。
- 人类可读输出或 `--json`；`--follow` 持续输出进度。
- 完整控制面：`add / list / get / status / pause / resume / cancel / retry / remove / cancel-chapter / events / logs / clean / config / system`。
- 无需开放端口：CLI 通过本地命令通道与引擎通信。
- 适合 cron、批量转换与运维。

### 4.3 API 模式 —— 面向服务与集成

Control API（`python -m server run`）以 `/fcgi-bin/api/*` 暴露同样的能力，供远程客户端与 Web 界面使用：

- 分步端点 + JSON 请求体：`upload → parse → generate → status/下载`。
- 统一响应信封 `{"code", "msg", "data"}`；事件流按 `event_id` 游标增量拉取。
- 供其他系统上传、批处理与集成。
- 托管打包好的 GUI；界面每次点击都映射到同样的端点。
- 无内置鉴权，暴露时请绑定回环/内网地址并在前面加反向代理。

### 4.4 CLI 与 API 对比

| | CLI（`fcgi-bin/cli.py`） | HTTP API（`/fcgi-bin/api/*`） |
|---|---|---|
| 适合 | 脚本、cron、批处理、运维 | 集成、远程客户端、GUI |
| 调用 | 一条命令完成上传 + 解析 + 生成 | 分步端点、JSON 请求体 |
| 传输 | 仅本地命令通道 | 绑定地址上的 HTTP |
| 输出 | 人类可读或 `--json` | 统一 `{code, msg, data}` 信封 |
| 需要 API 服务 | 否 | 是 |

两者向同一个引擎提交**同样的幂等命令**，能力对等。

---

## 5. 如何使用

### 5.1 界面（GUI）

打开 <http://127.0.0.1:8000/>：

1. 拖入一个或多个 `.txt` / `.md` / `.pdf`，每个上传创建一个任务。
2. 设置输出目录、音色（可试听）和停顿模式，点击**解析**。
3. 勾选要生成的章节，点击**开始**。
4. **暂停**在当前章节完成后停下；**继续**生成剩余章节。已完成章节可在线播放或下载。
5. 侧边栏**系统配置**按分组编辑业务配置，带选项说明、覆盖徽标与按组重置。

### 5.2 CLI

```bash
# 上传 + 解析 + 排队生成，一步完成
python fcgi-bin/cli.py add -i book.txt --voice zh-CN-YunxiNeural --rate 1.2 --no-llm --start 1 --end 5

# 多角色：使用已有的角色音色模板
python fcgi-bin/cli.py add -i novel.txt --multi-voice --character-template cache/role/novel_characters.json

# 控制与跟踪
python fcgi-bin/cli.py list --status running
python fcgi-bin/cli.py pause <task_id> && python fcgi-bin/cli.py resume <task_id>
python fcgi-bin/cli.py events <task_id> --follow

# 业务配置（与 GUI 同一份存储）
python fcgi-bin/cli.py config set TTS_RATE 1.15
```

全部子命令见 `python fcgi-bin/cli.py --help`。角色分析不在 v2 的 `add` 流程中；
多角色模板请自行准备（见开发者指南）。

### 5.3 API

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

错误码分段：`1000` 参数、`2000` 认证、`3000` 业务、`4000` 系统；引擎不可用时 HTTP `503` +
`code 3004`。全部端点见 [API 参考](api.md)。

### 5.4 任务生命周期

```text
pending ──▶ queued ──▶ running ──▶ succeeded / failed / canceled
                ▲          │
                │          ├──▶ paused ──▶ queued (resume)
                └──────────┘         failed ──▶ queued (retry)
任意状态 ──▶ removed
```

暂停/取消在章节边界生效；运行中任务每 10 秒刷新心跳。

### 5.5 输出目录

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
