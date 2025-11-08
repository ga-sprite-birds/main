#!/bin/bash

# 设置代理（如果需要）
export http_proxy=http://127.0.0.1:1080
export https_proxy=http://127.0.0.1:1080

echo "正在升级 pip、setuptools 和 wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "正在安装项目依赖..."
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

echo "依赖安装完成！"
echo "已安装的主要包："
pip show fastapi openai pydantic uvicorn | grep -E "(Name|Version)"

