# GA Sprite Birds - 安装指南

> **版本**: v1.0
> **开发团队**: Tiger

## 系统要求

- **操作系统**：Windows 10+, macOS 10.15+, Linux
- **Python**：3.10+
- **内存**：
  - 最低：8GB（仅使用 API 模式）
  - 推荐：32GB（使用本地 LLM DeepSeek R1 7B）
- **磁盘空间**：10GB+（用于模型存储）

---

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/tiger-sprite/ga-sprite-birds.git
cd ga-sprite-birds
```

### 2. 创建 Python 环境并安装依赖

#### 方式 1：使用安装脚本

```bash
# 使用辅助脚本安装项目依赖
bash install_dependencies.sh
```

#### 方式 2：使用 Conda 环境（推荐）

```bash
# 创建基础环境（只安装 Python、pip、setuptools、wheel 和 ffmpeg）
conda create -n ga-sprite-birds python=3.10 pip setuptools wheel -c conda-forge -y
conda activate ga-sprite-birds

# 安装 FFmpeg（音频处理必需）
conda install -c conda-forge ffmpeg -y

# 升级 pip 和构建工具
python -m pip install --upgrade pip setuptools wheel

# 安装所有 Python 依赖（requirements.txt 已做跨平台处理，Windows/Linux/macOS 通用）
pip install -r requirements.txt
```

#### 方式 3：使用 venv（不使用 Conda）

```bash
# 创建虚拟环境
python -m venv venv

# 激活环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 升级 pip 和构建工具
python -m pip install --upgrade pip setuptools wheel

# 安装依赖（同方式 2）
pip install -r requirements.txt

# 注意：需要手动安装 FFmpeg
# Windows: 从 https://ffmpeg.org/download.html 下载
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

**重要提示**：
- 使用 `>=` 版本约束而不是固定版本，避免特定版本不存在的问题
- 必须先安装 `setuptools` 和 `wheel`，否则某些包（如 pydantic-core）会构建失败

### 3. 安装 Ollama（可选，本地 LLM）

如果使用本地 LLM 模式，需要安装 Ollama：

#### Windows

```bash
# 下载安装包
# https://ollama.ai/download/windows

# 安装后，拉取模型
ollama pull deepseek-r1:7b
```

#### macOS

```bash
# 使用 Homebrew
brew install ollama

# 或下载安装包
# https://ollama.ai/download/mac

# 拉取模型
ollama pull deepseek-r1:7b
```

#### Linux

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取模型
ollama pull deepseek-r1:7b
```

### 4. 安装本地 TTS 模型（可选）

#### CosyVoice（推荐）

```bash
# 安装依赖
pip install modelscope
pip install funasr
pip install cosyvoice

# 下载模型（首次运行时自动下载）
# 模型会保存到 ./models/CosyVoice
```

#### ChatTTS

```bash
pip install ChatTTS
```

#### GPT-SoVITS

```bash
# 克隆仓库
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS

# 安装依赖
pip install -r requirements.txt
```

### 5. 配置文件

复制并编辑配置文件：

```bash
# 复制环境变量示例并编辑（项目配置通过 .env 环境变量管理，非 config.yaml）
cp .env.example .env
vim .env
```

### 6. 验证安装

```bash
# 运行测试
pytest
```

---

## 配置说明

### 最小配置（仅使用 API 模式）

项目配置通过 `.env` 环境变量管理（由 `config/__init__.py` 读取），不使用 YAML 文件。复制 `.env.example` 后编辑：

```env
# .env —— 仅使用云端 API（OpenAI 兼容）

# LLM（口语化）：云端 API 模式
LLM_MODE=api
LLM_API_TYPE=openai
LLM_API_ENDPOINT=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_API_MODEL=gpt-4

# TTS：Edge TTS（免费，无需 Key）
TTS_ENGINE=edge
TTS_VOICE=zh-CN-XiaoxiaoNeural
```

### 完全本地配置（本地 LLM）

```env
# .env —— 使用本地 Ollama 运行 LLM

LLM_MODE=local
LLM_LOCAL_HOST=http://localhost:11434
LLM_LOCAL_MODEL=deepseek-r1:7b

# TTS 当前版本仅支持 edge（Edge TTS），无需本地模型
TTS_ENGINE=edge
TTS_VOICE=zh-CN-YunxiNeural
```

> 说明：当前版本 TTS 引擎仅支持 `edge`（Edge TTS）。全部配置项及默认值见 `.env.example`。

---

## 启动服务

### 开发模式

```bash
# 启动 Ollama（如果使用本地 LLM）
ollama serve

# 启动 FastAPI 服务
python fcgi-bin/api.py

# 或使用 uvicorn（支持热重载）
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000 --reload
```

### 生产模式

```bash
# 使用 gunicorn + uvicorn workers
pip install gunicorn

gunicorn fcgi-bin.api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

---

## 常见问题

### 1. pip 安装依赖时报错：找不到特定版本

**错误示例**：
```
ERROR: Could not find a version that satisfies the requirement pypdf==3.17.4
ERROR: Could not find a version that satisfies the requirement openai==1.10.0
```

**解决方案**：
- 使用 `>=` 版本约束而不是 `==` 固定版本
- 确保已升级 pip：`python -m pip install --upgrade pip`

### 2. pip 安装时报错：Cannot import 'setuptools.build_meta' 或 'maturin'

**错误示例**：
```
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'maturin'
```

**解决方案**：
```bash
# 先升级 pip、setuptools 和 wheel
python -m pip install --upgrade pip setuptools wheel

# 然后再安装其他依赖
pip install "fastapi>=0.109.0" ...
```

### 3. 包下载缓慢或失败

**解决方案**：
```bash
# 使用可替代的镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "fastapi>=0.109.0" ...
```

### 4. Conda 环境创建失败

```bash
# 清理 Conda 缓存
conda clean --all

# 删除旧环境
conda env remove -n ga-sprite-birds

# 重新创建环境（推荐使用手动方式）
conda create -n ga-sprite-birds python=3.10 pip setuptools wheel -y
conda activate ga-sprite-birds
conda install -c conda-forge ffmpeg -y
```

### 5. FFmpeg 未找到

```bash
# 检查 FFmpeg 是否安装
ffmpeg -version

# 如果未安装，使用 Conda 安装
conda install -c conda-forge ffmpeg -y

# 或手动下载：https://ffmpeg.org/download.html
```

### 6. Ollama 连接失败

```bash
# 检查 Ollama 服务是否运行
curl http://localhost:11434/api/tags

# 如果未运行，启动服务
ollama serve

# 检查模型是否已下载
ollama list
```

### 7. Edge TTS 网络问题

如果 Edge TTS 连接失败，可以：

1. 稍后重试
2. 切换到本地 TTS 模型
3. 使用其他 API（阿里云、Azure）

**注意**：系统已内置自动重试机制（指数退避，最多重试 5 次），大部分网络问题会自动恢复。

### 8. 内存不足

如果运行本地 LLM 时内存不足：

1. 使用更小的模型（如 DeepSeek R1 1.5B）
2. 切换到 API 模式
3. 增加系统内存或使用 GPU

---

## 重试机制说明

系统已内置智能重试机制，无需手动配置：

### TTS 请求重试
- **最大重试次数**：5 次
- **重试策略**：指数退避（1s, 2s, 4s, 8s, 16s，最大 30s）
- **适用场景**：网络超时、连接失败、临时故障

### LLM 请求重试
- **最大重试次数**：3 次
- **重试策略**：指数退避（1s, 2s, 4s，最大 10s）
- **适用场景**：本地 Ollama 连接失败、API 临时故障

### 重试日志示例
```
WARNING - Attempt 1 failed: Connection timeout, retrying in 1.0s...
WARNING - Attempt 2 failed: Connection timeout, retrying in 2.0s...
INFO - TTS 生成成功（第 3 次尝试）
```

### 依赖说明
重试机制使用 `tenacity` 库实现，已包含在 `requirements.txt` 中：
```bash
pip install "tenacity>=8.2.3"
```

---

## 卸载

```bash
# 删除 Conda 环境
conda deactivate
conda env remove -n ga-sprite-birds

# 删除项目文件
cd ..
rm -rf ga-sprite-birds
```

---

## 可选：运行 API 测试

安装完成后，可以运行 API 测试验证系统功能是否正常。

### 运行单元测试（推荐）

单元测试不需要启动服务器，速度快：

```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定测试
pytest tests/unit/test_upload.py -v
```

### 运行集成测试

集成测试需要先启动 API 服务器：

```bash
# 终端 1: 启动 API 服务器
uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000

# 终端 2: 运行集成测试
pytest tests/integration -v
```

### 生成测试报告（可选）

```bash
# 安装测试报告工具
pip install pytest-html pytest-cov

# 生成 HTML 测试报告
pytest --html=report.html --self-contained-html

# 生成测试覆盖率报告
pytest --cov=ga_birds --cov=fcgi-bin --cov-report=html
```

详细说明请参考 [tests/README.md](../tests/README.md)。

---

## 下一步

安装完成后，请阅读 [README.zh.md](README.zh.md) 了解如何使用系统。

