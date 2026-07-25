#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="${PROJECT_DIR}/.titan.pid"
LOG_DIR="${PROJECT_DIR}/logs"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "TITAN is already running (PID: $PID)"
        exit 1
    fi
    rm -f "$PID_FILE"
fi

echo "Starting TITAN..."
cd "$PROJECT_DIR"
nohup python -m titan status >> "${LOG_DIR}/titan.log" 2>&1 &
echo $! > "$PID_FILE"
echo "TITAN started (PID: $(cat "$PID_FILE"))"
