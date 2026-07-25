#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="${PROJECT_DIR}/.titan.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "NOT_RUNNING"
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "HEALTHY"
    echo "PID: $PID"
    echo "Uptime: $(ps -p "$PID" -o etime= 2>/dev/null || echo 'unknown')"
    exit 0
else
    echo "UNHEALTHY"
    echo "PID file exists but process $PID is not running"
    rm -f "$PID_FILE"
    exit 1
fi
