#!/bin/bash

# GA Sprite Birds - CLI startup script
# Version: v1.0

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "${SCRIPT_DIR}"


# Set PYTHONPATH and run the CLI
PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

PYTHONPATH=. "$PYTHON_BIN" fcgi-bin/cli.py "$@"

