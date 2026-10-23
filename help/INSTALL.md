# GA Sprite Birds - Installation Guide

> **Version**: v1.0
> **Dev team**: Tiger

## System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, Linux
- **Python**: 3.10+
- **Memory**:
  - Minimum: 8GB (API mode only)
  - Recommended: 32GB (with local LLM DeepSeek R1 7B)
- **Disk Space**: 10GB+ (for model storage)

---

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/ga-sprite-birds/main.git
cd main
```

### 2. Create a Python Environment and Install Dependencies

#### Option 1: Use the Installation Script

```bash
# Install project dependencies with the helper script
bash install_dependencies.sh
```

#### Option 2: Use a Conda Environment (Recommended)

```bash
# Create the base environment (only installs Python, pip, setuptools, wheel and ffmpeg)
conda create -n ga-sprite-birds python=3.10 pip setuptools wheel -c conda-forge -y
conda activate ga-sprite-birds

# Install FFmpeg (required for audio processing)
conda install -c conda-forge ffmpeg -y

# Upgrade pip and build tools
python -m pip install --upgrade pip setuptools wheel

# Install all Python dependencies (requirements.txt is cross-platform and works on Windows/Linux/macOS)
pip install -r requirements.txt
```

#### Option 3: Use venv (without Conda)

```bash
# Create a virtual environment
python -m venv venv

# Activate the environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Upgrade pip and build tools
python -m pip install --upgrade pip setuptools wheel

# Install dependencies (same as Option 2)
pip install -r requirements.txt

# Note: FFmpeg must be installed manually
# Windows: download from https://ffmpeg.org/download.html
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

**Important Notes**:
- Use `>=` version constraints instead of pinned versions to avoid issues where a specific version does not exist.
- `setuptools` and `wheel` must be installed first, otherwise some packages (such as pydantic-core) will fail to build.

### 3. Install Ollama (Optional, for Local LLM)

If you use the local LLM mode, you need to install Ollama:

#### Windows

```bash
# Download the installer
# https://ollama.ai/download/windows

# After installation, pull the model
ollama pull deepseek-r1:7b
```

#### macOS

```bash
# Using Homebrew
brew install ollama

# Or download the installer
# https://ollama.ai/download/mac

# Pull the model
ollama pull deepseek-r1:7b
```

#### Linux

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the model
ollama pull deepseek-r1:7b
```

### 4. TTS Engine

The current release uses **Edge TTS** for narration. It is free and does not require a local model, but it does need network access. Other `TTS_ENGINE` values are not implemented in this release.

### 5. Configuration File

Copy and edit the configuration file:

```bash
# Copy the environment variable example and edit it (project configuration is managed via .env environment variables, not config.yaml)
cp .env.example .env
vim .env
```

### 6. Verify the Installation

```bash
# Run the unit tests (no server required)
pytest tests/unit
```

---

## Configuration Reference

### Minimal Configuration (API Mode Only)

Project configuration is managed through `.env` environment variables (read by `config/__init__.py`); no YAML file is used. Copy `.env.example` and then edit it:

```env
# .env — Cloud API only (OpenAI compatible)

# LLM (conversational): cloud API mode
LLM_MODE=api
LLM_API_TYPE=openai
LLM_API_ENDPOINT=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_API_MODEL=gpt-4

# TTS: Edge TTS (free, no key required)
TTS_ENGINE=edge
TTS_VOICE=zh-CN-XiaoxiaoNeural
```

### Fully Local Configuration (Local LLM)

```env
# .env — Run the LLM using local Ollama

LLM_MODE=local
LLM_LOCAL_HOST=http://localhost:11434
LLM_LOCAL_MODEL=deepseek-r1:7b

# The current version's TTS engine only supports edge (Edge TTS); no local model required
TTS_ENGINE=edge
TTS_VOICE=zh-CN-YunxiNeural
```

> Note: The current version's TTS engine only supports `edge` (Edge TTS). See `.env.example` for the full list of options and default values.

---

## Starting the Service

### Recommended

```bash
# Start Ollama first if you use the local LLM
ollama serve

# Start the local service and open the GUI
bash api.sh
```

`api.sh` starts FastAPI on a free port starting at `API_PORT` (default `8000`) and opens the browser.

### Direct launch

```bash
PYTHONPATH=. python fcgi-bin/api.py
```

### Production note

This project is designed for local use. The API has no authentication, and the bundled launcher uses a single process. If you need to expose it to a trusted network, place it behind an authenticated reverse proxy instead of binding it directly to the public internet.

---

## Frequently Asked Questions

### 1. pip reports an error when installing dependencies: specific version not found

**Error example**:
```
ERROR: Could not find a version that satisfies the requirement pypdf==3.17.4
ERROR: Could not find a version that satisfies the requirement openai==1.10.0
```

**Solution**:
- Use `>=` version constraints instead of `==` pinned versions.
- Make sure pip is upgraded: `python -m pip install --upgrade pip`

### 2. pip error: Cannot import 'setuptools.build_meta' or 'maturin'

**Error example**:
```
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'maturin'
```

**Solution**:
```bash
# Upgrade pip, setuptools and wheel first
python -m pip install --upgrade pip setuptools wheel

# Then install the remaining dependencies
pip install "fastapi>=0.109.0" ...
```

### 3. Slow or failed package downloads

**Solution**:
```bash
# Use an alternative package mirror
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "fastapi>=0.109.0" ...
```

### 4. Conda environment creation failed

```bash
# Clean the Conda cache
conda clean --all

# Remove the old environment
conda env remove -n ga-sprite-birds

# Recreate the environment (manual method recommended)
conda create -n ga-sprite-birds python=3.10 pip setuptools wheel -y
conda activate ga-sprite-birds
conda install -c conda-forge ffmpeg -y
```

### 5. FFmpeg not found

```bash
# Check if FFmpeg is installed
ffmpeg -version

# If not installed, install via Conda
conda install -c conda-forge ffmpeg -y

# Or download manually: https://ffmpeg.org/download.html
```

### 6. Ollama connection failed

```bash
# Check whether the Ollama service is running
curl http://localhost:11434/api/tags

# If not running, start the service
ollama serve

# Check whether the model is downloaded
ollama list
```

### 7. Edge TTS network issues

If Edge TTS fails to connect, you can:

1. Retry later.
2. Check your network/proxy configuration.
3. Use a different network or a mirror if your region blocks the service.

**Note**: The system has a built-in automatic retry mechanism (exponential backoff, up to 5 retries), so most network issues recover automatically.

### 8. Out of memory

If you run out of memory when running the local LLM:

1. Use a smaller model (e.g., DeepSeek R1 1.5B).
2. Switch to API mode.
3. Increase system memory or use a GPU.

---

## Retry Mechanism Reference

The system has a built-in intelligent retry mechanism that requires no manual configuration:

### TTS Request Retries
- **Maximum retries**: 5
- **Retry strategy**: Exponential backoff (1s, 2s, 4s, 8s, 16s, max 30s)
- **Applicable scenarios**: Network timeout, connection failure, transient faults

### LLM Request Retries
- **Maximum retries**: 3
- **Retry strategy**: Exponential backoff (1s, 2s, 4s, max 10s)
- **Applicable scenarios**: Local Ollama connection failure, transient API faults

### Retry Log Example
```
WARNING - Attempt 1 failed: Connection timeout, retrying in 1.0s...
WARNING - Attempt 2 failed: Connection timeout, retrying in 2.0s...
INFO - TTS generation succeeded (attempt 3)
```

### Dependency Notes
The retry mechanism is implemented using the `tenacity` library and is already included in `requirements.txt`:
```bash
pip install "tenacity>=8.2.3"
```

---

## Uninstallation

```bash
# Remove the Conda environment
conda deactivate
conda env remove -n ga-sprite-birds

# Remove the project files
cd ..
rm -rf ga-sprite-birds
```

---

## Optional: Running API Tests

After installation, you can run API tests to verify that the system works correctly.

### Run Unit Tests (Recommended)

Unit tests do not require starting the server and are fast:

```bash
# Run all unit tests
pytest tests/unit -v

# Run a specific test
pytest tests/unit/test_upload.py -v
```

### Run Integration Tests

Integration tests require the API server to be started first:

```bash
# Terminal 1: Start the API server
bash api.sh

# Terminal 2: Run the integration tests
# They default to http://localhost:8000.
pytest tests/integration -v
```

### Generate a Test Report (Optional)

```bash
# Install the test report tools
pip install pytest-html pytest-cov

# Generate an HTML test report
pytest --html=report.html --self-contained-html

# Generate a test coverage report
pytest --cov=ga_birds --cov=fcgi-bin --cov-report=html
```

See [tests/README.md](../tests/README.md) for details.

---

## Next Steps

After installation, please read [../README.md](../README.md) to learn how to use the system.

---

**Author:** adam
**Email:** dev@ebf.hk
**Website:** http://ebf.cc
**Source:** https://github.com/ga-sprite-birds/main
