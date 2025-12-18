#!/bin/bash
set -e

# Check for .venv
if [ ! -d ".venv" ] && [ "$VIRTUAL_ENV" == "" ]; then
    echo "Error: No .venv found and no virtual environment active."
    echo "Please create one or activate it."
    exit 1
fi

echo "Starting Uvicorn with reloading..."
python3 -m uvicorn src.software_factory_poc.main:app --reload --host 0.0.0.0 --port 8000
