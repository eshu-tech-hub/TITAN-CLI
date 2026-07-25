# ADR-033: CLI Foundation

## Status

Accepted

## Date

2026-07-11

## Context

TITAN had a monolithic `titan/cli.py` file containing all CLI commands in a single module. As the system grew to 25+ subsystems, this approach became unmaintainable:
- No separation of concerns between command groups.
- No shared formatting or error handling utilities.
- No standardized exit codes.
- No testable command modules (commands were tightly coupled to the app).
- No shell completion support.
- No structured help system.

The CLI needed a modular foundation that could scale to support the full TITAN subsystem surface while maintaining backward compatibility and testability.

## Decision

### Package-Based CLI Architecture

Replace the monolithic `titan/cli.py` with a `titan/cli/` package containing:

```
titan/cli/
    __init__.py      # Typer app, command wiring
    common.py        # Shared singletons
    formatting.py    # Rich formatting utilities
    errors.py        # Error display
    exit_codes.py    # Exit code constants
    commands/        # One module per command group
```

### Command Groups

Each command group is a separate `typer.Typer()` instance registered as a sub-app:

| Sub-app | Commands | Module |
|---|---|---|
| Root | `version`, `doctor` | `__init__.py` |
| `runtime` | `status`, `start`, `stop`, `restart` | `commands/runtime.py` |
| `paper` | `start`, `stop`, `restart`, `status`, `reset`, `report` | `commands/paper.py` |
| `live` | `status`, `start`, `stop`, `restart` | `commands/live.py` |
| `backtest` | `run`, `status`, `report`, `list` | `commands/backtest.py` |
| `config` | `show` | `commands/config.py` |
| `monitor` | `status` | `commands/monitor.py` |
| `audit` | `status`, `verify` | `commands/audit.py` |
| `report` | `generate` | `commands/report.py` |
| `deployment` | `status`, `start`, `stop`, `backup` | `commands/deployment.py` |
| `logs` | `show`, `path`, `stats` | `commands/logs.py` |

### Lazy-Loaded Singletons

`common.py` provides lazy-loaded access to shared managers:
- `get_config_manager()` - ConfigManager singleton
- `get_deployment_manager()` - DeploymentManager singleton
- `get_monitoring_manager()` - MonitoringManager singleton
- `get_runtime_engine()` - RuntimeEngine with PaperBroker (default)
- `get_recovery_manager()` - RecoveryManager singleton

This avoids importing heavy subsystem modules at CLI startup. Managers are only instantiated when their commands are first invoked.

### Runtime Engine Integration

The `titan runtime` command group provides full lifecycle management of the `RuntimeEngine`:

- **`status`**: Displays RuntimeReport fields (status, uptime, broker, stream, scheduler, pipeline executions, subscriptions, warnings, errors). `--json` outputs raw JSON. `--verbose` adds Component Health, Monitoring Summary, and Recovery Summary tables.
- **`start`**: Connects broker, starts stream/scheduler/heartbeat. `--verbose` shows live progress via Rich `Live` display.
- **`stop`**: Graceful shutdown in reverse order. `--verbose` shows shutdown progress.
- **`restart`**: stop then start.

The engine uses `PaperBroker` by default for CLI invocations (no network required). Production deployments inject real broker implementations via `set_runtime_engine()`.

### Live Trading Integration

The `titan live` command group provides full management of the live trading stack, built on top of the runtime engine. It orchestrates existing modules only — no new trading logic, execution logic, or broker logic.

**Command Hierarchy:**

| Command | Purpose | Options |
|---------|---------|---------|
| `start` | Full startup with validation pipeline | `--dry-run` `--force` `--verbose` |
| `stop` | Graceful shutdown | `--verbose` |
| `restart` | Stop then start | `--force` `--verbose` |
| `status` | Runtime + deployment status | `--json` `--verbose` |
| `pause` | Suspend pipeline scheduler | `--json` `--verbose` |
| `resume` | Resume from pause | `--json` `--verbose` |
| `positions` | Open positions via Broker | `--json` `--verbose` |
| `orders` | Order history via Broker | `--json` `--verbose` `--status` |
| `exposure` | Funds and margin via Broker | `--json` `--verbose` |
| `health` | Component health across subsystems | `--json` `--verbose` |
| `report` | Comprehensive operational report | `--json` `--verbose` `--export` |

**Lifecycle Decisions:**

- `start` creates a new `RuntimeEngine` via `create_runtime_engine(config)` and stores it via `set_runtime_engine()`.
- `stop` calls `engine.stop()` then clears the reference with `set_runtime_engine(None)`.
- `pause` calls `engine.pause()` (suspends scheduler) without disconnecting the broker.
- `resume` calls `engine.resume()` (resumes scheduler).
- Each lifecycle step is wrapped in try/except to ensure partial failures don't block cleanup.

**Pre-Flight Validation:**

The `StartupChecklist` runs before `titan live start`:

1. Configuration loaded
2. Broker provider configured
3. Environment validated
4. Production API key present (if production)
5. Risk limits within bounds
6. Monitoring enabled
7. Recovery system available
8. Audit trail enabled
9. Runtime engine available

If any mandatory check fails, startup is aborted with exit code 2. Use `--force` to override.

**Safety Philosophy:**

- Live mode must never start unless all pre-flight checks succeed.
- Each shutdown step is individually try/except guarded.
- The engine reference is always cleared on stop (even if individual subsystem stops fail).
- Audit events record all lifecycle transitions.
- `--dry-run` allows validation without any state changes.

**Rich UI:**

- Tables for structured data (status, positions, orders, exposure, health).
- `Live` animated progress for startup/shutdown sequences.
- Markup-based status indicators.
- Consistent formatting across all commands.

**JSON Support:**

All commands support `--json` for programmatic consumption and automation. JSON output bypasses Rich formatting and returns structured data suitable for monitoring systems, dashboards, and scripts.

### Paper Trading Lifecycle

The `titan paper` command group provides full management of the paper trading session:

- **`start`**: Creates a PaperBroker, connects, starts monitoring. `--dry-run` runs validations only. `--verbose` shows a Rich `Live` progress display with checklist results. `--cash` sets initial balance.
- **`stop`**: Disconnects broker, stops monitoring, clears session state. `--verbose` shows shutdown progress.
- **`restart`**: stop then start.
- **`status`**: Shows session state (cash, portfolio, P&L, positions, performance). `--json` outputs raw JSON. `--verbose` adds performance metrics and positions tables.
- **`reset`**: Resets all paper trading state. `--force` resets even if a session is running.
- **`report`**: Generates comprehensive session report with session summary, portfolio summary, P&L breakdown, performance metrics. `--json` outputs raw JSON. `--verbose` adds positions and orders tables. `--export <path>` exports to JSON or CSV. `--reset` clears state after report.

### Rich Formatting

All output uses Rich for consistent, readable formatting:
- Tables for structured data (status, config).
- Panels for version info, reports.
- Markup-based status indicators (no raw Unicode symbols to avoid cp1252 encoding issues on Windows).
- Consistent key-value table layout via `kv_table()`.
- `Live` display for startup/shutdown progress.

### Standardized Exit Codes

`exit_codes.py` defines 15 exit codes covering all failure modes. Commands return appropriate codes via `errors.py` handlers.

### Backward Compatibility

The entry point `titan = "titan.cli:app"` and `titan/__main__.py` (`from .cli import app`) continue to work identically. The old `cli.py` module was replaced by the `cli/` package with the same public API.

## Consequences

### Positive

- Commands are independently testable via `typer.testing.CliRunner`.
- New command groups can be added without modifying existing modules.
- Shared formatting ensures visual consistency across all commands.
- Shell completion works out of the box via Typer.
- Lazy loading keeps CLI startup fast (< 50ms).
- Runtime lifecycle is fully controllable from the CLI.
- Live trading validation pipeline prevents misconfigurations before they cause failures.
- `--dry-run` enables safe pre-flight checks without side effects.
- `--json` output enables programmatic consumption.
- `--verbose` provides operational visibility without cluttering default output.

### Negative

- Slightly more complex directory structure (15 files vs 1).
- Need to import sub-apps in `__init__.py` for registration.
- Each CLI invocation creates a fresh RuntimeEngine (no persistence across invocations).

### Operations & Administration CLI

The `titan` CLI exposes operational infrastructure through five command groups:

**Recovery** (`titan recovery`): Manages the recovery subsystem — status, retry, checkpoint, restore, circuit breakers. Each command supports `--json` and `--verbose`. Reuses `RecoveryManager`, `CheckpointManager`, `StateManager`, `CircuitBreaker` directly.

**Deployment** (`titan deployment`): Extends existing deployment commands with validate, restore, and health. All commands support `--json` and `--verbose`. Reuses `DeploymentManager`, `EnvironmentManager`, `DeploymentHealthService`.

**Audit** (`titan audit`): Extends existing audit CLI with search, export, and stats. Search supports `--source`, `--category`, `--severity`, `--action`, `--limit` filters. Export supports `--format json|csv` and `--output`. Reuses `AuditManager`, `AuditQuery`, `AuditQueryEngine`.

**Logging** (`titan logs`): Extends existing logs CLI with level, rotate, and clear. Level supports get/set. Rotate renames current log and creates fresh file. Clear truncates with confirmation. Reuses `LoggerManager`.

**Configuration** (`titan config`): Extends existing config CLI with validate, diff, export, and profile. Validate checks all sections. Diff compares against profile defaults. Export saves to JSON/YAML. Profile shows/sets active profile. Reuses `ConfigManager`, `profile_defaults`.

**Architecture Principles:**

- No new business logic — CLI is a thin presentation layer over existing modules.
- All commands follow the same `--json` / `--verbose` convention.
- Shared `formatting.py`, `errors.py`, `exit_codes.py`, `common.py` — zero duplication.
- Recovery is a new command group registered in `__init__.py`.
- All other modules extend existing command files.
- `common.py` provides lazy-loaded singletons for all managers.

### Risks

- Mitigated: Backward compatibility verified - `titan version`, `titan doctor` produce identical output to the old monolithic CLI.
- Mitigated: RuntimeEngine uses PaperBroker by default - no network dependency for CLI testing.
