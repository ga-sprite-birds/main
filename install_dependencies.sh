#!/bin/bash

# Upgrade pip and build tools
echo "Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "Installing project dependencies..."
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
    "edge-tts>=7.3.1" \
    "pydub>=0.25.1" \
    "soundfile>=0.12.1" \
    "loguru>=0.7.2" \
    "aiofiles>=23.2.1" \
    "python-dotenv>=1.0.0" \
    "pytest>=7.4.4" \
    "pytest-asyncio>=0.23.3" \
    "black>=24.1.1" \
    "flake8>=7.0.0" \
    "torch" \
    "torchvision" \
    "torchaudio"

echo "Dependencies installed."
echo "Installed core packages:"
pip show fastapi openai pydantic uvicorn | grep -E "(Name|Version)"

