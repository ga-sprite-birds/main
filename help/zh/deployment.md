# 部署与运维

> English version：[../en/deployment.md](../en/deployment.md) · 使用指南：[README.md](README.md) · 开发文档：[development.md](development.md)

v2 始终由**两个进程**组成：

```
┌──────────────────────────┐        localhost HTTP + Bearer token
│  Core 引擎 (engine)      │◀──────────────────────────────┐
│  · 唯一执行者            │                               │
│  · 唯一写 data/tasks.db  │                               │
│  · 单实例锁 run/engine.lock                             │
│  · 发现文件 run/engine.json (0600)                      │
└──────────────────────────┘                               │
                                                           │
┌──────────────────────────┐       只读 data/tasks.db      │
│  Control API (api.py)    │───────────────────────────────┘
│  · 收上传、转发命令      │
│  · 只读查询任务状态      │
│  · 托管 GUI 与系统配置页  │
└──────────────────────────┘
```

关闭 API 不影响引擎继续跑任务；重启引擎后 `running` 任务会从最后一个成功章节续跑，
`paused` 任务保持暂停等人工 `resume`。

> 生产部署可选 **Docker（推荐）** 与 **venv（原生）**。conda 只用于开发环境（见[开发文档](development.md)）。

---

## 1. Docker（推荐）

仓库自带 `Dockerfile` + `docker-compose.yml`，在一个容器内同时运行 Core 引擎与 Control API
（共享 loopback，API 可访问引擎命令通道）。

```bash
cp .env.example .env          # 配置 LLM 凭据
mkdir -p data run cache output logs uploads
sudo chown -R 1000:1000 data run cache output logs uploads
docker compose up -d --build
# GUI: http://127.0.0.1:8000/
docker compose logs -f
docker compose down
```

- 持久化：`./data ./run ./cache ./output ./logs ./uploads`（bind mount）。
- 容器内 `API_HOST=0.0.0.0`；compose 默认只发布到 **127.0.0.1**。可用
  `API_HOST_PORT=18080 docker compose up -d --build` 改端口。
- 局域网访问需同时设置 `API_BIND_HOST=0.0.0.0` 并启用鉴权：
  ```env
  API_BIND_HOST=0.0.0.0
  API_AUTH_ENABLED=true
  API_AUTH_TOKEN=<长随机令牌>
  ```
  客户端使用 `Authorization: Bearer <token>`；GUI 顶部钥匙按钮可保存令牌。
- CORS 默认关闭。独立前端来源需要时再设置 `API_CORS_ENABLED=true` 和明确的
  `API_CORS_ORIGINS`，不要使用 `*`。
- 引擎命令通道 `127.0.0.1:39300` 不暴露。
- 镜像以非 root 的 `app` 用户运行（默认 UID/GID `1000:1000`）。首次启动前，把宿主机绑定目录
  改成该用户可写：
  ```bash
  mkdir -p data run cache output logs uploads
  sudo chown -R 1000:1000 data run cache output logs uploads
  ```
  如果宿主机用户 UID/GID 不同，在 `.env` 设置 `APP_UID`/`APP_GID` 后重新执行
  `docker compose up -d --build`；compose 会把它们作为构建参数传入。
- Docker daemon 本身通常以 root 运行；容器内进程不是 root。若还想隔离 daemon，可使用
  rootless Docker。
- compose 丢弃全部 Linux capabilities 并启用 `no-new-privileges`；运行时文件为 `0600`，
  卷目录为 `0700`。
- `models/` 是镜像内的 Python 代码包；模型缓存写到 `./cache/models`。
- Docker 与宿主机引擎**不能同时共用** `data/`、`run/`（单实例锁）：切换前先停宿主机
  `engine`/`server`，或在独立目录运行 compose。
- 宿主机不需要 Python 或 FFmpeg，二者都在镜像内。
- 需要水平拆分时，可改成 engine / api 两个服务，并用 `network_mode: service:engine`
  让 API 共享引擎的 loopback。

---

## 2. venv（原生）

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env

# 终端 1：Core 引擎（前台运行，Ctrl+C 优雅退出）
python -m engine run

# 终端 2：Control API + GUI
python -m server run
```

**只用 CLI 时，`python -m server run` 是可选的**：CLI 直接通过本地命令通道与引擎通信。
不需要 GUI / HTTP API 时只启动 `python -m engine run`；需要时再同时启动两个进程。

API 鉴权可选；但绑定到 loopback 之外时必须启用。在 `.env` 设置
`API_AUTH_ENABLED=true` + `API_AUTH_TOKEN`；客户端使用 `Authorization: Bearer <token>`，
GUI 顶部钥匙按钮会把令牌保存在浏览器。

先安装 FFmpeg（`apt install ffmpeg`、`brew install ffmpeg` 或 Windows 构建），用
`ffmpeg -version` 验证；也可以设置 `FFMPEG_PATH`。

健康检查：

```bash
python -m engine status          # pid / 端口 / 任务计数
python -m engine doctor --json   # 目录、权限、tasks.db、ffmpeg、发现文件
curl -s http://127.0.0.1:8000/fcgi-bin/api/status
```

引擎默认监听 `127.0.0.1:39300`，被占用时顺延，实际端口写入 `run/engine.json`。
API 默认 `127.0.0.1:8000`，由 `.env` 的 `API_HOST` / `API_PORT` 决定；未加
`--strict-port` 时会自动顺延到空闲端口。

### 日常运维命令

```bash
# 引擎状态与自检
python -m engine status
python -m engine doctor

# CLI 与 API 对等：命令都经由引擎执行
python fcgi-bin/cli.py list --status running
python fcgi-bin/cli.py status <task_id>
python fcgi-bin/cli.py pause <task_id>
python fcgi-bin/cli.py resume <task_id>
python fcgi-bin/cli.py cancel <task_id>
python fcgi-bin/cli.py remove <task_id> --delete-outputs
python fcgi-bin/cli.py events <task_id> --follow
python fcgi-bin/cli.py clean --ttl-seconds 86400 --dry-run

# 系统配置（与 GUI 同一套 ConfigService）
python fcgi-bin/cli.py config get TTS_VOICE
python fcgi-bin/cli.py config set TTS_RATE 1.15
python fcgi-bin/cli.py system info
```

---

## 3. systemd

单元模板在 [`scripts/systemd/`](../../scripts/systemd/)：
`ga-sprite-birds-core.{user,system}.service` 与 `ga-sprite-birds-api.{user,system}.service`。
system 变体带加固项，默认假定安装在 `/opt/ga-sprite-birds` 且使用 `.venv`。

用户级（无需 root，跟随登录会话启动）：

```bash
mkdir -p ~/.config/systemd/user
cp scripts/systemd/ga-sprite-birds-core.user.service ~/.config/systemd/user/ga-sprite-birds-core.service
cp scripts/systemd/ga-sprite-birds-api.user.service  ~/.config/systemd/user/ga-sprite-birds-api.service
systemctl --user daemon-reload
systemctl --user enable --now ga-sprite-birds-core ga-sprite-birds-api
```

退出登录后仍保持运行：`sudo loginctl enable-linger "$USER"`。

系统级（开机启动，不依赖登录）：

```bash
sudo useradd --system --create-home --home-dir /opt/ga-sprite-birds gasprite
sudo cp -r . /opt/ga-sprite-birds
# 先按需修改 unit 内的 User/Group/WorkingDirectory/ExecStart
sudo cp scripts/systemd/ga-sprite-birds-core.system.service /etc/systemd/system/ga-sprite-birds-core.service
sudo cp scripts/systemd/ga-sprite-birds-api.system.service  /etc/systemd/system/ga-sprite-birds-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now ga-sprite-birds-core ga-sprite-birds-api
```

查看与排障：

```bash
systemctl status ga-sprite-birds-core
journalctl -u ga-sprite-birds-core -f
journalctl -u ga-sprite-birds-api -f
```

单实例保护：两个 Core 抢同一份 `run/engine.lock` 时，后启动的进程直接退出并返回码 `2`，
不会出现双写 `tasks.db`。

### 3.1 Windows — NSSM

```powershell
nssm install GASpriteBirds-Core "C:\path\to\repo\.venv\Scripts\python.exe" "-m engine run"
nssm set GASpriteBirds-Core AppDirectory "C:\path\to\repo"
nssm install GASpriteBirds-API "C:\path\to\repo\.venv\Scripts\python.exe" "-m server run --strict-port"
nssm set GASpriteBirds-API AppDirectory "C:\path\to\repo"
nssm start GASpriteBirds-Core; nssm start GASpriteBirds-API
```

### 3.2 升级与回滚

```bash
# 升级：先停 API（前端 503），再停 Core（当前章节跑完后退出），替换代码，再按序启动
sudo systemctl stop ga-sprite-birds-api
sudo systemctl stop ga-sprite-birds-core     # 等满 TimeoutStopSec 才强杀
sudo -u gasprite git -C /opt/ga-sprite-birds pull
sudo systemctl start ga-sprite-birds-core
sudo systemctl start ga-sprite-birds-api
```

`data/tasks.db` 迁移随代码走：引擎启动时执行版本化迁移（`engine/migrations/`），升级只前进不后退。
回滚代码前请先备份 `data/` 与 `cache/config/system.json`。

---

## 4. 路径与权限

| 路径 | 写入者 | 说明 |
|------|--------|------|
| `data/tasks.db` | 仅 Core | 任务、章节、事件、命令幂等日志；WAL；权限 `0600` |
| `data/system.db` | Core/API 种子 + 迁移 | 配置默认值；两个进程首次启动都会补齐缺失键；权限 `0600` |
| `cache/config/system.json` | API / Core（原子替换） | 用户覆盖值；两边按文件签名自动重载 |
| `run/engine.json` | Core | 发现文件（host/port/token/pid），权限 `0600` |
| `run/engine.lock` | Core | 单实例锁 |
| `uploads/` | API | 上传源文件（目录 `0700`，文件 `0600`） |
| `output/` | Core | 生成的音频与章节文本 |
| `logs/` | 两者 | 分文件滚动日志 |

`run/engine.json` 内含 Bearer token（`0600`，仅属主可读）。这与早期契约文档里
「发现文件不含凭证」的表述冲突，v2 选择把 token 直接写进该文件，理由：命令通道只绑定
`127.0.0.1`，token 的寿命与进程一致，拆文件反而多一处同步失败点。若所在环境要求凭证与
发现信息分离，把 `token` 字段搬到 `run/engine.token`（同样 `0600`）即可，客户端只需改
`engine/runtime.py` 的读取函数。

---

## 5. 反向代理（可选）

GUI 与 API 同源，反代只需透传：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_read_timeout 600s;   # 大文件上传
    client_max_body_size 100m; # 与 API_MAX_UPLOAD_SIZE 对齐
}
```

**不要**把 `127.0.0.1:39300`（引擎命令通道）暴露出去。
