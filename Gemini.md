# TITAN-CLI Context & Rules

## 1. System Architecture
* **Purpose**: TITAN is an institutional-grade, event-driven quantitative trading framework and TUI (Text User Interface).
* **Core Components**: Runtime Engine, Paper Broker, Pipeline Scheduler, Portfolio Analytics, and Textual-based TUI.
* **Paradigm**: 100% research-to-live parity. Backtesting and live trading must use the exact same state machine and execution logic.

## 2. Coding Standards & Safety
* **Immutability**: Always use strictly typed, frozen dataclasses for data models (e.g., `FundsInfo`, `MarginInfo`, `ComponentHealth`).
* **State Management**: The `RuntimeEngine` is the single source of truth for the system state (`STOPPED` -> `STARTING` -> `RUNNING` -> `STOPPING` -> `STOPPED`).
* **Graceful Degradation**: TUI layout parsers must use safe `hasattr()` or `getattr()` checks with default fallbacks to prevent screen crashes. Do not use blank `except Exception:` blocks to silently swallow errors.

## 3. Testing Rules
* **No Broken Tests**: TITAN currently has 4,700+ passing tests. No code modifications are permitted if they break existing backwards compatibility.
* **Mocking**: When writing tests for the CLI or TUI, use real domain objects (dataclasses) whenever possible. Avoid deeply nested `MagicMock` hacks that conflict with strict Enum evaluations.

## 4. Workflows & Execution Gates
* **Plan Before Code**: Always investigate the root cause and propose a clear architectural plan before implementing any code changes.
* **IPC (Inter-Process Communication)**: Background daemon teardowns (like `titan runtime stop`) must always be non-blocking. Enforce strict timeouts (e.g., 2.0s) on thread `.join()` operations to prevent the CLI from hanging.