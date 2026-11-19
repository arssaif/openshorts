#!/usr/bin/env bash
# GTA 6 Viral Clipper Launcher Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PORT=${1:-8000}

# Activate virtual environment if present
PYTHON="python3"
if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null || true
    if [ -f ".venv/bin/python3" ]; then
        PYTHON=".venv/bin/python3"
    fi
elif [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
    if [ -f "venv/bin/python3" ]; then
        PYTHON="venv/bin/python3"
    fi
fi

echo "=========================================================="
echo "⚡ Starting GTA 6 Viral Clipper Dashboard on port $PORT..."
echo "=========================================================="

# Check if port is in use and pick next available if needed
while lsof -i :$PORT >/dev/null 2>&1; do
    echo "⚠️  Port $PORT is already in use. Trying port $((PORT+1))..."
    PORT=$((PORT+1))
done

# Open browser in background after 1.5 seconds
(sleep 1.5 && (open "http://localhost:$PORT" 2>/dev/null || xdg-open "http://localhost:$PORT" 2>/dev/null || echo "Open http://localhost:$PORT in your browser")) &

# Start FastAPI server
"$PYTHON" server.py --port "$PORT"

