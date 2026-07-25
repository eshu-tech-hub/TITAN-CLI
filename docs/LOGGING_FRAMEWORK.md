# TITAN Logging Framework

## Overview

The Logging Framework is the single logging authority for TITAN.

Every component obtains its logger from `LoggerManager`. No module
instantiates its own logging configuration or uses Python's `logging`
module directly.

## Architecture

```
Application
    │
    ▼
LoggerManager ─── configure() ─── LoggingConfig
    │
    ├── get_logger() → StructuredLogger
    │       │
    │       ├── .info(), .debug(), .error(), ...
    │       └── LoggingContext (automatic propagation)
    │
    └── Handlers
            ├── ConsoleHandler
            ├── FileHandler (rotating)
            └── JSONFileHandler (rotating, JSONL)
```

## Log Levels

| Level    | Numeric | Use Case                |
|----------|---------|--------------------------|
| TRACE    | 5       | Verbose debugging        |
| DEBUG    | 10      | Development diagnostics  |
| INFO     | 20      | Normal operation         |
| WARNING  | 30      | Unexpected but safe      |
| ERROR    | 40      | Failure, operation deg.  |
| CRITICAL | 50      | System-unstable failure   |

## Structured Log Entry

Every log entry carries:

| Field           | Type     | Source              |
|-----------------|----------|----------------------|
| timestamp       | datetime | auto                 |
| level           | LogLevel | method called        |
| module          | str      | logger module name   |
| component       | str      | logger component     |
| message         | str      | caller               |
| metadata        | dict     | kwargs to log method |
| exception       | str\|None| exc_info parameter   |
| duration_ms     | float\|None| duration() method  |
| pipeline_id     | str\|None| LoggingContext       |
| correlation_id  | str\|None| LoggingContext       |
| request_id      | str\|None| LoggingContext       |
| trade_id        | str\|None| LoggingContext       |
| order_id        | str\|None| LoggingContext       |
| position_id     | str\|None| LoggingContext       |
| runtime_id      | str\|None| LoggingContext       |

## Usage

```python
from titan.logging import LoggerManager, LoggingConfig, HandlerConfig, HandlerType

manager = LoggerManager()

config = LoggingConfig(
    level=LogLevel.INFO,
    handlers=(
        HandlerConfig(handler_type=HandlerType.CONSOLE, level=LogLevel.INFO),
        HandlerConfig(
            handler_type=HandlerType.FILE,
            level=LogLevel.DEBUG,
            file_path="./logs/titan.log",
        ),
    ),
)
manager.configure(config)

logger = manager.get_logger("execution", "order_manager")

# Basic logging
logger.info("Order placed", order_id="ord-123", side="BUY")
logger.warning("Slippage exceeded", expected=0.05, actual=0.12)

# Exception logging
try:
    ...
except ConnectionError as e:
    logger.error("Broker connection failed", exc_info=e)

# Duration tracking
logger.duration("Pipeline run complete", duration_ms=1520.3)

# Context propagation
from titan.logging import LoggingContext
LoggingContext.bind(pipeline_id="pl-001", trade_id="tr-xyz")
logger.info("Processing trade")  # automatically includes context
```

## Context Propagation

`LoggingContext` uses `contextvars` for automatic context propagation
across threads and async tasks:

```python
with LoggingContext.scope(trade_id="tr-789"):
    logger.info("Inside scope")  # includes trade_id

logger.info("Outside scope")  # trade_id not present
```

## Formatters

| Formatter         | Description                          |
|-------------------|--------------------------------------|
| `ConsoleFormatter`| Human-readable, color-coded by level |
| `JSONFormatter`   | Structured JSON, one object per line |
| `CompactFormatter`| Minimal single-line output           |

## Handlers

| Handler            | Sink                  | Rotation |
|--------------------|------------------------|----------|
| `ConsoleHandler`   | stdout / stderr        | N/A      |
| `FileHandler`      | Rotating text file     | Size-based|
| `JSONFileHandler`  | Rotating JSONL file    | Size-based|

## Logging Report

```python
report = manager.generate_report()
report.level              # LogLevel
report.component_count    # Number of registered loggers
report.handlers          # Tuple of HandlerConfig
report.dropped_messages  # Count of messages below handler threshold
```

## Quality

- Frozen dataclasses throughout
- Strict typing (MyPy clean)
- Contextvars-based for thread safety
- Dependency injection (handlers injected into loggers)
- 49+ unit tests, zero I/O in unit tests

## CLI Integration

The logging subsystem is exposed through the `titan logs` command group:

```bash
titan logs show                # Show recent log entries
titan logs show -n 50          # Show last 50 lines
titan logs show --json         # Entries as JSON

titan logs path                # Show log file path
titan logs stats               # Show log file statistics
titan logs stats --json        # Stats as JSON

titan logs level               # Get current log level
titan logs level --json        # Level as JSON
titan logs level DEBUG         # Set log level
titan logs level WARNING       # Set to WARNING

titan logs rotate              # Rotate log files
titan logs rotate --json       # Rotate as JSON

titan logs clear               # Clear log file (with confirmation)
titan logs clear --force       # Clear without confirmation
titan logs clear --force --json  # Clear as JSON
```

### Log Rotation

The `rotate` command:
1. Renames the current log file to `.log.1`
2. Creates a new empty log file
3. Reports the previous file size

### Log Clearing

The `clear` command truncates the current log file. Use `--force` to skip confirmation prompt. Use `--json` to skip confirmation automatically.
