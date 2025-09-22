#!/bin/bash

# Stock Analyzer Runner Script
# This script can be called from Spring Boot scheduler

# Set working directory to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set Python path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Create necessary directories
mkdir -p logs models features

# Execute Python script with all arguments
python app/main.py "$@"

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment if it was activated
if [ -d "venv" ]; then
    deactivate
fi

# Exit with the same code as the Python script
exit $EXIT_CODE
