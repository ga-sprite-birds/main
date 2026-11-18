# 部署与运维

v2 是**两个进程**：

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

---

## 1. 手动启动（开发/单机）

```bash
# 终端 1：Core 引擎（前台运行，Ctrl+C 优雅退出）
python -m engine run

# 终端 2：Control API
python -m server run

# 另开终端做健康检查
python -m engine status          # pid / port / 任务计数
python -m engine doctor --json   # 目录、权限、DB、ffmpeg、端口自检
curl -s http://127.0.0.1:8000/fcgi-bin/api/status
```

引擎默认监听 `127.0.0.1:39300`，被占用时顺延，实际端口写在 `run/engine.json`。
API 默认 `127.0.0.1:8000`，由 `.env` 的 `API_HOST` / `API_PORT` 决定。

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

## 2. systemd

```bash
sudo useradd --system --create-home --home-dir /opt/ga-sprite-birds gasprite
sudo cp -r . /opt/ga-sprite-birds
# 单元模板统一在 scripts/systemd/（system 变体已内置加固项）
sudo cp scripts/systemd/ga-sprite-birds-core.system.service /etc/systemd/system/ga-sprite-birds-core.service
sudo cp scripts/systemd/ga-sprite-birds-api.system.service  /etc/systemd/system/ga-sprite-birds-api.service
# 先按需修改 unit 内的 User/Group/WorkingDirectory/ExecStart
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

### 升级与回滚

```bash
# 升级：先停 API（前端 503），再停 Core（当前章节跑完后退出），替换代码，再按序启动
sudo systemctl stop ga-sprite-birds-api
sudo systemctl stop ga-sprite-birds-core     # 等满 TimeoutStopSec 才强杀
sudo -u gasprite git -C /opt/ga-sprite-birds pull
sudo systemctl start ga-sprite-birds-core
sudo systemctl start ga-sprite-birds-api
```

`data/tasks.db` 迁移随代码走：引擎启动时执行版本化迁移（`engine/migrations/`），
升级只前进不后退；回滚代码前请先备份 `data/` 与 `cache/config/system.json`。

---

## 3. 路径与权限

| 路径 | 写入者 | 说明 |
|------|--------|------|
| `data/tasks.db` | 仅 Core | 任务、章节、事件、命令幂等日志；WAL |
| `data/system.db` | 初始化/迁移 | 配置默认值（只读挂载给 API 也够用） |
| `cache/config/system.json` | API / Core（原子替换） | 用户覆盖值；两边按文件签名自动重载 |
| `run/engine.json` | Core | 发现文件（host/port/token/pid），权限 `0600` |
| `run/engine.lock` | Core | 单实例锁 |
| `uploads/` | API | 上传源文件 |
| `output/` | Core | 生成的音频与章节文本 |
| `logs/` | 两者 | 分文件滚动日志 |

`run/engine.json` 内含 Bearer token（`0600`，仅属主可读）。这与早期契约文档里
「发现文件不含凭证」的表述冲突，v2 选择把 token 直接写进该文件，理由：命令通道只绑定
`127.0.0.1`，token 的寿命与进程一致，拆文件反而多一处同步失败点。若所在环境要求凭证与
发现信息分离，把 `token` 字段搬到 `run/engine.token`（同样 `0600`）即可，客户端只需改
`engine/runtime.py` 的读取函数。

---

## 4. 反向代理（可选）

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

---

## 5. Docker

仓库自带 `Dockerfile` + `docker-compose.yml`，在一个容器内同时运行 Core 引擎与 Control API（共享 loopback，API 可访问引擎命令通道）。

```bash
cp .env.example .env          # 配置 LLM 凭据
docker compose up -d --build
# GUI: http://127.0.0.1:8000/
docker compose logs -f
docker compose down
```

- 持久化：`./data ./run ./cache ./output ./logs ./uploads`（bind mount）。
- 容器内 `API_HOST=0.0.0.0`；默认映射宿主机 `8000`，可用 `API_HOST_PORT=18080 docker compose up -d` 改端口；引擎命令通道 `127.0.0.1:39300` 不暴露。
- `models/` 是镜像内的 Python 代码包；模型缓存写到 `./cache/models`。
- Docker 与宿主机引擎**不能同时共用** `data/`、`run/`（单实例锁）：切换前先停宿主机 `engine`/`server`，或在独立目录运行 compose。
- 需要水平拆分时，可改成 engine / api 两个服务，并用 `network_mode: service:engine` 让 API 共享引擎的 loopback。

> 服务器部署以 **venv** 为主；conda 是开发环境，不作为服务器运行时。
