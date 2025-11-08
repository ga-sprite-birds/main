# GA Sprite Birds - 音频朗读系统

> 将文本（txt/md/pdf）通过 LLM 处理后转换为音频（TTS），支持角色配音、情感朗读、章节拆分
>
> **版本**: v1.0
> **开发团队**: Tiger

## 📋 项目简介

**GA Sprite Birds** 是一个音频朗读系统，核心功能包括：

- ✅ 支持多种文本格式（txt, md, pdf）
- ✅ 自动章节拆分（正则表达式）
- ✅ LLM 文本口语化（本地 Ollama 或 API）
- ✅ TTS 音频生成（本地模型或 Edge TTS）
- ✅ 异步任务管理
- ✅ RESTful API 接口
- ✅ 每章独立生成，边生成边可播放

**目标用户**：个人阅读爱好者、有声小说创作者、私有化部署用户

---

## 🚀 快速开始

### 1. 环境准备

#### 创建 Conda 环境

```bash
# 方式 1：使用 environment.yml
conda env create -f environment.yml
conda activate ga-sprite-birds

# 方式 2：手动创建
conda create -n ga-sprite-birds python=3.10 -y
conda activate ga-sprite-birds
conda install -c conda-forge ffmpeg -y
pip install -r requirements.txt
```

#### 安装 Ollama（本地 LLM）

如果使用本地 LLM 模式，需要安装 Ollama：

```bash
# 下载并安装 Ollama
# https://ollama.ai/

# 拉取 DeepSeek R1 7B 模型
ollama pull deepseek-r1:7b
```

### 2. 配置文件

编辑 `config.yaml` 配置文件：

```yaml
# LLM 配置
llm:
  mode: local  # local 或 api
  local:
    host: http://localhost:11434
    model: deepseek-r1:7b

# TTS 配置
tts:
  mode: api  # local 或 api
  api:
    type: edge-tts  # 免费，推荐
    voice: zh-CN-XiaoxiaoNeural  # 中文女声

# 输出配置
output:
  base_path: ./output
  format: mp3
```

### 3. 运行测试

```bash
# 运行功能测试（不启动服务）
python run_test.py
```

### 4. 启动 API 服务

```bash
# 启动 FastAPI 服务
python fcgi-bin/index.py

# 或使用 uvicorn
uvicorn fcgi-bin.index:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问：
- API 文档：http://localhost:8000/docs
- 根路径：http://localhost:8000/

---

## 📖 API 使用说明

### 1. 上传文件

```bash
# 上传本地文件
curl -X POST "http://localhost:8000/upload" \
  -F "file=@test.txt"

# 或指定本地路径
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/file.txt"}'

# 返回示例
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "文件上传成功，任务 ID: 123e4567-e89b-12d3-a456-426614174000"
}
```

### 2. 解析章节

```bash
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "123e4567-e89b-12d3-a456-426614174000"}'

# 返回示例
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "parsed",
  "message": "解析完成，共 10 章"
}
```

### 3. 生成音频

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "voice": "zh-CN-XiaoxiaoNeural",
    "enable_llm": true
  }'

# 返回示例
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "generating",
  "message": "音频生成已开始，请通过 /task/{id}/status 查询进度"
}
```

### 4. 查询任务状态

```bash
curl "http://localhost:8000/task/123e4567-e89b-12d3-a456-426614174000/status"

# 返回示例
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "generating",
  "total_chapters": 10,
  "completed_chapters": 3,
  "progress": 0.3,
  "created_at": "2025-01-01T10:00:00",
  "started_at": "2025-01-01T10:01:00",
  "completed_at": null,
  "error": null
}
```

### 5. 下载单章音频

```bash
curl "http://localhost:8000/task/123e4567-e89b-12d3-a456-426614174000/chapter/1" \
  --output chapter_1.mp3
```

---

## 📁 项目结构

```
ga-sprite-mp3/
├── fcgi-bin/                 # API 层
│   └── index.py              # FastAPI 统一路由
│
├── ga_birds/                 # 核心模块
│   ├── Config/               # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── LLM/                  # LLM 处理
│   │   ├── __init__.py
│   │   └── manager.py
│   │
│   ├── Audio/                # 音频生成
│   │   ├── __init__.py
│   │   ├── tts_manager.py
│   │   └── audio_exporter.py
│   │
│   ├── Parser/               # 文本解析
│   │   ├── __init__.py
│   │   └── chapter_parser.py
│   │
│   ├── Task/                 # 任务管理
│   │   ├── __init__.py
│   │   └── task_manager.py
│   │
│   ├── Sprite/               # 角色管理
│   │   ├── __init__.py
│   │   └── sprite_manager.py
│   │
│   └── Utils/                # 工具函数
│       ├── __init__.py
│       └── file_utils.py
│
├── output/                   # 输出目录
├── models/                   # 模型目录
├── logs/                     # 日志目录
├── uploads/                  # 上传文件目录
│
├── config.yaml               # 配置文件
├── requirements.txt          # Python 依赖
├── environment.yml           # Conda 环境
├── run_test.py               # 测试入口
└── README.md                 # 项目说明
```

---

## 🎙️ TTS 模型推荐

### 推荐方案 1：Edge TTS（免费，推荐）

- ✅ 完全免费，无限制
- ✅ 中文支持好
- ✅ 无需安装模型
- ✅ 配置简单

**配置示例**：

```yaml
tts:
  mode: api
  api:
    type: edge-tts
    voice: zh-CN-XiaoxiaoNeural  # 女声
    # voice: zh-CN-YunxiNeural   # 男声
```

### 推荐方案 2：CosyVoice（本地，高质量）

- ✅ 阿里开源，免费
- ✅ 中文支持极佳
- ✅ 支持声音克隆
- ⚠️ 需要下载模型

**安装**：

```bash
pip install modelscope
pip install cosyvoice
```

**配置示例**：

```yaml
tts:
  mode: local
  local:
    engine: cosyvoice
    model_path: ./models/CosyVoice
```

---

## 🧠 LLM 模型配置

### 本地模式（Ollama）

```yaml
llm:
  mode: local
  local:
    host: http://localhost:11434
    model: deepseek-r1:7b
```

### API 模式（OpenAI 兼容）

```yaml
llm:
  mode: api
  api:
    type: openai
    endpoint: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}  # 从环境变量读取
    model: gpt-4
```

---

## ⚙️ 配置说明

### 章节拆分

```yaml
chapter:
  enabled: true
  regex_patterns:
    - '^第[零一二三四五六七八九十百千万0-9]+章'
    - '^Chapter\s+\d+'
  min_length: 100
  keep_title: true
```

### 输出策略

```yaml
output:
  base_path: ./output
  strategy: by_role  # by_role, by_model, by_date
  format: mp3
  bitrate: 128
  filename_template: '{index:03d}-{title}.{format}'
```

---

## 🔧 开发说明

### 运行测试

```bash
# 运行所有测试
python run_test.py

# 运行单元测试（如果有）
pytest
```

### 代码格式化

```bash
# 使用 black 格式化代码
black ga_birds/ fcgi-bin/

# 使用 flake8 检查代码
flake8 ga_birds/ fcgi-bin/
```

---

## 📝 版本计划

- **V1**（当前）：基础文本支持，章节拆分，单角色/情绪 TTS，本地/API 可选，异步生成
- **V2**：多角色配音，情绪更精细化，背景音支持
- **V3**：OCR PDF 支持，Docker 化部署，Web UI，分布式 LLM 推理

---

## 🐛 常见问题

### 1. Ollama 连接失败

确保 Ollama 服务已启动：

```bash
ollama serve
```

### 2. Edge TTS 速度慢

Edge TTS 依赖网络，国内可能较慢。建议使用本地 TTS 模型。

### 3. FFmpeg 未安装

```bash
# Conda 安装
conda install -c conda-forge ffmpeg

# 或手动下载：https://ffmpeg.org/download.html
```

---

## 📄 许可证

MIT License

---

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系方式

如有问题，请提交 Issue。

