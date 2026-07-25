#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup-name>"
    echo ""
    echo "Available backups:"
    if [ -d "$BACKUP_DIR" ]; then
        ls -1 "$BACKUP_DIR" 2>/dev/null || echo "  (none)"
    else
        echo "  (no backups directory)"
    fi
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Error: Backup not found: ${BACKUP_PATH}"
    exit 1
fi

echo "Restoring from backup: ${BACKUP_NAME}..."
cd "$PROJECT_DIR"

bash "${SCRIPT_DIR}/stop.sh" 2>/dev/null || true

for item in data logs .env; do
    if [ -e "${BACKUP_PATH}/${item}" ]; then
        cp -r "${BACKUP_PATH}/${item}" .
        echo "  Restored: $item"
    fi
done

echo "Restore complete: ${BACKUP_NAME}"
