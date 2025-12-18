#!/bin/bash
set -e

# Check for .venv
if [ ! -d ".venv" ] && [ "$VIRTUAL_ENV" == "" ]; then
    echo "Error: No .venv found and no virtual environment active."
    echo "Please create one or activate it."
    exit 1
fi

echo "Running tests with pytest..."
# Coverage is optional if pytest-cov is not installed, but usually good to have. 
# Using a simple check or just running pytest if coverage fails could be robust, 
# but for now, let's assume standard pytest usage.
python3 -m pytest tests/
