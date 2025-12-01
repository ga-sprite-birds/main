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
git clone <repository_url>
cd ga-sprite-birds
```

### 2. 创建 Python 环境并安装依赖

#### 方式 1：使用安装脚本（推荐，适用于中国大陆）

```bash
# 如果在中国大陆，需要设置代理加速下载
# 脚本会自动设置代理并安装所有依赖
bash install_dependencies.sh
```

#### 方式 2：使用 Conda 环境（推荐）

```bash
# 注意：如果在中国大陆，建议先设置代理
export http_proxy=http://127.0.0.1:1080
export https_proxy=http://127.0.0.1:1080

# 创建基础环境（只安装 Python、pip、setuptools、wheel 和 ffmpeg）
conda create -n ga-sprite-birds python=3.10 pip setuptools wheel -c conda-forge -y
conda activate ga-sprite-birds

# 安装 FFmpeg（音频处理必需）
conda install -c conda-forge ffmpeg -y

# 升级 pip 和构建工具
python -m pip install --upgrade pip setuptools wheel

# 安装所有 Python 依赖（使用灵活的版本约束）
pip install \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "python-multipart>=0.0.6" \
    "pyyaml>=6.0.1" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "chardet>=5.2.0" \
    "pypdf>=3.17.0" \
    "python-magic-bin>=0.4.14" \
    "ollama>=0.1.6" \
    "openai>=1.0.0" \
    "httpx>=0.26.0" \
    "edge-tts>=6.1.9" \
    "pydub>=0.25.1" \
    "soundfile>=0.12.1" \
    "loguru>=0.7.2" \
    "aiofiles>=23.2.1" \
    "python-dotenv>=1.0.0" \
    "pytest>=7.4.4" \
    "pytest-asyncio>=0.23.3" \
    "black>=24.1.1" \
    "flake8>=7.0.0"
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
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" ...

# 注意：需要手动安装 FFmpeg
# Windows: 从 https://ffmpeg.org/download.html 下载
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

**重要提示**：
- 使用 `>=` 版本约束而不是固定版本，避免特定版本不存在的问题
- 必须先安装 `setuptools` 和 `wheel`，否则某些包（如 pydantic-core）会构建失败
- 如果在中国大陆，强烈建议设置代理以加速下载

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
# 配置文件已存在，直接编辑
vim config.yaml

# 或复制环境变量示例
cp .env.example .env
vim .env
```

### 6. 验证安装

```bash
# 运行测试
python run_test.py
```

---

## 配置说明

### 最小配置（仅使用 API）

```yaml
llm:
  mode: api
  api:
    type: openai
    endpoint: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    model: gpt-4

tts:
  mode: api
  api:
    type: edge-tts
    voice: zh-CN-XiaoxiaoNeural
```

### 完全本地配置

```yaml
llm:
  mode: local
  local:
    host: http://localhost:11434
    model: deepseek-r1:7b

tts:
  mode: local
  local:
    engine: cosyvoice
    model_path: ./models/CosyVoice
```

---

## 启动服务

### 开发模式

```bash
# 启动 Ollama（如果使用本地 LLM）
ollama serve

# 启动 FastAPI 服务
python fcgi-bin/index.py

# 或使用 uvicorn（支持热重载）
uvicorn fcgi-bin.index:app --host 0.0.0.0 --port 8000 --reload
```

### 生产模式

```bash
# 使用 gunicorn + uvicorn workers
pip install gunicorn

gunicorn fcgi-bin.index:app \
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
- 如果在中国大陆，设置代理加速下载

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

### 3. 中国大陆网络下载缓慢或失败

**解决方案**：
```bash
# 方法 1：使用代理（推荐）
export http_proxy=http://127.0.0.1:1080
export https_proxy=http://127.0.0.1:1080

# 方法 2：使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "fastapi>=0.109.0" ...

# 方法 3：永久配置镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
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

1. 使用代理
2. 切换到本地 TTS 模型
3. 使用其他 API（阿里云、Azure）

### 8. 内存不足

如果运行本地 LLM 时内存不足：

1. 使用更小的模型（如 DeepSeek R1 1.5B）
2. 切换到 API 模式
3. 增加系统内存或使用 GPU

---

## 卸载

```bash
# 删除 Conda 环境
conda deactivate
conda env remove -n ga-sprite-mp3

# 删除项目文件
cd ..
rm -rf ga-sprite-mp3
```

---

## 下一步

安装完成后，请阅读 [README.md](README.md) 了解如何使用系统。

