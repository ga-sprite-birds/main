# GA Sprite Birds — 开发文档

> English version：[../en/development.md](../en/development.md) · 使用指南：[README.md](README.md) · 部署：[deployment.md](deployment.md)

本文面向**开发者**：包含基于 conda 的本地安装、源码运行、GUI 构建、测试与故障排查。

> 生产部署请使用 **Docker（推荐）** 或原生 **venv**；conda 只是开发环境，不用于生产。
> 参见根目录 [README](../../README.md) 与[部署与运维](deployment.md)。

---

## 1. 环境要求

| 项目 | 要求 | 说明 |
|---|---|---|
| 系统 | Windows 10+ / macOS 10.15+ / Linux | |
| Python | 3.10+ | conda 环境固定为 3.10 |
| FFmpeg | **必需** | conda 环境已包含；用于 MP3 导出 / 音频合并 |
| Node.js | 可选 | 仅在自行构建前端时需要 |
| 内存 | 最低 4 GB；使用本地 LLM 建议 16 GB+ | 只跑 API 占用很小 |
| 磁盘 | 约 1 GB + 生成的音频 | 含依赖与缓存 |
| 网络 | Edge TTS / 在线 LLM 需要联网 | 本地 Ollama 可离线 |

---

## 2. 获取代码

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
```

## 3. 创建 conda 环境

`environment.yml` 已包含 Python 3.10、FFmpeg，并通过 `pip install -r requirements.txt` 安装依赖：

```bash
conda env create -f environment.yml
conda activate ga-sprite-birds
```

之后如果 `requirements.txt` 有更新：

```bash
pip install -r requirements.txt
```

## 4. 验证 FFmpeg

```bash
ffmpeg -version
```

conda 环境自带 FFmpeg。若想使用系统安装的版本，安装后保持 `FFMPEG_PATH` 为空（走 `PATH`），
或把 `FFMPEG_PATH` 指向可执行文件所在目录。

## 5. （可选）本地 LLM

只有不接在线 API、需要 LLM 口语化时才需要：

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:7b      # 默认本地模型；可在 .env 修改
```

Windows / macOS 安装包：<https://ollama.com/download>。也可以完全跳过本地模型，使用任意
OpenAI 兼容接口（`LLM_MODE=api`）。

## 6. 配置 `.env`

```bash
cp .env.example .env
```

`.env` 只放**部署级配置与凭证**：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `LLM_MODE` | `local` | `local`（Ollama）或 `api`（OpenAI 兼容） |
| `LLM_API_ENDPOINT` / `LLM_API_KEY` / `LLM_API_MODEL` | — | `api` 模式的地址、密钥、模型 |
| `LLM_LOCAL_HOST` / `LLM_LOCAL_MODEL` | `http://localhost:11434` / `deepseek-r1:7b` | 本地 Ollama |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Control API 绑定地址 |
| `API_AUTH_ENABLED` / `API_AUTH_TOKEN` | `false` / 空 | 可选令牌鉴权；API 离开 loopback 时必须启用 |
| `API_CORS_ENABLED` / `API_CORS_ORIGINS` | `false` / 空 | 默认关闭 CORS；需要时使用明确来源 |
| `API_MAX_UPLOAD_SIZE` | `100` | 上传上限（MB）；`0` 不限 |
| `API_MAX_JSON_BODY_SIZE` | `1` | JSON 请求体上限（MB）；`0` 不限 |
| `API_LOCAL_READ_ROOTS` | 空 | `/upload?path=` 额外允许的根目录；uploads/ 始终允许 |
| `TASK_MAX_CONCURRENT` | `2` | 引擎并发任务数 |
| `TASK_RESULT_TTL` | `86400` | 终态任务记录保留秒数；`0` 永久保留 |
| `FFMPEG_PATH` | 空 | FFmpeg 目录；空则使用系统 `PATH` |
| `MODEL_CACHE_DIR` | `./cache/models` | 下载的模型缓存（与 `models/` 代码包分离） |
| `LOG_LEVEL` / `LOG_FILE` | `INFO` / `./logs/app.log` | 日志 |

> 路径安全：`/upload?path=` 只能访问 `API_UPLOAD_DIR` 及 `API_LOCAL_READ_ROOTS`；
> `output_path` 必须位于 `OUTPUT_BASE_PATH` 内；文件名模板不能包含 `/`、`\` 或 `..`；
> `character_template` 必须位于 `CHARACTER_CACHE_DIR` 内。符号链接逃逸和 `..` 穿越都会被拒绝。

> **业务配置不在 `.env`。** 语言、音色、语速、章节规则、输出策略以及新的按次开关来自
> `data/system.db`（默认值）+ `cache/config/system.json`（用户覆盖）。在 GUI「系统配置」页或
> `python fcgi-bin/cli.py config set …` 修改；无需重启，对新任务生效。

## 7. 验证环境

```bash
python -m engine doctor --json   # 目录、权限、数据库、ffmpeg、发现文件、配置
python -m pytest tests/unit -q   # 单元测试，无需启动服务
```

`doctor` 会检查 data/run 目录可写、`tasks.db` 完整性、FFmpeg、配置服务与运行时发现文件；
它是只读的，不会执行数据库迁移。

---

## 8. 从源码运行

```bash
# 终端 1：Core 引擎（前台运行，Ctrl+C 优雅退出）
python -m engine run

# 终端 2：Control API + GUI
python -m server run
```

打开 <http://127.0.0.1:8000/>。Linux/macOS 可用 `utils/quick/` 一键拉起两个进程并打开界面：

```bash
bash utils/quick/linux-run.sh
./utils/quick/mac-run.command
```

`utils/quick/` 只是本地 GUI 的便利脚本。无界面场景请分别启动：

- **只用 CLI：** 只启动引擎（`python -m engine run`）即可；CLI 走本地命令通道，不需要 API 进程。
- **需要 GUI / HTTP API：** 同时启动 `python -m engine run` 与 `python -m server run`。

- 引擎默认监听 `127.0.0.1:39300`，被占用时顺延；实际端口与 token 写入 `run/engine.json`。
- API 端口被占用时会自动顺延并打印警告；加 `--strict-port` 可固定端口。
- 引擎是**单实例**：第二个 `python -m engine run` 会立即退出（返回码 2）。
- 健康检查：`python -m engine status`、`curl -s http://127.0.0.1:8000/fcgi-bin/api/status`。

CLI 是 Core 的客户端：`python fcgi-bin/cli.py add -i book.txt ...` 会一次完成上传、解析与排队生成。

---

## 9. GUI 构建（仅开发）

发布版在仓库根目录提供打包好的单文件 `index.html`。要改前端：

```bash
cd gui
npm install
npm run dev      # Vite 开发服务器，把 /fcgi-bin 代理到 API
npm run build    # 生成单文件 ../index.html
```

> **Windows + 网络共享**：`vite build` 依赖 rollup 原生模块，在 SMB/UNC 路径上会失败。
> 请在本地磁盘构建，再把生成的 `index.html` 复制回去。

如果 `npm run build` 报 Vite 可执行文件缺失（例如复制目录后权限丢失），可用：

```bash
node ./node_modules/vite/bin/vite.js build
```

---

## 10. 测试

```bash
# 单元测试（无需服务）
python -m pytest tests/unit -q

# 全部测试；集成测试在 API/引擎不可达时会自动跳过
python -m pytest tests

# 单个文件
python -m pytest tests/unit/test_api_v2.py -v
```

- 单元测试在 `tests/unit/`；集成测试在 `tests/integration/`。
- 标记：`unit`、`integration`、`slow`。
- 改动 API 契约时必须同步更新 `tests/unit/test_api_v2.py` 与 [API 参考](api.md)。

---

## 11. 故障排查

**`python -m engine run` 立即退出并返回 2？**
已有实例在运行（单实例锁）。用 `python -m engine status` 查看，或先停掉。

**API 返回 503 + code 3004？**
引擎未运行，或端口/token 不匹配。先启动引擎；API 从 `run/engine.json` 读取地址。

**数据库完整性 / WAL 警告？**
运行 `python -m engine doctor` 检查 `tasks.db` 完整性。`data/` 请放在本地磁盘；SQLite WAL 在
SMB 网络盘上不可靠。

**音色试听没有声音？**
试听使用 Edge TTS，需要联网；每个音色首次合成需要几秒（缓存在 `cache/tts/preview/`）。

**GUI 开发服务器连不上 API？**
检查 `gui/vite.config.*` 的代理配置，以及 `python -m server run` 是否监听在配置的端口。

---

## 下一步

- [开发者指南](developer-guide.md)：全局契约、模块边界、配置项、i18n、测试
- [API 参考](api.md)
- [部署与运维](deployment.md)
- [设计规格](design/README.md)
