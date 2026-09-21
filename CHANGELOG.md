# TITAN Changelog

## [1.0.0-rc1] - 2026-07-16
### Added
- **M1:** Core CLI framework leveraging Typer and Rich.
- **M2:** Base RuntimeEngine and EventBus for orchestrating algorithmic pipelines.
- **M3:** YFinance integration and generic Broker interface for live trading execution.
- **M4:** Market intelligence layer including Option Greeks and regime analysis (Charm, Vanna).
- **M5:** Decision Engine with deterministic signal constraints and consensus logic.
- **M6:** Trade and Decision Journaling with local persistence.
- **M7:** TUI layer leveraging Textual for real-time visual telemetry.
- **M8:** Institutional hardening, including `RuntimeSupervisor`, synchronous watchdogs, escalating recoveries (Levels 1-4), configuration validation, and production readiness reporting.

### Changed
- Refactored legacy `HeartbeatMonitor` to a static, synchronous `HeartbeatRegistry`.
- Refined TUI Configuration screens to display real-time validation warnings.
- Switched dependency requirements to strictly enforce Python 3.14.

### Removed
- Eliminated all arbitrary background polling threads to guarantee determinism.
