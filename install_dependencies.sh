#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

echo "Upgrading pip, setuptools, and wheel..."
"${PYTHON_BIN}" -m pip install --upgrade pip setuptools wheel

echo "Installing project dependencies..."
"${PYTHON_BIN}" -m pip install -r "${SCRIPT_DIR}/requirements.txt"

echo
echo "Dependencies installed."
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Warning: ffmpeg was not found on PATH."
    echo "Install it with your package manager before generating or merging audio."
fi
