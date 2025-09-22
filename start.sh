#!/bin/bash

# Stock Analyzer Server Startup Script

# Set working directory to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Stock Analyzer Server..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Set Python path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Create necessary directories
mkdir -p logs models features cache

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your actual configuration values."
fi

# Install requirements if needed
if [ ! -f "requirements_installed.flag" ]; then
    echo "📚 Installing Python requirements..."
    pip install -r requirements.txt
    touch requirements_installed.flag
    echo "✅ Requirements installed."
fi

# Run the server
echo "🎯 Launching Stock Analyzer Server..."
python server.py "$@"

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment if it was activated
if [ -d "venv" ]; then
    deactivate
fi

echo "🛑 Stock Analyzer Server stopped (exit code: $EXIT_CODE)"
exit $EXIT_CODE
