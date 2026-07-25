# TITAN Deployment Guide

## Overview

This document covers deploying TITAN in production environments.

## Prerequisites

- Python 3.14+
- 500MB+ free disk space
- Network access to broker APIs
- (Optional) Docker for containerized deployment

## Installation

```bash
git clone https://github.com/your-org/titan-cli.git
cd titan-cli
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -e .
```

## Configuration

Copy and configure the environment file:

```bash
cp .env.example .env
# Edit .env with your broker credentials and settings
```

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TITAN_ENVIRONMENT` | Deployment environment | `development` |
| `TITAN_BROKER_PROVIDER` | Broker provider | `paper` |
| `TITAN_BROKER_API_KEY` | Broker API key | (required for production) |
| `TITAN_LOG_LEVEL` | Logging level | `INFO` |

## Deployment Manager

`DeploymentManager` is TITAN's single production entry point:

```python
from titan.deployment import DeploymentManager

dm = DeploymentManager()
report = dm.start(profile="production")
print(f"Status: {report.status}")
print(f"Version: {report.version.version}")
```

## Docker Deployment

```bash
cd docker
docker compose up -d
docker compose logs -f titan
```

## systemd Deployment (Linux)

```bash
sudo cp systemd/titan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable titan
sudo systemctl start titan
sudo systemctl status titan
```

## Windows Service

```bash
pip install pywin32
python windows\titan_service.py install
python windows\titan_service.py start
```

## Health Checks

```bash
# Linux/Mac
bash scripts/healthcheck.sh

# PowerShell
.\scripts\healthcheck.ps1

# Docker
docker compose exec titan python -c "from titan.deployment import DeploymentManager; print('healthy')"
```

## Backup & Restore

```bash
# Create backup
bash scripts/backup.sh

# List backups
ls backups/

# Restore
bash scripts/restore.sh <backup-name>
```

## Environment Profiles

| Profile | Description | Use Case |
|---------|-------------|----------|
| `development` | Local dev | Default |
| `testing` | Test environment | CI/CD |
| `paper` | Paper trading | Strategy validation |
| `backtesting` | Historical | Backtest runs |
| `production` | Live trading | Real capital |

## Production Checklist

1. Environment validated
2. Broker credentials configured
3. Secrets available (not hardcoded)
4. Directories writable
5. Disk space sufficient
6. Logging configured
7. Monitoring enabled
8. Backup schedule established

## CLI Integration

The deployment subsystem is exposed through the `titan deployment` command group:

```bash
titan deployment status        # Show deployment status
titan deployment status --json # Status as JSON
titan deployment status --verbose  # With health probes

titan deployment start         # Start the deployment
titan deployment stop          # Stop the deployment

titan deployment backup        # Create a backup
titan deployment backup --dest /path/to/backups  # Custom destination
titan deployment backup --json # Backup manifest as JSON

titan deployment restore <backup_id>  # Restore from backup
titan deployment restore <backup_id> --json  # Restore as JSON

titan deployment validate      # Validate deployment health
titan deployment validate --json  # Validation as JSON
titan deployment validate --verbose  # With subsystem details

titan deployment health        # Show deployment health
titan deployment health --json # Health as JSON
titan deployment health --verbose  # With subsystem table
```

### Health Probes

The deployment health service provides three probes:

- **Readiness**: Is TITAN ready to accept work?
- **Liveness**: Is TITAN alive and responding?
- **Startup**: Has TITAN completed initialization?

These are accessible via `titan deployment health --verbose`.

## TUI Integration
The Configuration & Deployment Screen (F7) provides live deployment status, health, and history.
