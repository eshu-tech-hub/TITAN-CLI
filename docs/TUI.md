# TITAN TUI

Terminal User Interface for real-time system monitoring via Textual.

## Architecture

```
titan/tui/
    __init__.py              # Package init
    models.py                # All frozen dataclasses (Dashboard, Runtime, Paper, Market, Monitoring)
    layout.py                # TITANApp (main Textual App) + state builders
    theme.py                 # ThemeColors (DARK, LIGHT presets), get_theme/set_theme
    router.py                # ScreenRouter (registration, lazy creation, history, back-nav)
    shell.py                 # ShellApp (institutional desktop shell)
    screens/
        __init__.py
        dashboard.py         # DashboardScreen with auto-refresh
        runtime.py           # RuntimeScreen with auto-refresh
        paper.py             # PaperScreen with auto-refresh
        help.py              # HelpScreen — keyboard shortcuts reference
        market.py            # MarketScreen with auto-refresh
        monitor.py           # MonitoringScreen with auto-refresh
    widgets/
        __init__.py
        header.py            # HeaderWidget (version, hostname, uptime, clock)
        sidebar.py           # SidebarWidget (sections, active highlight)
        status_bar.py        # StatusBarWidget (env, runtime, broker, mode, time)
        runtime_card.py      # Runtime status card (Dashboard)
        market_card.py       # Broker/stream connectivity card (Dashboard)
        trading_card.py      # Trading mode card (Dashboard)
        health_card.py       # Alerts, monitoring, recovery card (Dashboard)
        system_card.py       # Version, environment, deployment card (Dashboard)
        runtime.py           # 6 widgets for Runtime screen
        paper.py             # 7 widgets for Paper Trading screen
        market.py            # 8 widgets for Market Intelligence screen
        live.py              # 8 widgets for Live Trading screen
        monitor.py           # 8 widgets for Monitoring & Alerting screen
```

## Application Shell (M8.2.5)

`ShellApp` in `shell.py` provides the unified institutional desktop layout:

- **Header** (top, 1 row): TITAN version, hostname, profile, uptime, runtime indicator, clock
- **Sidebar** (left, 24 cols): 15 sections with keyboard/mouse navigation and active highlight
- **Content** (center): Screen content via `push_screen()`
- **Status bar** (bottom, 1 row): Environment, runtime status, broker status, mode, refresh interval, clock

### Navigation

| Key | Action |
|-----|--------|
| F1 | Dashboard |
| F2 | Runtime |
| F3 | Paper Trading |
| F4 | Market Intelligence |
| F5 | Live Trading |
| F6 | Monitoring & Alerting |
| F11 | Help |
| Escape | Previous screen (go back) |
| Ctrl+R | Refresh current screen |
| Ctrl+Q | Quit |

### Screen Router

`ScreenRouter` manages screen registration, lazy creation, and back-navigation history:
- `register(name, factory)`: Register a screen factory
- `navigate(name)`: Push current to history, switch to target
- `go_back()`: Pop history, switch to previous screen
- `can_go_back()`: Check if history is non-empty
- `invalidate(name)`: Clear cache to force recreation
- Navigating to the default screen clears history (home resets state)

### Theme

`ThemeColors` dataclass with DARK and LIGHT presets. Access via `get_theme()` / `set_theme()`.

## Screens

### Dashboard Screen (F1)

Five status cards: Runtime, Market, Trading, Health, System.

### Runtime Screen (F2)

Six detailed widgets for runtime introspection:

| Widget | Description |
|--------|-------------|
| `RuntimeStatusWidget` | Engine status, uptime, scheduler state |
| `StreamWidget` | Market stream connectivity, symbols, tick rate |
| `PipelineWidget` | Execution count, average runtime, last run |
| `EventBusWidget` | Published events, subscriber count |
| `HealthWidget` | Component health grid (dynamic) |
| `RuntimeEventsWidget` | Recent runtime event history (dynamic) |

### Paper Trading Screen (F3)

Seven widgets for live paper trading session monitoring:

| Widget | Description |
|--------|-------------|
| `PaperSessionWidget` | Session status, uptime, mode indicator |
| `AccountSummaryWidget` | Available cash, used/available margin, payin/payout |
| `PortfolioWidget` | Cash, equity, unrealized/realized P&L |
| `PositionWidget` | Open positions table (dynamic) |
| `ActiveOrdersWidget` | Pending/open orders table (dynamic) |
| `PerformanceWidget` | Win rate, profit factor, expectancy, max drawdown |
| `TradeHistoryWidget` | Last 20 closed trades (dynamic) |

### Help Screen (F11)

Keyboard shortcuts reference. Escape/Q/F11 returns to previous screen.

### Market Intelligence Screen (F4)

Eight widgets for real-time market microstructure monitoring:

| Widget | Description |
|--------|-------------|
| `MarketStatusWidget` | Exchange status, trading session, market hours |
| `MarketStructureWidget` | Trend, bias, momentum, breadth, ATR, ADX |
| `TrendWidget` | Short/medium/long trend, strength, RSI, MACD |
| `BreadthWidget` | Advance/decline, new highs/lows, A/D ratio |
| `VolumeWidget` | Total/average volume, volume ratio |
| `VWAPWidget` | VWAP value, session high/low VWAP, deviation |
| `RegimeWidget` | Volatility regime, mean-reversion, dispersion |
| `RecentSignalsWidget` | Last 20 market intelligence signals (dynamic) |

Market analyzers are instance-based singletons (`get_<analyzer>()`). Read from `titan.market.analyzers.<module>` — the pipeline has no cached results. PgUp/PgDn scroll the recent signals widget.

### Monitoring & Alerting Screen (F6)

Eight widgets for real-time operational monitoring:

| Widget | Description |
|--------|-------------|
| `SystemHealthWidget` | Overall health, subsystem statuses (dynamic list) |
| `TelemetryWidget` | Metrics count, collectors, collections, uptime |
| `AlertSummaryWidget` | Alert counts by status (active, critical, acknowledged, resolved) |
| `RecoveryStatusWidget` | Recovery status, attempts, strategy, recovered components |
| `MetricsWidget` | Resource metrics table (dynamic list) |
| `ActiveAlertsWidget` | Active alerts list (dynamic) |
| `AlertHistoryWidget` | Alert history list (dynamic) |
| `MonitoringEventsWidget` | Monitoring events list (dynamic) |

Data sources: `MonitoringManager`, `AlertManager`, `RecoveryManager` via `titan.cli.common`. PgUp/PgDn scroll through alerts, history, and events.

## Data Flow

```
build_dashboard_state()          # Reads all managers (read-only)
    -> DashboardState            # Frozen dataclass snapshot
    -> DashboardScreen._update_widgets()
    -> CardWidget.update_data()

build_runtime_state()            # Reads all managers (read-only)
    -> RuntimeScreenState        # Frozen dataclass snapshot
    -> RuntimeScreen._update_widgets()
    -> Widget.update_data()

build_paper_state()              # Reads PaperBroker (read-only)
    -> PaperScreenState          # Frozen dataclass snapshot
    -> PaperScreen._update_widgets()
    -> Widget.update_data()

build_market_state()             # Reads market analyzers (read-only)
    -> MarketScreenState         # Frozen dataclass snapshot
    -> MarketScreen._update_widgets()
    -> Widget.update_data()

build_monitoring_state()         # Reads monitoring/alerting/recovery managers (read-only)
    -> MonitoringScreenState     # Frozen dataclass snapshot
    -> MonitoringScreen._update_widgets()
    -> Widget.update_data()
```

All data flows **read-only** from managers to widgets. TUI never mutates manager state.

## State Builder

### Dashboard

`build_dashboard_state()` in `layout.py` collects data from:

- `get_runtime_engine()` -> RuntimeInfo
- `get_monitoring_manager()` -> HealthInfo (monitoring_status)
- `get_alert_manager()` -> HealthInfo (alerts)
- `get_recovery_manager()` -> HealthInfo (recovery)
- `get_deployment_manager()` -> SystemInfo

### Runtime

`build_runtime_state()` in `layout.py` collects data from:

- `get_runtime_engine()` -> RuntimeEngineInfo, RuntimeStreamInfo, RuntimePipelineInfo, RuntimeEventBusInfo, RuntimeComponentInfo, RuntimeEventEntry
- `get_recovery_manager()` -> RuntimeEventEntry (recovery events)

### Paper Trading

`build_paper_state()` in `layout.py` collects data from:

- `_get_broker()` -> PaperBroker
- `broker.is_connected()` -> session active
- `broker.funds()` -> PaperAccountInfo (cash, margin, payin, payout)
- `broker.margin()` -> PaperAccountInfo (used/available margin)
- `broker.position_engine.open_positions()` -> PaperPositionEntry list
- `broker.portfolio.compute_state()` -> PaperPortfolioInfo
- `broker.performance.compute()` -> PaperPerformanceInfo
- `broker.orders()` -> PaperOrderEntry list (pending/open only)
- `broker.journal.to_broker_trades()` -> PaperTradeEntry list (last 20)

Each access is `try/except` guarded. Falls back to defaults when broker is unavailable.

Each manager access is `try/except` guarded. If a manager is unavailable, widgets render defaults.

### Market Intelligence

`build_market_state()` in `layout.py` reads instance-based market analyzers from `titan.market.analyzers`:

- `get_market_status_analyzer()` -> MarketStatusAnalyzer
- `get_market_structure_analyzer()` -> MarketStructureAnalyzer
- `get_trend_analyzer()` -> TrendAnalyzer
- `get_market_breadth_analyzer()` -> MarketBreadthAnalyzer
- `get_volume_analyzer()` -> VolumeAnalyzer
- `get_vwap_analyzer()` -> VWAPAnalyzer
- `get_market_regime_analyzer()` -> MarketRegimeAnalyzer
- `get_market_intelligence_service()` -> MarketIntelligenceService (recent signals)

Each access is `try/except` guarded. Falls back to defaults when analyzers are unavailable.

Inject a custom builder via `app.set_state_builder(fn)`, `app.set_runtime_state_builder(fn)`, `app.set_paper_state_builder(fn)`, `app.set_market_state_builder(fn)`, or `app.set_monitoring_state_builder(fn)` for testing.

### Monitoring & Alerting

`build_monitoring_state()` in `layout.py` collects data from:

- `get_monitoring_manager().health.evaluate()` -> SystemHealthInfo
- `get_monitoring_manager().dashboard_status()` -> TelemetryInfo, ResourceMetricsInfo
- `get_alert_manager().generate_report()` -> AlertSummaryInfo
- `get_alert_manager().get_active_alerts()` -> AlertEntry tuple
- `get_alert_manager().history.all_entries()` -> AlertHistoryEntry tuple
- `get_recovery_manager().generate_report()` -> RecoveryStatusInfo
- `get_recovery_manager().get_recovery_history()` -> RecoveryStatusInfo (last strategy)
- Monitoring warnings + recovery history + alert warnings -> MonitoringEventEntry tuple

Each access is `try/except` guarded. Falls back to defaults when managers are unavailable.

## Refresh Lifecycle

1. Screen `on_mount()` starts a 1-second interval timer.
2. `_tick_refresh()` calls `_refresh_state()`.
3. `_refresh_state()` calls the state builder, then pushes the result to all widgets.
4. Manual refresh via `r` key or `action_refresh()`.

No blocking operations. No custom polling threads.

## Keyboard Bindings

| Key | Action | Scope |
|-----|--------|-------|
| `q` | Quit | App + Screen |
| `r` | Refresh | Screen |
| `escape` | Back / Quit | Screen / App |
| `F1` | Dashboard | ShellApp |
| `F2` | Runtime | ShellApp |
| `F3` | Paper Trading | ShellApp |
| `F4` | Market Intelligence | ShellApp |
| `F5` | Live Trading | ShellApp |
| `F6` | Monitoring & Alerting | ShellApp |
| `F11` | Help | ShellApp |
| `Ctrl+R` | Refresh current screen | ShellApp |
| `Ctrl+Q` | Quit | ShellApp |
| `up/down` | Focus navigation | App |
| `page_up` | Scroll events/positions/signals/alerts | Screen |
| `page_down` | Scroll events/positions/signals/alerts | Screen |
| `home` | Jump to top | PaperScreen / MarketScreen / MonitoringScreen |
| `end` | Jump to bottom | PaperScreen / MarketScreen / MonitoringScreen |
| `enter` | Select (placeholder) | App |

## Widget Pattern

Each widget:
- Extends `textual.widget.Widget`
- Uses `compose()` to yield `Static` children
- Implements `update_data(InfoDataclass)` to update children
- `render()` returns `""` (children handle visual output)
- CSS: `$surface` background, `$primary` border, `height: auto`, `min-height` for card size

Dynamic widgets (`HealthWidget`, `RuntimeEventsWidget`, `PositionWidget`, `ActiveOrdersWidget`, `TradeHistoryWidget`, `RecentSignalsWidget`) maintain `_rows` lists and use `mount()` / `remove()` to update child widgets.

## Testing

- Unit tests: models, widget rendering, format helpers, screen state management
- Async tests: `App.run_test()` headless mode (requires `pytest-asyncio`)
- Tests are in `tests/test_tui_dashboard.py`, `tests/test_tui_runtime.py`, `tests/test_tui_paper.py`, `tests/test_tui_navigation.py`, `tests/test_tui_market.py`, and `tests/test_tui_monitor.py`

## Running

```bash
titan tui           # (when CLI command is added)
# or directly:
python -m titan.tui.layout
# or institutional desktop:
python -m titan.tui.shell
```

## Configuration & Deployment Screen
Accessible via F7, provides a read-only view of configuration, environment, and deployment status.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.
