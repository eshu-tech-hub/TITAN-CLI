# TITAN CLI Reference

## Overview

The TITAN CLI provides a comprehensive command-line interface for the TITAN Trading Intelligence System. Built with Typer and Rich, it offers modular command groups, rich formatting, and shell completion.

## Installation

```bash
pip install -e .
```

## Entry Point

```bash
titan [OPTIONS] COMMAND [ARGS]...
# or
python -m titan [OPTIONS] COMMAND [ARGS]...
```

## Commands

### Root Commands

| Command | Description |
|---|---|
| `titan version` | Display TITAN version information |
| `titan version -v` | Show detailed version info (build, git, Python, OS) |
| `titan doctor` | Check TITAN installation health |

### Runtime Engine

```bash
titan runtime status              # Show runtime engine status
titan runtime status --json       # Output as JSON
titan runtime status --verbose    # Show component health + monitoring + recovery
titan runtime start               # Start the runtime engine
titan runtime start --verbose     # Start with live progress display
titan runtime stop                # Stop the runtime engine gracefully
titan runtime stop --verbose      # Stop with live progress display
titan runtime restart             # Restart (stop then start)
titan runtime restart --verbose   # Restart with progress
```

The runtime commands manage the full `RuntimeEngine` lifecycle:
- **Broker connection** (PaperBroker for CLI, real broker for production)
- **Stream management** (market data)
- **Scheduler** (pipeline execution loop)
- **Heartbeat** (health monitoring)
- **Event bus** (inter-component communication)
- **Health checks** (component health tracking)

Status shows: Runtime Status, Uptime, Broker, Stream, Scheduler, Pipeline Executions, Active Subscriptions, Warnings, Errors.

Verbose adds: Component Health table, Monitoring Summary, Recovery Summary.

### Paper Trading

```bash
titan paper start                     # Start paper trading session
titan paper start --verbose           # Start with checklist + live progress
titan paper start --dry-run           # Validate only, do not start
titan paper start --dry-run --verbose # Show full checklist details
titan paper start --cash 50000        # Start with custom initial cash
titan paper stop                      # Stop the paper trading session
titan paper stop --verbose            # Stop with live progress
titan paper restart                   # Restart (stop then start)
titan paper restart --verbose         # Restart with progress
titan paper restart --cash 200000     # Restart with new initial cash
titan paper status                    # Show paper trading session status
titan paper status --json             # Output as JSON
titan paper status --verbose          # Show session + performance metrics + positions
titan paper reset                     # Reset paper trading state
titan paper reset --force             # Reset without confirmation
titan paper report                    # Generate session report
titan paper report --json             # Output report as JSON
titan paper report --verbose          # Show full report with positions and orders
titan paper report --export report.json  # Export report to JSON file
titan paper report --export report.csv   # Export report to CSV file
titan paper report --reset            # Reset session after generating report
```

The `paper` commands manage the complete paper trading lifecycle with a **validation pipeline** that runs before startup:

1. **Configuration** - Validates config loads correctly
2. **Broker** - Validates broker provider (defaults to paper)
3. **Environment** - Checks environment
4. **Risk Limits** - Validates risk configuration
5. **Monitoring** - Checks monitoring status
6. **Recovery** - Checks recovery system
7. **Audit** - Checks audit trail
8. **Paper Engine** - Validates paper trading engine readiness

**Options (start):**
- `--dry-run` - Run all validations, display checklist, exit without starting
- `--verbose` - Show startup checklist details, live progress, and session status
- `--cash` - Initial cash balance (default: 100000)

**Options (status):**
- `--json` - Output raw JSON for programmatic consumption
- `--verbose` - Show performance metrics table and open positions

**Options (report):**
- `--json` - Output raw JSON for programmatic consumption
- `--verbose` - Show full report with positions and orders tables
- `--export <path>` - Export report to JSON or CSV file (auto-detected by extension)
- `--reset` - Reset session state after generating report

**Status fields:** Session uptime, cash balance, portfolio value, buying power, exposure, total/daily/realized/unrealized P&L, open positions, orders, win rate, profit factor, expectancy, max drawdown.

**Report sections:** Session Summary, Portfolio Summary, P&L Breakdown, Performance Metrics, Open Positions (verbose), Orders (verbose).

### Live Trading

```bash
# Lifecycle
titan live start                     # Full startup: validate config, connect broker, start engine
titan live start --verbose           # Startup with checklist + live progress
titan live start --dry-run           # Run validations only (no state changes)
titan live start --dry-run --verbose # Show full checklist details
titan live start --force             # Skip safety checks (e.g. missing API key)
titan live stop                      # Graceful shutdown
titan live stop --verbose            # Shutdown with live progress
titan live restart                   # Full restart (stop + start)
titan live restart --verbose         # Restart with progress

# Status & Control
titan live status                    # Show live trading status
titan live status --json             # Output as JSON
titan live status --verbose          # Show risk configuration + monitoring
titan live pause                     # Pause live trading (suspend scheduler)
titan live pause --json              # Pause with JSON output
titan live resume                    # Resume from paused state
titan live resume --json             # Resume with JSON output

# Portfolio & Orders
titan live positions                 # Show current open positions
titan live positions --json          # Positions as JSON
titan live positions --verbose       # Detailed positions view
titan live orders                    # Show current and recent orders
titan live orders --json             # Orders as JSON
titan live orders --status FILLED    # Filter orders by status

# Risk & Health
titan live exposure                  # Show capital and risk exposure
titan live exposure --json           # Exposure as JSON
titan live health                    # Show system health across all components
titan live health --json             # Health as JSON
titan live health --verbose          # Detailed component health

# Reports
titan live report                    # Comprehensive operational report
titan live report --json             # Report as JSON
titan live report --verbose          # Detailed report with all subsystems
titan live report --export report.json  # Export report to file
```

The `live` commands manage the complete live trading stack with a **validation pipeline** that runs before startup:

1. **Configuration** - Validates config loads correctly
2. **Broker** - Validates broker provider is configured
3. **Environment** - Checks environment (warning if not production)
4. **Risk Limits** - Validates risk configuration is not defaults
5. **Monitoring** - Checks monitoring is enabled
6. **Recovery** - Checks recovery system is enabled
7. **Audit** - Checks audit trail is enabled
8. **Runtime** - Checks for existing engine (warning if already running)

**Lifecycle Options:**
- `--dry-run` - Run all validations, display checklist, exit without starting
- `--force` - Skip safety checks (allows missing API key in production)
- `--verbose` - Show startup checklist details, live progress, and component status

**Data Options:**
- `--json` - Output raw JSON for programmatic consumption
- `--status` - Filter orders by status (`FILLED`, `CANCELLED`, `REJECTED`, `OPEN`, `PENDING`)
- `--export` - Export report to a file path

**Status fields:** broker provider, broker status, runtime status, environment, deployment status, uptime.

**Pause/Resume:** Suspends or resumes the pipeline scheduler without disconnecting the broker. Useful for lunch breaks or news events.

**Positions:** Displays open positions via the Broker interface. Shows symbol, exchange, quantity, P&L. Empty when no broker is connected.

**Orders:** Displays order history via the Broker interface. Supports `--status` filtering. Shows order ID, symbol, side, type, quantity, price, and status.

**Exposure:** Displays funds (available cash, used cash, P&L) and margin information from the Broker.

**Health:** Aggregates health from Runtime, Monitoring, Recovery, and Alert subsystems. Shows component status, circuit breakers, and active alerts.

**Report:** Comprehensive operational report combining runtime, deployment, positions, orders, funds, monitoring, recovery, and audit data. Supports `--json` and `--export`.

**Audit trail:** Start, stop, and pause events are automatically recorded via `AuditManager`.

### Monitoring

```bash
titan monitor status                    # Show monitoring subsystem status
titan monitor status --json             # Status as JSON
titan monitor status --verbose          # Detailed status
titan monitor start                     # Start metric collection
titan monitor start --verbose           # Start with progress
titan monitor stop                      # Stop metric collection
titan monitor restart                   # Restart monitoring
titan monitor metrics                   # Show collected metrics
titan monitor metrics --json            # Metrics as JSON
titan monitor dashboard                 # Show monitoring dashboard
titan monitor dashboard --json          # Dashboard as JSON
```

### Alerting

```bash
titan alert status                      # Show alerting subsystem status
titan alert status --json               # Status as JSON
titan alert active                      # Show active (unresolved) alerts
titan alert active --json               # Active alerts as JSON
titan alert history                     # Show alert history
titan alert history --json              # History as JSON
titan alert history --limit 10          # Limit history entries
titan alert acknowledge <alert_id>      # Acknowledge an alert
titan alert acknowledge <alert_id> --by admin  # Acknowledge with attribution
titan alert resolve <alert_id>          # Resolve an alert
titan alert resolve <alert_id> --by ops # Resolve with attribution
titan alert rules                       # Show registered alert rules
titan alert rules --json                # Rules as JSON
```

### Configuration

```bash
titan config show              # Show all configuration sections
titan config show app          # Show only the APP section
titan config show broker       # Show only the BROKER section
titan config show runtime      # Show only the RUNTIME section
titan config show risk         # Show only the RISK section
titan config show execution    # Show only the EXECUTION section
titan config show logging      # Show only the LOGGING section
titan config show monitoring   # Show only the MONITORING section
titan config show --json       # Show all config as JSON
titan config validate          # Validate current configuration
titan config validate --json   # Validate as JSON
titan config diff              # Diff against development profile
titan config diff -p production  # Diff against production profile
titan config diff --json       # Diff as JSON
titan config export            # Export config to config_export.json
titan config export -o cfg.json  # Export to custom path
titan config export --format yaml  # Export as YAML
titan config profile           # Show current profile
titan config profile testing   # Set profile to testing
titan config profile --json    # Profile info as JSON
```

### Audit Trail

```bash
titan audit status             # Show audit subsystem status
titan audit status --json      # Status as JSON
titan audit verify             # Verify audit chain integrity
titan audit search             # Search all events (default limit: 20)
titan audit search --source pipeline  # Filter by source
titan audit search --category system_start  # Filter by category
titan audit search --severity error   # Filter by severity
titan audit search --action "config"  # Filter by action substring
titan audit search --limit 5   # Limit results
titan audit search --json      # Search results as JSON
titan audit export             # Export to audit_export.json
titan audit export -o audit.json  # Export to custom path
titan audit export --format csv  # Export as CSV
titan audit export --limit 100  # Limit exported events
titan audit stats              # Show event statistics
titan audit stats --json       # Stats as JSON
```

### System Reports

```bash
titan report generate  # Generate comprehensive system report
```

### Deployment

```bash
titan deployment status        # Show deployment status
titan deployment status --json # Status as JSON
titan deployment status --verbose  # Status with health probes
titan deployment start         # Start the deployment
titan deployment stop          # Stop the deployment
titan deployment backup        # Create a deployment backup
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

### Recovery

```bash
titan recovery status          # Show recovery subsystem status
titan recovery status --json   # Status as JSON
titan recovery status --verbose  # With recent history
titan recovery retry <component> <reason>  # Trigger recovery retry
titan recovery retry pipeline "manual test" --json  # Retry as JSON
titan recovery checkpoint save --component pipeline --id cp-1  # Save checkpoint
titan recovery checkpoint save --id cp-1 --json  # Save as JSON
titan recovery checkpoint list # List all checkpoints
titan recovery checkpoint list --json  # List as JSON
titan recovery checkpoint latest --component pipeline  # Latest checkpoint
titan recovery restore <checkpoint_id>  # Restore from checkpoint
titan recovery restore <checkpoint_id> --json  # Restore as JSON
titan recovery circuit list    # List circuit breakers
titan recovery circuit list --json  # List as JSON
titan recovery circuit reset --name <name>  # Reset a circuit breaker
titan recovery circuit reset --name <name> --json  # Reset as JSON
```

### Logs

```bash
titan logs stats               # Show log file statistics
titan logs stats --json        # Stats as JSON
titan logs path                # Show log file path
titan logs show                # Show recent log entries
titan logs show -n 50          # Show last 50 log lines
titan logs show --json         # Entries as JSON
titan logs level               # Get current log level
titan logs level --json        # Level as JSON
titan logs level DEBUG         # Set log level
titan logs rotate              # Rotate log files
titan logs rotate --json       # Rotate as JSON
titan logs clear               # Clear log file (with confirmation)
titan logs clear --force       # Clear without confirmation
titan logs clear --force --json  # Clear as JSON
```

### Backtesting

```bash
titan backtest run RELIANCE nse --csv data.csv              # Run backtest from CSV
titan backtest run RELIANCE nse --csv data.csv --capital 500000  # Custom capital
titan backtest run RELIANCE nse --csv data.csv --verbose    # Run with progress display
titan backtest status                # Show backtesting status
titan backtest status --json         # JSON output
titan backtest report                # Show last backtest report
titan backtest report --json         # JSON output
titan backtest report --verbose      # Show full details including warnings/errors
titan backtest report --export report.json  # Export report to file
titan backtest report 1              # Show specific backtest by index
titan backtest list                  # List all completed backtests
titan backtest list --json           # JSON output
```

The `backtest` commands manage the backtesting subsystem. The `run` command
loads historical OHLCV data from a CSV file, feeds it through the TITAN
pipeline using the PaperBroker for simulated execution, and produces a
comprehensive `BacktestReport` with statistics and performance metrics.

**CSV format**: `timestamp,open,high,low,close,volume` (ISO-8601 timestamps).

## Shell Completion

```bash
# Bash
titan --install-completion bash

# Zsh
titan --install-completion zsh

# Fish
titan --install-completion fish

# PowerShell
titan --install-completion powershell

# Show completion script
titan --show-completion
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Usage error |
| 2 | Configuration error |
| 3 | Runtime error |
| 4 | Network error |
| 5 | Authentication error |
| 6 | Deployment error |
| 7 | Health check failed |
| 8 | Backup failed |
| 9 | Audit error |
| 10 | Report error |
| 11 | Timeout |
| 50 | Dependency missing |
| 130 | Interrupted |

## Package Structure

```
titan/cli/
    __init__.py          # Main Typer app, command registration
    common.py            # Shared singletons (config, deployment, monitoring, runtime, recovery managers)
    formatting.py        # Rich formatting helpers (status icons, tables, panels)
    errors.py            # CLI error handling and display
    exit_codes.py        # Standardized exit code constants
    commands/
        __init__.py
        runtime.py       # titan version, titan runtime {status, start, stop, restart}
        doctor.py        # titan doctor
        paper.py         # titan paper {start, stop, restart, status, reset, report}
        live.py          # titan live {status, start, stop, restart}
        backtest.py      # titan backtest {status}
        config.py        # titan config {show}
        monitor.py       # titan monitor {status}
        audit.py         # titan audit {status, verify}
        report.py        # titan report {generate}
        deployment.py    # titan deployment {status, start, stop, backup}
        logs.py          # titan logs {show, path, stats}
```

## Architecture Decisions

See [ADR-033-CLI-Foundation.md](adr/ADR-033-CLI-Foundation.md) for the architectural decision record.

 # #   B r o k e r   C o m m a n d s 
 
 t i t a n   b r o k e r   c e r t i f y   [ b r o k e r _ i d ] 
 
 t i t a n   b r o k e r   r e p o r t   [ r e p o r t _ i d ] 
 
 t i t a n   b r o k e r   c a p a b i l i t i e s   [ b r o k e r _ i d ] 
 
 t i t a n   b r o k e r   c o m p l i a n c e   [ b r o k e r _ i d ] 
 
 t i t a n   b r o k e r   v a l i d a t e   [ b r o k e r _ i d ] 
 
 

## Architecture

For technical details on how the runtime is managed in the background, see [Runtime Service Architecture](RUNTIME_SERVICE.md).
