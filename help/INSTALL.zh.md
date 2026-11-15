# GA Sprite Birds — 安装指南

> 适用于 v2（Core 引擎 + 轻薄 Control API，两个进程）。English version: [INSTALL.md](INSTALL.md)
> 日常使用见：[README.zh.md](README.zh.md)。

本文顺序：**1) 运行环境 → 2) 初始安装 → 3) 部署方式（本地 / API）→ 4) GUI 构建 → 5) 故障排查**。

---

## 1. 运行环境

| 项目 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows 10+ / macOS 10.15+ / Linux | |
| Python | 3.10+ | |
| FFmpeg | **必需** | MP3 导出 / 音频合并 |
| Node.js | 可选 | 仅自行构建前端时需要 |
| 内存 | 最低 4GB；用本地 LLM 建议 16GB+ | 纯在线 API 模式占用很低 |
| 磁盘 | ~1GB + 生成的音频 | 含依赖与缓存 |
| 网络 | Edge TTS / 在线 LLM 需要 | 本地 Ollama 可离线 |

---

## 2. 初始安装

### 2.1 获取代码

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
```

### 2.2 创建 Python 环境

**venv（通用）**

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -U pip setuptools wheel
pip install -r requirements.txt
```

**Conda**

```bash
conda env create -f environment.yml
conda activate ga-sprite-birds
pip install -r requirements.txt
```

### 2.3 安装 FFmpeg

- **Windows**：从 <https://ffmpeg.org/download.html> 下载并加入 `PATH`，或在 `.env` 设置 `FFMPEG_PATH`
- **macOS**：`brew install ffmpeg`
- **Debian/Ubuntu**：`sudo apt install ffmpeg`

用 `ffmpeg -version` 验证。

### 2.4（可选）安装 Ollama 以使用本地 LLM

只有"不用在线 API 也要 LLM 口语化"时才需要：

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:7b      # 默认本地模型，可在 .env 修改
```

Windows / macOS 安装包：<https://ollama.com/download>。也可以完全跳过本地模型，改用任意 OpenAI 兼容接口（`LLM_MODE=api`，见下）。

### 2.5 配置 `.env`

```bash
cp .env.example .env
```

`.env` **只放部署设置与凭据**：

| 变量 | 默认 | 用途 |
|---|---|---|
| `LLM_MODE` | `local` | `local`（Ollama）或 `api`（OpenAI 兼容） |
| `LLM_API_ENDPOINT` / `LLM_API_KEY` / `LLM_API_MODEL` | — | `api` 模式的端点、密钥、模型 |
| `LLM_LOCAL_HOST` / `LLM_LOCAL_MODEL` | `http://localhost:11434` / `deepseek-r1:7b` | 本地 Ollama |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Control API 绑定地址 |
| `TASK_MAX_CONCURRENT` | `2` | 引擎并发任务数 |
| `TASK_RESULT_TTL` | `86400` | 终态任务记录保留秒数；`0` 表示永久 |
| `FFMPEG_PATH` | 空 | FFmpeg 目录；空则用系统 `PATH` |
| `LOG_LEVEL` / `LOG_FILE` | `INFO` / `./logs/app.log` | 日志 |

> **业务配置不在 `.env` 里。** 语言、音色、语速、章节规则、输出策略来自 `data/system.db`（默认值）+ `cache/config/system.json`（用户覆盖）。请在 GUI 的**系统配置**页或 `python fcgi-bin/cli.py config set …` 修改；对之后新启动的任务立即生效，无需重启。

### 2.6 验证安装

```bash
python -m engine doctor --json   # 检查目录、权限、数据库、ffmpeg、端口
```

`doctor` 会检查 data/run/cache 目录可写、SQLite 正常、FFmpeg 可执行、默认端口可用。

---

## 3. 部署方式

v2 始终是**两个进程**：Core 引擎（唯一执行者、任务状态唯一写者）与 Control API（托管 GUI 与端点）。下面两种部署方式只是进程的托管方式不同，功能完全一致。

### 3.1 本地部署（个人机器 / 开发）

每个进程一个终端：

```bash
# 终端 1：Core 引擎（前台；Ctrl+C 优雅停止）
python -m engine run

# 终端 2：Control API（同时托管 GUI）
python fcgi-bin/api.py
```

打开 <http://127.0.0.1:8000/>。健康检查：

```bash
python -m engine status                      # PID / 端口 / 任务计数
curl -s http://127.0.0.1:8000/fcgi-bin/api/status
```

- 引擎默认监听 `127.0.0.1:39300`，端口被占用会顺延；实际端口与 token 写入 `run/engine.json`。
- 引擎是**单实例**：再执行一次 `python -m engine run` 会立即退出（退出码 2）。
- 临时后台运行（仅调试）：`nohup python -m engine run > logs/engine.log 2>&1 &`。

### 3.2 API 部署（长期运行 / 对外提供 HTTP API）

API **没有内置鉴权** —— 请绑定回环/内网地址，对外时在前面加 Nginx 或内部网关。**切勿**暴露引擎命令通道 `127.0.0.1:39300`。

**Linux — systemd（推荐）。** unit 模板在 [`scripts/systemd/`](../scripts/systemd/)：
`ga-sprite-birds-core.{user,system}.service` 与 `ga-sprite-birds-api.{user,system}.service`。

用户级（无需 root；随登录会话启动）：

```bash
mkdir -p ~/.config/systemd/user
cp scripts/systemd/ga-sprite-birds-core.user.service ~/.config/systemd/user/ga-sprite-birds-core.service
cp scripts/systemd/ga-sprite-birds-api.user.service  ~/.config/systemd/user/ga-sprite-birds-api.service
systemctl --user daemon-reload
systemctl --user enable --now ga-sprite-birds-core ga-sprite-birds-api

systemctl --user status ga-sprite-birds-core
journalctl --user -u ga-sprite-birds-core -f
```

登出后仍要常驻：`sudo loginctl enable-linger "$USER"`。

系统级（开机自启、与登录无关）：

```bash
sudo cp scripts/systemd/ga-sprite-birds-core.system.service /etc/systemd/system/ga-sprite-birds-core.service
sudo cp scripts/systemd/ga-sprite-birds-api.system.service  /etc/systemd/system/ga-sprite-birds-api.service
# 先按需修改 unit 内的 User/Group/WorkingDirectory/ExecStart
sudo systemctl daemon-reload
sudo systemctl enable --now ga-sprite-birds-core ga-sprite-birds-api

systemctl status ga-sprite-birds-core
journalctl -u ga-sprite-birds-core -f
```

unit 会失败自动重启（`Restart=on-failure`），并优雅停止（当前章节先完成并 checkpoint）。目录权限、反向代理、升级回滚见 [docs/deploy/README.md](../docs/deploy/README.md)。

**Windows — NSSM**（保留工作目录、崩溃重启）：

```powershell
nssm install GASpriteBirds-Core "C:\path\to\python.exe" "-m engine run"
nssm set GASpriteBirds-Core AppDirectory "C:\path\to\repo"
nssm install GASpriteBirds-API "C:\path\to\python.exe" "fcgi-bin/api.py"
nssm set GASpriteBirds-API AppDirectory "C:\path\to\repo"
nssm start GASpriteBirds-Core; nssm start GASpriteBirds-API
```

---

## 4. GUI 构建（仅开发用）

发布版已在仓库根目录提供打包好的单文件 `index.html`。要改前端：

```bash
cd gui
npm install
npm run dev      # Vite 开发服务器 :5173，/fcgi-bin 代理到 API
npm run build    # 输出单文件 ../index.html
```

> **Windows + 网络共享盘**：`vite build` 会加载 rollup 原生模块，在 SMB/UNC 路径上会失败。请在本地区盘构建，再把 `index.html` 拷回共享盘。

---

## 5. 故障排查

**`python -m engine run` 立即退出、码 2？**
已有实例在运行（单实例锁）。用 `python -m engine status` 查看，或先停止它。

**API 返回 503 / code 3004？**
引擎未运行，或端口/token 不匹配。先启动引擎；API 从 `run/engine.json` 读取地址。

**数据库完整性 / WAL 告警？**
用 `python -m engine doctor` 检查 `tasks.db` 完整性。`data/` 尽量放本地磁盘；SQLite WAL 在 SMB 网络盘上不可靠。

**音色试听没声音？**
试听走 Edge TTS，需要联网；每个音色首次合成需几秒（缓存在 `cache/tts/preview/`）。

**如何跑测试？**

```bash
python -m pytest tests    # 引擎不可达时集成测试自动跳过
```

---

## 下一步

- 使用说明：[中文 README](README.zh.md) · [English README](../README.md)
- API 端点：[docs/api.md](../docs/api.md)
- 运维细节：[docs/deploy/README.md](../docs/deploy/README.md)
