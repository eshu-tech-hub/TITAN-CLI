#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="${PROJECT_DIR}/.titan.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "TITAN is not running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping TITAN (PID: $PID)..."
    kill "$PID"
    for i in $(seq 1 10); do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing TITAN (PID: $PID)..."
        kill -9 "$PID" 2>/dev/null || true
    fi
    echo "TITAN stopped"
else
    echo "TITAN process $PID is not running"
fi

rm -f "$PID_FILE"
