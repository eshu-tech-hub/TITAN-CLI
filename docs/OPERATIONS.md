# TITAN Operations Guide

## Day-to-Day Operations

### Starting TITAN

```bash
# Linux/Mac
bash scripts/start.sh

# Windows
.\scripts\start.ps1

# systemd
sudo systemctl start titan
```

### CLI-Based Lifecycle Management

TITAN also provides direct CLI commands for lifecycle management:

```bash
# Paper trading (no broker connection required)
titan paper start --verbose  # Start with validation checklist
titan paper status           # Check session status
titan paper status --json    # JSON output for automation
titan paper report           # Generate session report
titan paper report --export report.json  # Export to file
titan paper stop             # Stop session
titan paper restart          # Full restart
titan paper reset            # Reset all state

# Live trading (full validation pipeline)
titan live status           # Check status
titan live start --verbose  # Start with validation checklist
titan live stop --verbose   # Graceful shutdown
titan live restart          # Full restart

# Runtime engine (no validation pipeline)
titan runtime status
titan runtime start --verbose
titan runtime stop --verbose

# Pre-flight checks (no state changes)
titan live start --dry-run
titan live start --dry-run --verbose

# JSON output for monitoring/automation
titan live status --json
titan runtime status --json

# Backtesting (historical data replay)
titan backtest run RELIANCE nse --csv data.csv  # Run backtest
titan backtest status                           # Check status
titan backtest report                           # View report
titan backtest list                             # List completed backtests
```

### Stopping TITAN

```bash
bash scripts/stop.sh
# or
sudo systemctl stop titan
```

### Restarting

```bash
bash scripts/restart.sh
# or
sudo systemctl restart titan
```

### Health Monitoring

```bash
bash scripts/healthcheck.sh
```

## Operational Playbooks

### Morning Startup

Start the trading day with a validated startup sequence:

```bash
# 1. Verify configuration
titan config show broker

# 2. Pre-flight check (no state changes)
titan live start --dry-run --verbose

# 3. Start live trading
titan live start --verbose

# 4. Verify system health
titan live health

# 5. Check positions and orders
titan live positions
titan live orders
```

### Health Verification

Periodic health checks during the trading day:

```bash
# Quick health check
titan live health --json

# Detailed component status
titan live health --verbose

# Check monitoring subsystem
titan monitor status

# Check for active alerts
titan alert active
```

### Trading Day Workflow

Standard workflow during market hours:

```bash
# Check positions
titan live positions

# Check orders
titan live orders

# Check exposure
titan live exposure

# Check runtime status
titan live status

# View comprehensive report
titan live report
```

### Lunch Pause

Pause trading during lunch break (scheduler stops, broker stays connected):

```bash
# Pause scheduler
titan live pause

# Verify paused state
titan live status

# Positions and orders remain accessible
titan live positions
titan live orders
```

### Resume

Resume trading after lunch or maintenance:

```bash
# Resume scheduler
titan live resume

# Verify running state
titan live status

# Check health after resume
titan live health
```

### End-of-Day Shutdown

Graceful shutdown at end of trading day:

```bash
# 1. Generate daily report
titan live report --export daily_report.json

# 2. Verify all orders processed
titan live orders --status PENDING

# 3. Stop live trading
titan live stop --verbose

# 4. Verify stopped state
titan live status

# 5. Check monitoring recorded the session
titan monitor metrics
```

### Daily Report Export

Export operational data for record-keeping:

```bash
# Full report as JSON
titan live report --json --export reports/$(date +%Y%m%d)_report.json

# Positions snapshot
titan live positions --json --export reports/$(date +%Y%m%d)_positions.json

# Order history
titan live orders --json --export reports/$(date +%Y%m%d)_orders.json
```

### Recovery Operations

```bash
# Check recovery status
titan recovery status

# View recent recovery attempts
titan recovery status --verbose

# Trigger manual recovery
titan recovery retry pipeline "connection timeout"

# Save checkpoint before maintenance
titan recovery checkpoint save --component pipeline --id pre-maintenance

# List checkpoints
titan recovery checkpoint list

# Restore from checkpoint
titan recovery restore pre-maintenance

# Check circuit breakers
titan recovery circuit list

# Reset a tripped circuit breaker
titan recovery circuit reset --name broker_connection
```

### Deployment Validation

```bash
# Pre-deployment validation
titan deployment validate

# Detailed validation
titan deployment validate --verbose

# Health check
titan deployment health

# Create backup before changes
titan deployment backup

# Restore from backup
titan deployment restore <backup_id>
```

### Audit Operations

```bash
# Check audit status
titan audit status

# Verify chain integrity
titan audit verify

# Search for specific events
titan audit search --source execution --severity error

# Search by time (limit results)
titan audit search --category order_placed --limit 10

# Export audit trail
titan audit export --format csv -o audit_$(date +%Y%m%d).csv

# View statistics
titan audit stats
```

### Log Management

```bash
# Check log level
titan logs level

# Set log level for debugging
titan logs level DEBUG

# Rotate logs
titan logs rotate

# Clear logs
titan logs clear --force
```

## Monitoring

### TUI Dashboard

TITAN provides a real-time terminal UI for continuous system monitoring:

```bash
# Start the institutional desktop shell
python -m titan.tui.shell

# Or the legacy flat layout
python -m titan.tui.layout
```

**Navigation (ShellApp):**
- F1: Dashboard — 5 status cards (runtime, market, trading, health, system)
- F2: Runtime — 6 widgets for engine introspection
- F3: Paper Trading — 7 widgets for live paper session monitoring
- F5: Live Trading — 8 widgets for live trading monitoring
- F6: Monitoring & Alerting — 8 widgets for operational health monitoring
- F11: Help — keyboard shortcuts reference
- Escape: Previous screen
- Ctrl+R: Refresh current screen
- Ctrl+Q: Quit

The sidebar provides persistent navigation across all screens. The header shows version, hostname, and runtime status. The status bar shows environment, broker status, mode, and refresh interval.

### Health Probes

- **Readiness**: Is TITAN ready to accept work?
- **Liveness**: Is TITAN alive and responsive?
- **Startup**: Has TITAN completed initialization?

### Health Report

```python
from titan.deployment import DeploymentManager

dm = DeploymentManager.instance()
report = dm.health().generate_report()
print(f"Overall: {report.overall_status}")
print(f"Readiness: {report.readiness}")
print(f"Liveness: {report.liveness}")
```

### Deployment Report

```python
report = dm.generate_report()
print(f"Status: {report.status}")
print(f"Environment: {report.environment}")
print(f"Uptime: {report.uptime_seconds:.0f}s")
print(f"Version: {report.version.version}")
```

## Backup Operations

### Automated Backup

```bash
bash scripts/backup.sh
```

Creates timestamped backup in `backups/` directory containing:
- `data/` - Runtime data
- `logs/` - Log archives
- `.env` - Configuration

### Restore

```bash
bash scripts/restore.sh titan-backup-20260710-120000
```

## Troubleshooting

### TITAN Won't Start

1. Check Python version: `python --version` (requires 3.14+)
2. Check dependencies: `pip install -e .`
3. Check configuration: review `.env` file
4. Check logs: `tail -f logs/titan.log`

### High Memory Usage

1. Check `MonitoringConfig.snapshot_retention`
2. Review log rotation settings
3. Monitor with `DeploymentHealthService`

### Broker Connection Issues

1. Verify API credentials in `.env`
2. Check network connectivity
3. Verify broker is operational
4. Check `TITAN_BROKER_CONNECTION_TIMEOUT_SECONDS`

## Log Management

Logs are stored in `logs/` directory:
- `titan.log` - Main application log
- Rotation: Configurable via `LoggingConfig`

## Performance Tuning

- `RuntimeConfig.pipeline_interval_seconds`: Pipeline frequency
- `MonitoringConfig.collector_interval_seconds`: Metric collection rate
- `RiskConfig.max_position_size`: Position limits

## Configuration & Deployment Visibility
Operators can verify environment details and active profiles through the Configuration & Deployment Screen (F7) in the TUI.


## Architecture

For technical details on how the runtime is managed in the background, see [Runtime Service Architecture](RUNTIME_SERVICE.md).
