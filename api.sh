#!/bin/bash

# GA Sprite Birds - startup script
# Version: v1.0

echo "Starting the GA Sprite Birds audio narration system..."

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "${SCRIPT_DIR}"

# Set the Python path
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}"

# Check the Python environment
if ! command -v python &> /dev/null; then
    echo "Error: Python was not found. Please install Python 3.10+ first."
    exit 1
fi

# Show the Python version
echo "Python version:"
python --version

# Start the FastAPI service
echo "Starting the API service..."
echo "Open http://localhost:8000/docs to view the API documentation."
echo "Press Ctrl+C to stop the service."
echo ""

python fcgi-bin/api.py

