#!/bin/bash

# GA Sprite Birds - CLI startup script
# Version: v1.0

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "${SCRIPT_DIR}"


# Set PYTHONPATH and run the CLI
PYTHONPATH=. python fcgi-bin/cli.py "$@"

