# ADR-034: TUI

## Status

Accepted

## Date

2026-07-11

## Updated

2026-07-13 — Added Runtime screen (M8.2.3), Paper Trading screen (M8.2.4), Shell & Navigation (M8.2.5), Market Intelligence screen (M8.2.6)
2026-07-14 — Added Monitoring & Alerting screen (M8.2.8)

## Context

TITAN needs a real-time terminal dashboard to monitor system health without relying on external tools or log parsing. The CLI provides point-in-time status via `titan status`, but operators need continuous visibility into runtime, market connectivity, trading state, alerts, and system deployment.

Requirements:
- Refresh automatically every second.
- Display status across five screens: Dashboard (overview), Runtime (detailed), Paper Trading (live session monitoring), Market Intelligence (real-time market microstructure), and Monitoring & Alerting (operational health).
- Read-only access to all managers (no side effects).
- Resilient to unavailable managers (show defaults).
- Testable without running the full system.

## Decision

### Textual Framework

Use Textual for the TUI framework. Textual provides:
- CSS-based styling with `$surface`, `$primary`, `$success`, `$error`, `$warning` variables.
- `App.run_test()` for headless async testing.
- `Screen` and `Widget` abstractions for layout.
- Timer-based auto-refresh via `set_interval()`.

### Frozen Dataclass DTOs

Define immutable snapshot dataclasses for each screen:
- **Dashboard**: `DashboardState` with `RuntimeInfo`, `MarketInfo`, `TradingInfo`, `HealthInfo`, `SystemInfo`.
- **Runtime**: `RuntimeScreenState` with `RuntimeEngineInfo`, `RuntimeStreamInfo`, `RuntimePipelineInfo`, `RuntimeEventBusInfo`, `RuntimeComponentInfo`, `RuntimeEventEntry`.
- **Paper Trading**: `PaperScreenState` with `PaperSessionInfo`, `PaperAccountInfo`, `PaperPortfolioInfo`, `PaperPerformanceInfo`, `PaperPositionEntry`, `PaperOrderEntry`, `PaperTradeEntry`.
- **Market Intelligence**: `MarketScreenState` with `MarketStatusInfo`, `MarketStructureInfo`, `TrendInfo`, `BreadthInfo`, `VolumeInfo`, `VWAPInfo`, `MarketRegimeInfo`, `MarketSignal`.
- **Monitoring & Alerting**: `MonitoringScreenState` with `SystemHealthInfo`, `TelemetryInfo`, `ResourceMetricsInfo`, `AlertSummaryInfo`, `AlertEntry`, `AlertHistoryEntry`, `RecoveryStatusInfo`, `MonitoringEventEntry`.

Frozen ensures immutability: widgets receive a snapshot and cannot corrupt manager state.

### Read-Only State Builders

`build_dashboard_state()`, `build_runtime_state()`, `build_paper_state()`, `build_market_state()`, and `build_monitoring_state()` read all managers with `try/except` on every access. If a manager is unavailable, defaults are used. This makes the TUI resilient to partial system initialization.

### Screen-per-Page Architecture

`TITANApp` is the root `App` subclass. Navigation via `push_screen()` / `pop_screen()`:
- `F1` -> DashboardScreen
- `F2` -> RuntimeScreen
- `F3` -> PaperScreen
- `F6` -> MonitoringScreen

### Widget Composition Pattern

Each widget:
- Extends `Widget` (not `Static`) to support child composition.
- Uses `compose()` to yield `Static` children with CSS classes.
- `update_data(InfoDataclass)` updates the Static children via `update()`.
- `render()` returns `""` — children handle visual output.

Dynamic widgets (`HealthWidget`, `RuntimeEventsWidget`) use `mount()` / `remove()` for variable-length content.

### Runtime Screen

The Runtime screen provides six widgets for deep runtime introspection:
1. **RuntimeStatusWidget** — Engine status, uptime, scheduler state.
2. **StreamWidget** — Market stream connectivity, symbols tracked, tick rate.
3. **PipelineWidget** — Execution count, average runtime, last run time.
4. **EventBusWidget** — Published events, subscriber count.
5. **HealthWidget** — Dynamic component health grid.
6. **RuntimeEventsWidget** — Scrollable recent event history.

PgUp/PgDn bindings scroll the event history widget.

### Paper Trading Screen

The Paper Trading screen provides seven widgets for live paper trading session monitoring:
1. **PaperSessionWidget** — Session status, uptime, mode indicator.
2. **AccountSummaryWidget** — Available cash, used/available margin, payin/payout.
3. **PortfolioWidget** — Cash, equity, unrealized/realized P&L.
4. **PositionWidget** — Dynamic open positions table.
5. **ActiveOrdersWidget** — Dynamic pending/open orders table.
6. **PerformanceWidget** — Win rate, profit factor, expectancy, max drawdown.
7. **TradeHistoryWidget** — Dynamic last 20 closed trades.

Paper broker is accessed via `_get_broker()` imported from `titan.cli.commands.paper`. The `PaperBroker` singleton manages the paper session. F3 key switches to this screen. PgUp/PgDn/Home/End scroll through positions, orders, and trades.

### Monitoring & Alerting Screen (M8.2.8)

The Monitoring & Alerting screen provides eight widgets for real-time operational monitoring:
1. **SystemHealthWidget** — Overall health status, subsystem health grid (dynamic).
2. **TelemetryWidget** — Metrics count, active collectors, collections, uptime.
3. **AlertSummaryWidget** — Alert counts by status (active, critical, acknowledged, resolved).
4. **RecoveryStatusWidget** — Recovery status, attempts, last strategy, recovered components.
5. **MetricsWidget** — Resource metrics table (dynamic).
6. **ActiveAlertsWidget** — Active alerts list (dynamic).
7. **AlertHistoryWidget** — Alert history list (dynamic).
8. **MonitoringEventsWidget** — Monitoring events list (dynamic).

Data sources: `MonitoringManager`, `AlertManager`, `RecoveryManager` via `titan.cli.common`. F6 key switches to this screen. PgUp/PgDn scroll through alerts, history, and events. Sidebar entry merged: "Monitoring & Alerting" replaces separate "Monitoring" and "Alerts" entries.

### Application Shell & Navigation (M8.2.5)

`ShellApp` replaces the flat `TITANApp` with a persistent institutional desktop shell:
- **Header** (top): Version, hostname, profile, uptime, runtime indicator, clock
- **Sidebar** (left): Sections (Dashboard, Runtime, Paper Trading, Live Trading, Monitoring & Alerting, Logs, Audit, Configuration, Deployment, Help) with separators, keyboard/mouse navigation, and active highlight
- **Content** (center): Screen content via `push_screen()`
- **Status bar** (bottom): Environment, runtime status, broker status, mode, refresh interval, clock

Navigation is centralized through `ScreenRouter`:
- **Lazy creation**: Screens created on first visit, cached thereafter
- **History stack**: Each non-default navigation pushes the current screen; `go_back()` pops it
- **Home reset**: Navigating to the default screen clears history
- **Invalidate**: Force screen recreation on next visit

F1–F11 keys navigate between screens. Escape returns to the previous screen. Ctrl+R refreshes the current screen. Ctrl+Q quits.

`ThemeColors` provides DARK and LIGHT preset themes, accessible via `get_theme()` / `set_theme()`.

## Consequences

### Positive
- Real-time monitoring without leaving the terminal.
- No side effects on managers — safe for production use.
- Resilient to partial system state.
- Fully testable: unit tests for models/widgets, async tests for screens.
- Four-screen architecture: overview, runtime introspection, live paper trading, and help reference.
- Five-screen architecture: overview, runtime introspection, live paper trading, market intelligence, monitoring & alerting.
- Institutional desktop shell with persistent header/sidebar/status bar.
- Centralized navigation with history stack and back-navigation.

### Negative
- Adds `textual` dependency (mitigated: already a dev dependency).
- 1-second refresh may impact CPU on slow terminals (mitigated: configurable interval).
- ShellApp adds complexity over flat TITANApp (mitigated: clean separation of concerns).

### Neutral
- Future screens follow the same Screen + widget pattern.
- Keyboard bindings are consistent across screens.

## Alternatives Considered

1. **Rich Live display**: Rejected — no persistent layout, no keyboard navigation.
2. **Curses-based**: Rejected — no CSS styling, harder to maintain.
3. **Web dashboard**: Deferred — requires HTTP server, not pure terminal.

- Configuration & Deployment Screen implemented in M8.2.10.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.
