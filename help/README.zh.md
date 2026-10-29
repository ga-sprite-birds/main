# GA Sprite Birds

> 将书籍或长文本按章节转换为语音，支持 Edge TTS、可选的 LLM 口语化，以及本地 Web 界面。

GA Sprite Birds 会把文本拆分为章节，可选地把书面语改写为自然口语，然后为每一章生成一个 MP3。项目提供 Web 界面、CLI 和本地 FastAPI 服务。单角色配音支持界面、CLI 和 API；多角色配音目前仅支持 CLI。

---

## 功能

| 功能 | 说明 | 界面 | CLI | API |
|------|------|:---:|:---:|:---:|
| **单角色配音** | 整本书使用同一个音色 | ✅ | ✅ | ✅ |
| **多角色配音** | 识别对话并为不同角色分配音色 | ❌ | ✅ | ❌ |
| **角色分析** | 提取角色并生成配音模板 | ❌ | ✅ | ❌ |
| **LLM 口语化** | 将书面语改写为自然口语 | ✅ | ✅ | ✅ |
| **章节拆分** | 自动识别章节标题并逐章生成 | ✅ | ✅ | ✅ |
| **章节选择** | 只生成勾选的章节 | ✅ | ✅ | ✅ |
| **标点停顿** | 按句插入停顿，可选轻微语气 | ✅ | ✅ | ✅ |
| **暂停 / 继续** | 当前章节完成后暂停，之后继续剩余章节 | ✅ | ❌ | ✅ |
| **任务持久化** | 服务重启后恢复暂停或中断的任务 | ✅ | — | ✅ |
| **多语言界面** | 中文 / English | ✅ | ✅ | ✅ |
| **TTS 试听工具** | 浏览并试听 Edge TTS 音色 | ❌ | ✅ | ❌ |

**输入格式：** `.txt`、`.md`、`.pdf`
**输出格式：** `.mp3`
**TTS 引擎：** Edge TTS（免费、无需 API Key，但需要联网）
**LLM 后端：** Ollama（本地）或任意 OpenAI 兼容接口

---

## 快速开始

### 1. 安装

需要 Python 3.10+ 和 FFmpeg。

```bash
git clone https://github.com/ga-sprite-birds/main.git
cd main

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Debian/Ubuntu 示例
sudo apt install ffmpeg
```

也可以使用 Conda：

```bash
conda env create -f environment.yml
conda activate ga-sprite-birds
```

### 2. 配置

```bash
cp .env.example .env
```

默认使用 Edge TTS 并启用 LLM。使用本地模型：

```env
LLM_MODE=local
LLM_LOCAL_HOST=http://localhost:11434
LLM_LOCAL_MODEL=deepseek-r1:7b
```

使用 OpenAI 兼容接口：

```env
LLM_MODE=api
LLM_API_TYPE=openai
LLM_API_ENDPOINT=https://api.deepseek.com/v1
LLM_API_KEY=your_api_key_here
LLM_API_MODEL=deepseek-chat
```

更多选项见[配置说明](#配置)。

### 3. 启动

**Web 界面 + 本地 API**

```bash
bash api.sh
```

脚本会启动 FastAPI，从 `API_PORT`（默认 `8000`）开始寻找空闲端口，并打开 `http://127.0.0.1:<端口>/`。接口文档位于 `/docs`。

**CLI**

```bash
bash cli.sh -i input.txt
```

**界面源码开发**

仓库根目录已包含构建好的界面。修改界面源码：

```bash
cd gui
npm install
npm run dev      # Vite 开发服务器 :5173
npm run build    # 生成 ../index.html
```

---

## 界面使用流程

1. 将 `.txt`、`.md` 或 `.pdf` 文件拖入上传区域，可一次添加多个文件。
2. 设置输出根目录、音色和停顿/语气模式，点击 **解析**。
3. 勾选要生成的章节（默认全选），点击 **开始**。
4. **暂停**会等当前章节完成后停止；**继续**会生成剩余选中的章节。
5. 已完成的章节可以直接试听或下载。**清空任务**会在确认后删除所有章节音频、章节文本、解析列表和任务记录；已上传的源文件会保留，重新开始需再次上传。

浏览器只保留最近一个任务。任务记录保存在 `cache/tasks/`，任务完成后自动删除。

---

## CLI 使用

### 单角色

```bash
# 基础用法
bash cli.sh -i input.txt

# 指定音色和语速（0.5-2.0）
bash cli.sh -i input.txt --voice zh-CN-YunxiNeural --rate 1.2

# 按标点停顿；prosody 还会轻微调整问句/感叹句/省略号
bash cli.sh -i input.txt --prosody pause

# 关闭 LLM 口语化（更快）
bash cli.sh -i input.txt --no-llm

# 只生成第 1-5 章
bash cli.sh -i input.txt --start 1 --end 5

# 指定输出目录
bash cli.sh -i input.txt -o ./my_output

# 英文界面
bash cli.sh -i input.txt --language en_US
```

CLI 会读取 `.env` 中的 `ENABLE_MULTI_VOICE`。如果它为 `true`，单角色生成需要显式传入 `--multi-voice false`。`--prosody` 同样适用于多角色输出。

### 多角色

多角色是仅 CLI 支持的两步流程。

**第一步：角色分析**

```bash
bash cli.sh -i novel.txt --analyze-characters

# 使用自定义角色列表的混合模式
bash cli.sh -i novel.txt --analyze-characters \
  --analysis-mode hybrid \
  --character-list characters.txt
```

`characters.txt` 示例：

```text
张三 male
李四 female
王五
```

分析结果会写入类似 `cache/role/novel_characters.json` 的模板文件。

**第二步：生成**

```bash
# 使用自动生成的模板
bash cli.sh -i novel.txt --multi-voice true

# 指定模板并只生成第 1-3 章
bash cli.sh -i novel.txt --multi-voice true \
  --character-template cache/role/custom_characters.json \
  --start 1 --end 3
```

多角色输出会在每个 MP3 旁生成一个 `.txt`，记录对白和音色分配。

### TTS 试听

```bash
# 列出中文音色
python utils/try_tts/cli.py list --lang zh-CN

# 为所有中文音色生成试听
python utils/try_tts/cli.py generate --lang zh-CN

# 用自定义文本试听一个音色
python utils/try_tts/cli.py generate \
  --voice zh-CN-XiaoxiaoNeural \
  --text "这是我的试听文本"
```

试听文件输出到 `output/tts_samples/`。

---

## API 使用

使用 `bash api.sh` 启动，或直接运行：

```bash
PYTHONPATH=. python fcgi-bin/api.py
```

API 仅面向本地使用，没有鉴权。不要直接暴露到公网。以下示例使用 `8000` 端口；如果 `api.sh` 自动切换了端口，请替换为实际端口。

### 1. 上传

`file`、`path`、`output_path`、`language` 都是查询参数；文件本身使用 multipart 表单上传。`output_path` 是输出根目录，系统会自动追加源文件名作为子目录。

```bash
# 上传文件
curl -X POST "http://localhost:8000/upload?output_path=./my_output" \
  -F "file=@input.txt"

# 或指定服务器上已有的文件
curl -X POST "http://localhost:8000/upload?path=/absolute/path/input.txt"
```

返回：

```json
{"task_id":"<id>","status":"pending","message":"文件上传成功，任务 ID: <id>"}
```

上传大小受 `API_MAX_UPLOAD_SIZE` 限制（单位 MB，默认 `100`）。文件保存在 `API_UPLOAD_DIR`，并自动添加唯一前缀。

### 2. 解析

```bash
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<id>","language":"zh_CN"}'
```

### 3. 生成

```bash
# 生成全部章节
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<id>","voice":"zh-CN-YunxiNeural","enable_llm":true}'

# 只生成指定章节，并设置语速
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<id>",
    "chapter_indexes": [1, 2, 5],
    "rate": 1.2,
    "prosody_mode": "prosody",
    "enable_llm": false
  }'
```

传入 `chapter_indexes` 时，必须是非空且存在的章节序号列表；省略表示全部章节。`enable_llm` 默认读取 `.env` 中的 `ENABLE_LLM`；`rate` 必须在 `0.5` 到 `2.0` 之间。`prosody_mode` 可选 `off`（默认）、`pause` 或 `prosody`；省略时读取 `.env` 中的 `TTS_PROSODY_MODE`。

API 只支持单角色配音。多角色配音请使用 CLI。

### 4. 状态、暂停、继续、清空

```bash
# 任务进度和每章状态
curl "http://localhost:8000/task/<id>/status"

# 当前章节完成后暂停
curl -X POST "http://localhost:8000/task/<id>/pause"

# 继续生成剩余章节（沿用保存的章节范围）
curl -X POST "http://localhost:8000/task/<id>/resume"

# 下载某一章
curl "http://localhost:8000/task/<id>/chapter/1" --output chapter_1.mp3

# 清空整个任务：解析列表、所有音频和任务记录
curl -X DELETE "http://localhost:8000/task/<id>"

# 可选：只删除某一章的音频和章节文本
curl -X DELETE "http://localhost:8000/task/<id>/chapter/1"

# API 默认配置和健康状态
curl "http://localhost:8000/api/status"
```

暂停会先完成当前章节。选中范围内尚未生成的章节会标记为 `paused`，继续时按待生成处理。任务参数和章节范围都会持久化，因此服务重启后仍可继续暂停的任务。清空任务会删除解析列表、所有生成音频和任务记录；已上传的源文件会保留。

### 输出目录

每个源文件都会在输出根目录下创建独立目录，目录名使用源文件名（不含扩展名）。默认 `OUTPUT_STRATEGY=by_role`：

```text
output/
└── 示例书名/
    ├── 001-第一章.mp3
    ├── 001-第一章.txt
    ├── 002-第二章.mp3
    └── ...
```

自定义输出根目录 `abc` 时，系统仍会自动追加源文件名：`abc/示例书名/`。多角色输出使用 `abc/示例书名/multi/`。

标题匹配 `OUTPUT_FRONT_MATTER_MARKERS`（默认 `导读,前言`）的前置章节会使用 `000` 前缀并命名为 `<前缀>篇`；后续章节序号不重排。

---

## 配置

复制 `.env.example` 为 `.env`。常用配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LANGUAGE` | `en_US` | 默认界面/API 语言（`en_US` 或 `zh_CN`） |
| `ENABLE_LLM` | `true` | 是否默认启用 LLM 口语化 |
| `LLM_MODE` | `local` | `local`（Ollama）或 `api`（OpenAI 兼容） |
| `TTS_VOICE` | `zh-CN-YunxiNeural` | 默认 Edge TTS 音色 |
| `TTS_RATE` | `1.0` | 默认语速 |
| `TTS_CHUNK_MAX_CHARS` | `2000` | 长章节按句子边界切块 |
| `TTS_CHUNK_TIMEOUT` | `180` | 单个 TTS 分块超时（秒） |
| `TTS_PROSODY_MODE` | `off` | `off`、`pause` 或 `prosody` |
| `TTS_PROSODY_MAX_UNIT_CHARS` | `120` | 每个停顿单元的最大字符数；越小请求越多 |
| `OUTPUT_BASE_PATH` | `./output` | 输出根目录；会自动追加源文件名子目录 |
| `OUTPUT_FRONT_MATTER_MARKERS` | `导读,前言` | 前置章节标题前缀，逗号分隔；留空可关闭 000 规则 |
| `OUTPUT_DUPLICATE_HANDLING` | `rename` | `skip`、`rename` 或 `overwrite` |
| `OUTPUT_STRATEGY` | `by_role` | `by_role`、`by_model`、`by_date` 或平铺 |
| `CHAPTER_NORMALIZE_ENABLED` | `true` | 规范化 Markdown/加粗章节标题 |
| `API_MAX_UPLOAD_SIZE` | `100` | 上传大小限制（MB，`0` 表示不限制） |
| `API_UPLOAD_DIR` | `./uploads` | 上传文件目录 |
| `TASK_CACHE_DIR` | `./cache/tasks` | 任务记录目录 |
| `TASK_RESULT_TTL` | `86400` | 非完成任务记录保留时间（秒，`0` 表示永不过期） |

`TTS_PROSODY_MAX_UNIT_CHARS=120` 与试听样例一致。生成整本长书时，可提高到 `200`-`300` 以减少 TTS 请求数，代价是句内停顿更少。

`OUTPUT_FORMAT` 和 `OUTPUT_BITRATE` 控制 MP3 导出参数；完整配置见 `config/__init__.py`。

---

## 项目结构

```text
fcgi-bin/            CLI 和 FastAPI 入口
ga_birds/
  Audio/             TTS 引擎、章节生成器、导出与合并
  Common/            配置、i18n、章节加载、文本保存
  LLM/               Ollama / OpenAI 客户端
  Parser/            章节解析器
  character_analyzer/ 多角色与对话分析
  Task/              任务管理与 JSON 持久化
  Utils/             文件、文本、重试、Token 工具
gui/                 Vue 3 + Element Plus 前端
help/                安装与开发文档
output/              生成的音频（已被 git 忽略）
uploads/             上传的源文件（已被 git 忽略）
cache/tasks/         任务记录（已被 git 忽略）
```

---

## 参考文档

- [开发指南](./help/development-guide.md)
- [安装指南](./help/INSTALL.md)
- [English README](../README.md)

---

**最后更新：** 2026-10-23  
**维护者：** GA Sprite Birds Development Team

**作者：** adam  
**邮箱：** dev@ebf.hk  
**网站：** http://ebf.cc  
**源码：** https://github.com/ga-sprite-birds/main
