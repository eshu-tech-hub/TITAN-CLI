#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="titan-backup-${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

echo "Creating backup: ${BACKUP_NAME}..."

cd "$PROJECT_DIR"

for item in data logs .env .env.example; do
    if [ -e "$item" ]; then
        cp -r "$item" "${BACKUP_DIR}/${BACKUP_NAME}/"
        echo "  Backed up: $item"
    fi
done

echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}"
echo "Total size: $(du -sh "${BACKUP_DIR}/${BACKUP_NAME}" | cut -f1)"
