"""Tests for TITAN TUI Runtime screen — models, widgets, helpers, screen, app."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest

from titan.tui.layout import (
    TITANApp,
    _format_relative_time,
    _format_uptime,
    _read_runtime_components,
    _read_runtime_engine,
    _read_runtime_event_bus,
    _read_runtime_events,
    _read_runtime_pipeline,
    _read_runtime_stream,
    build_runtime_state,
)
from titan.tui.models import (
    RuntimeComponentInfo,
    RuntimeEngineInfo,
    RuntimeEventBusInfo,
    RuntimeEventEntry,
    RuntimePipelineInfo,
    RuntimeScreenState,
    RuntimeStreamInfo,
)
from titan.tui.screens.runtime import RuntimeScreen
from titan.tui.widgets.runtime import (
    EventBusWidget,
    HealthWidget,
    PipelineWidget,
    RuntimeEventsWidget,
    RuntimeStatusWidget,
    StreamWidget,
    _event_level_class,
    _health_class,
    _status_class,
)

# ──────────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────────


class TestRuntimeEngineInfo:
    def test_defaults(self) -> None:
        info = RuntimeEngineInfo()
        assert info.status == "Unknown"
        assert info.uptime == "00:00:00"
        assert info.is_running is False
        assert info.scheduler_active is False

    def test_custom(self) -> None:
        info = RuntimeEngineInfo(
            status="RUNNING",
            uptime="03:42:18",
            is_running=True,
            scheduler_active=True,
        )
        assert info.status == "RUNNING"
        assert info.uptime == "03:42:18"
        assert info.is_running is True
        assert info.scheduler_active is True

    def test_frozen(self) -> None:
        info = RuntimeEngineInfo()
        with pytest.raises(AttributeError):
            info.status = "STOPPED"  # type: ignore[misc]


class TestRuntimeStreamInfo:
    def test_defaults(self) -> None:
        info = RuntimeStreamInfo()
        assert info.connected is False
        assert info.symbols_tracked == 0
        assert info.tick_rate == "N/A"

    def test_custom(self) -> None:
        info = RuntimeStreamInfo(
            connected=True,
            symbols_tracked=24,
            tick_rate="10/sec",
        )
        assert info.connected is True
        assert info.symbols_tracked == 24
        assert info.tick_rate == "10/sec"

    def test_frozen(self) -> None:
        info = RuntimeStreamInfo()
        with pytest.raises(AttributeError):
            info.connected = True  # type: ignore[misc]


class TestRuntimePipelineInfo:
    def test_defaults(self) -> None:
        info = RuntimePipelineInfo()
        assert info.executions == 0
        assert info.avg_runtime == "N/A"
        assert info.last_run == "Never"

    def test_custom(self) -> None:
        info = RuntimePipelineInfo(
            executions=1248, avg_runtime="18 ms", last_run="0.8 sec ago"
        )
        assert info.executions == 1248
        assert info.avg_runtime == "18 ms"
        assert info.last_run == "0.8 sec ago"

    def test_frozen(self) -> None:
        info = RuntimePipelineInfo()
        with pytest.raises(AttributeError):
            info.executions = 1  # type: ignore[misc]


class TestRuntimeEventBusInfo:
    def test_defaults(self) -> None:
        info = RuntimeEventBusInfo()
        assert info.published == 0
        assert info.subscribers == 0

    def test_custom(self) -> None:
        info = RuntimeEventBusInfo(published=500, subscribers=12)
        assert info.published == 500
        assert info.subscribers == 12

    def test_frozen(self) -> None:
        info = RuntimeEventBusInfo()
        with pytest.raises(AttributeError):
            info.published = 1  # type: ignore[misc]


class TestRuntimeComponentInfo:
    def test_defaults(self) -> None:
        info = RuntimeComponentInfo()
        assert info.name == ""
        assert info.status == "Unknown"

    def test_custom(self) -> None:
        info = RuntimeComponentInfo(name="Runtime", status="healthy")
        assert info.name == "Runtime"
        assert info.status == "healthy"

    def test_frozen(self) -> None:
        info = RuntimeComponentInfo()
        with pytest.raises(AttributeError):
            info.name = "X"  # type: ignore[misc]


class TestRuntimeEventEntry:
    def test_defaults(self) -> None:
        entry = RuntimeEventEntry()
        assert entry.level == "info"
        assert entry.source == ""
        assert entry.message == ""

    def test_custom(self) -> None:
        entry = RuntimeEventEntry(level="error", source="pipeline", message="Timeout")
        assert entry.level == "error"
        assert entry.source == "pipeline"
        assert entry.message == "Timeout"

    def test_frozen(self) -> None:
        entry = RuntimeEventEntry()
        with pytest.raises(AttributeError):
            entry.level = "warn"  # type: ignore[misc]


class TestRuntimeScreenState:
    def test_defaults(self) -> None:
        state = RuntimeScreenState()
        assert isinstance(state.engine, RuntimeEngineInfo)
        assert isinstance(state.stream, RuntimeStreamInfo)
        assert isinstance(state.pipeline, RuntimePipelineInfo)
        assert isinstance(state.event_bus, RuntimeEventBusInfo)
        assert state.components == ()
        assert state.events == ()
        assert state.last_refresh == ""

    def test_frozen(self) -> None:
        state = RuntimeScreenState()
        with pytest.raises(AttributeError):
            state.last_refresh = "12:00"  # type: ignore[misc]

    def test_with_components(self) -> None:
        comps = (RuntimeComponentInfo(name="RT", status="healthy"),)
        state = RuntimeScreenState(components=comps)
        assert len(state.components) == 1
        assert state.components[0].name == "RT"

    def test_with_events(self) -> None:
        events = (RuntimeEventEntry(level="warning", message="test"),)
        state = RuntimeScreenState(events=events)
        assert len(state.events) == 1
        assert state.events[0].message == "test"


# ──────────────────────────────────────────────────
# Helper function tests
# ──────────────────────────────────────────────────


class TestStatusClass:
    def test_running(self) -> None:
        assert _status_class("RUNNING") == "value-running"

    def test_stopped(self) -> None:
        assert _status_class("STOPPED") == "value-stopped"

    def test_paused(self) -> None:
        assert _status_class("PAUSED") == "value-paused"

    def test_unknown(self) -> None:
        assert _status_class("UNKNOWN") == "value-default"

    def test_connected(self) -> None:
        assert _status_class("Connected") == "value-running"

    def test_error(self) -> None:
        assert _status_class("error") == "value-stopped"

    def test_starting(self) -> None:
        assert _status_class("starting") == "value-paused"


class TestHealthClass:
    def test_healthy(self) -> None:
        assert _health_class("healthy") == "value-healthy"

    def test_ok(self) -> None:
        assert _health_class("ok") == "value-healthy"

    def test_degraded(self) -> None:
        assert _health_class("degraded") == "value-degraded"

    def test_warning(self) -> None:
        assert _health_class("warning") == "value-degraded"

    def test_unhealthy(self) -> None:
        assert _health_class("unhealthy") == "value-unhealthy"

    def test_critical(self) -> None:
        assert _health_class("critical") == "value-unhealthy"

    def test_unknown(self) -> None:
        assert _health_class("unknown") == "value-unknown"

    def test_empty(self) -> None:
        assert _health_class("") == "value-unknown"


class TestEventLevelClass:
    def test_error(self) -> None:
        assert _event_level_class("error") == "event-error"

    def test_critical(self) -> None:
        assert _event_level_class("critical") == "event-error"

    def test_warning(self) -> None:
        assert _event_level_class("warning") == "event-warning"

    def test_warn(self) -> None:
        assert _event_level_class("warn") == "event-warning"

    def test_info(self) -> None:
        assert _event_level_class("info") == "event-info"

    def test_empty(self) -> None:
        assert _event_level_class("") == "event-info"


class TestFormatUptime:
    def test_zero(self) -> None:
        assert _format_uptime(0) == "00:00:00"

    def test_seconds_only(self) -> None:
        assert _format_uptime(59) == "00:00:59"

    def test_minutes_and_seconds(self) -> None:
        assert _format_uptime(90) == "00:01:30"

    def test_hours_minutes_seconds(self) -> None:
        assert _format_uptime(3661) == "01:01:01"

    def test_large(self) -> None:
        assert _format_uptime(86400) == "24:00:00"


class TestFormatRelativeTime:
    def test_none(self) -> None:
        assert _format_relative_time(None) == "Never"

    def test_just_now(self) -> None:
        from datetime import datetime, timedelta

        dt = datetime.now(UTC) - timedelta(microseconds=1)
        assert _format_relative_time(dt) == "Just now"

    def test_recent(self) -> None:
        from datetime import datetime, timedelta

        dt = datetime.now(UTC) - timedelta(seconds=0.5)
        assert _format_relative_time(dt) == "< 1 sec ago"

    def test_seconds_ago(self) -> None:
        from datetime import datetime, timedelta

        dt = datetime.now(UTC) - timedelta(seconds=30)
        result = _format_relative_time(dt)
        assert "sec ago" in result

    def test_minutes_ago(self) -> None:
        from datetime import datetime, timedelta

        dt = datetime.now(UTC) - timedelta(minutes=5)
        result = _format_relative_time(dt)
        assert "min ago" in result

    def test_hours_ago(self) -> None:
        from datetime import datetime, timedelta

        dt = datetime.now(UTC) - timedelta(hours=3)
        result = _format_relative_time(dt)
        assert "hr ago" in result


# ──────────────────────────────────────────────────
# Widget tests
# ──────────────────────────────────────────────────


class TestRuntimeStatusWidget:
    def test_init(self) -> None:
        w = RuntimeStatusWidget()
        assert w._info.status == "Unknown"

    def test_update_data_running(self) -> None:
        w = RuntimeStatusWidget()
        info = RuntimeEngineInfo(
            status="RUNNING", uptime="03:42:18", scheduler_active=True
        )
        w.update_data(info)
        assert w._info.status == "RUNNING"

    def test_update_data_stopped(self) -> None:
        w = RuntimeStatusWidget()
        info = RuntimeEngineInfo(status="STOPPED", is_running=False)
        w.update_data(info)
        assert w._info.status == "STOPPED"

    def test_update_data_paused(self) -> None:
        w = RuntimeStatusWidget()
        info = RuntimeEngineInfo(
            status="PAUSED", is_running=False, scheduler_active=False
        )
        w.update_data(info)
        assert w._info.status == "PAUSED"
        assert w._info.scheduler_active is False

    def test_render_returns_empty_string(self) -> None:
        w = RuntimeStatusWidget()
        assert w.render() == ""


class TestStreamWidget:
    def test_init(self) -> None:
        w = StreamWidget()
        assert w._info.connected is False

    def test_update_data_connected(self) -> None:
        w = StreamWidget()
        info = RuntimeStreamInfo(connected=True, symbols_tracked=24, tick_rate="10/sec")
        w.update_data(info)
        assert w._info.connected is True
        assert w._info.symbols_tracked == 24
        assert w._info.tick_rate == "10/sec"

    def test_update_data_disconnected(self) -> None:
        w = StreamWidget()
        info = RuntimeStreamInfo(connected=False, symbols_tracked=0)
        w.update_data(info)
        assert w._info.connected is False

    def test_update_data_default_tick_rate(self) -> None:
        w = StreamWidget()
        info = RuntimeStreamInfo()
        w.update_data(info)
        assert w._info.tick_rate == "N/A"

    def test_render_returns_empty_string(self) -> None:
        w = StreamWidget()
        assert w.render() == ""


class TestPipelineWidget:
    def test_init(self) -> None:
        w = PipelineWidget()
        assert w._info.executions == 0

    def test_update_data(self) -> None:
        w = PipelineWidget()
        info = RuntimePipelineInfo(
            executions=1248, avg_runtime="18 ms", last_run="0.8 sec ago"
        )
        w.update_data(info)
        assert w._info.executions == 1248
        assert w._info.avg_runtime == "18 ms"
        assert w._info.last_run == "0.8 sec ago"

    def test_update_data_default_avg_runtime(self) -> None:
        w = PipelineWidget()
        info = RuntimePipelineInfo()
        w.update_data(info)
        assert w._info.avg_runtime == "N/A"

    def test_render_returns_empty_string(self) -> None:
        w = PipelineWidget()
        assert w.render() == ""


class TestEventBusWidget:
    def test_init(self) -> None:
        w = EventBusWidget()
        assert w._info.published == 0
        assert w._info.subscribers == 0

    def test_update_data(self) -> None:
        w = EventBusWidget()
        info = RuntimeEventBusInfo(published=500, subscribers=12)
        w.update_data(info)
        assert w._info.published == 500
        assert w._info.subscribers == 12

    def test_update_data_defaults(self) -> None:
        w = EventBusWidget()
        info = RuntimeEventBusInfo()
        w.update_data(info)
        assert w._info.published == 0
        assert w._info.subscribers == 0

    def test_render_returns_empty_string(self) -> None:
        w = EventBusWidget()
        assert w.render() == ""


class TestHealthWidget:
    def test_init(self) -> None:
        w = HealthWidget()
        assert w._components == ()

    def test_update_data_empty(self) -> None:
        w = HealthWidget()
        w.update_data(())
        assert w._components == ()

    def test_update_data_with_components(self) -> None:
        w = HealthWidget()
        comps = (
            RuntimeComponentInfo(name="Runtime", status="healthy"),
            RuntimeComponentInfo(name="Stream", status="degraded"),
        )
        w.update_data(comps)
        assert len(w._components) == 2

    def test_update_data_replaces_previous(self) -> None:
        w = HealthWidget()
        w.update_data((RuntimeComponentInfo(name="A", status="healthy"),))
        assert len(w._components) == 1
        w.update_data(())
        assert len(w._components) == 0

    def test_render_returns_empty_string(self) -> None:
        w = HealthWidget()
        assert w.render() == ""


class TestRuntimeEventsWidget:
    def test_init(self) -> None:
        w = RuntimeEventsWidget()
        assert w._events == ()

    def test_update_data_empty(self) -> None:
        w = RuntimeEventsWidget()
        w.update_data(())
        assert w._events == ()

    def test_update_data_with_events(self) -> None:
        w = RuntimeEventsWidget()
        events = (
            RuntimeEventEntry(level="warning", source="stream", message="Reconnect"),
            RuntimeEventEntry(level="error", source="pipeline", message="Timeout"),
        )
        w.update_data(events)
        assert len(w._events) == 2

    def test_update_data_replaces_previous(self) -> None:
        w = RuntimeEventsWidget()
        w.update_data((RuntimeEventEntry(level="info", message="first"),))
        assert len(w._events) == 1
        w.update_data(())
        assert len(w._events) == 0

    def test_render_returns_empty_string(self) -> None:
        w = RuntimeEventsWidget()
        assert w.render() == ""


# ──────────────────────────────────────────────────
# Screen unit tests
# ──────────────────────────────────────────────────


class TestRuntimeScreenUnit:
    def test_screen_creation(self) -> None:
        screen = RuntimeScreen()
        assert screen is not None

    def test_default_state(self) -> None:
        screen = RuntimeScreen()
        assert isinstance(screen.state, RuntimeScreenState)

    def test_set_state_builder(self) -> None:
        screen = RuntimeScreen()

        def builder() -> RuntimeScreenState:
            return RuntimeScreenState()

        screen.set_state_builder(builder)
        assert screen._state_builder is builder

    def test_refresh_state_with_builder(self) -> None:
        screen = RuntimeScreen()
        custom = RuntimeScreenState(
            engine=RuntimeEngineInfo(status="RUNNING"),
        )
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen.state.engine.status == "RUNNING"

    def test_refresh_state_without_builder(self) -> None:
        screen = RuntimeScreen()
        screen._refresh_state()
        assert isinstance(screen.state, RuntimeScreenState)

    def test_refresh_state_builder_exception(self) -> None:
        screen = RuntimeScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        screen._refresh_state()
        assert isinstance(screen.state, RuntimeScreenState)

    def test_update_widgets_before_compose(self) -> None:
        screen = RuntimeScreen()
        screen._state = RuntimeScreenState(
            engine=RuntimeEngineInfo(status="RUNNING"),
        )
        screen._update_widgets()
        assert screen._engine_widget is None

    def test_bindings_exist(self) -> None:
        keys = [b[0] for b in RuntimeScreen.BINDINGS]
        assert "q" in keys
        assert "r" in keys
        assert "escape" in keys

    def test_paging_bindings_exist(self) -> None:
        keys = [b[0] for b in RuntimeScreen.BINDINGS]
        assert "page_up" in keys
        assert "page_down" in keys

    def test_scroll_actions_exist(self) -> None:
        screen = RuntimeScreen()
        assert hasattr(screen, "action_scroll_up")
        assert hasattr(screen, "action_scroll_down")

    def test_scroll_actions_with_no_widget(self) -> None:
        screen = RuntimeScreen()
        screen.action_scroll_up()
        screen.action_scroll_down()

    def test_scheduler_paused_state(self) -> None:
        screen = RuntimeScreen()
        custom = RuntimeScreenState(
            engine=RuntimeEngineInfo(
                status="PAUSED", is_running=False, scheduler_active=False
            ),
        )
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen.state.engine.status == "PAUSED"
        assert screen.state.engine.scheduler_active is False

    def test_scheduler_active_state(self) -> None:
        screen = RuntimeScreen()
        custom = RuntimeScreenState(
            engine=RuntimeEngineInfo(
                status="RUNNING", is_running=True, scheduler_active=True
            ),
        )
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen.state.engine.scheduler_active is True

    def test_engine_control_bindings_exist(self) -> None:
        keys = [b[0] for b in RuntimeScreen.BINDINGS]
        assert "s" in keys
        assert "x" in keys

    def test_engine_control_actions_exist(self) -> None:
        screen = RuntimeScreen()
        assert hasattr(screen, "action_start_engine")
        assert hasattr(screen, "action_stop_engine")
        assert hasattr(screen, "_start_engine_worker")
        assert hasattr(screen, "_stop_engine_worker")

    def test_start_engine_guard_when_running(self) -> None:
        screen = RuntimeScreen()
        screen.notify = MagicMock()
        mock_engine = MagicMock()
        mock_engine.is_running = True
        with patch(
            "titan.tui.screens.runtime.get_runtime_engine", return_value=mock_engine
        ) as mock_get:
            screen.action_start_engine()
            mock_get.assert_called_once_with()
        mock_engine.start.assert_not_called()
        screen.notify.assert_called()

    def test_stop_engine_guard_when_not_running(self) -> None:
        screen = RuntimeScreen()
        screen.notify = MagicMock()
        mock_engine = MagicMock()
        mock_engine.is_running = False
        with patch(
            "titan.tui.screens.runtime.get_runtime_engine", return_value=mock_engine
        ):
            screen.action_stop_engine()
        mock_engine.stop.assert_not_called()
        screen.notify.assert_called()

    def test_update_engine_status_bar_without_app(self) -> None:
        screen = RuntimeScreen()
        screen._update_engine_status_bar("Running")
        assert screen is not None


# ──────────────────────────────────────────────────
# App tests
# ──────────────────────────────────────────────────


class TestTITANAppRuntime:
    def test_app_creation(self) -> None:
        app = TITANApp()
        assert app is not None

    def test_set_runtime_state_builder(self) -> None:
        app = TITANApp()

        def builder() -> RuntimeScreenState:
            return RuntimeScreenState()

        app.set_runtime_state_builder(builder)
        assert app._runtime_state_builder is builder

    def test_f1_binding_exists(self) -> None:
        keys = [b[0] for b in TITANApp.BINDINGS]
        assert "f1" in keys
        assert "f2" in keys


# ──────────────────────────────────────────────────
# State builder unit tests (with mocked managers)
# ──────────────────────────────────────────────────


def _make_mock_engine(
    status: str = "RUNNING",
    uptime: float = 12738.0,
    stream_status: str = "connected",
    subscriptions: int = 24,
    pipeline_executions: int = 1248,
    scheduler_active: bool = True,
    last_pipeline_time: object = None,
    last_quote_time: object = None,
    component_health: object = (),
    warnings: object = (),
    errors: object = (),
) -> MagicMock:
    engine = MagicMock()
    engine.is_running = status == "RUNNING"
    engine.status.name = status
    from titan.runtime.models import RuntimeStatus

    status_map = {
        "RUNNING": RuntimeStatus.RUNNING,
        "STOPPED": RuntimeStatus.STOPPED,
        "PAUSED": RuntimeStatus.PAUSED,
    }
    report = MagicMock()
    report.runtime_status = status_map.get(status, RuntimeStatus.RUNNING)
    report.performance = MagicMock()
    report.performance.uptime_seconds = uptime
    report.market = MagicMock()
    report.market.stream_status = stream_status
    report.market.active_subscriptions = subscriptions
    report.market.last_quote_time = last_quote_time
    report.scheduler = MagicMock()
    report.scheduler.active = scheduler_active
    report.scheduler.pipeline_executions = pipeline_executions
    report.scheduler.last_pipeline_time = last_pipeline_time
    report.health = MagicMock()
    report.health.component_health = component_health
    report.health.warnings = warnings
    report.health.errors = errors
    engine.generate_report.return_value = report
    engine.event_bus = MagicMock()
    from titan.runtime.models import RuntimeEventType

    for et in RuntimeEventType:
        engine.event_bus.listener_count.return_value = 0
    return engine


class TestBuildRuntimeState:
    @patch("titan.cli.common.get_runtime_engine")
    @patch("titan.cli.common.get_recovery_manager", side_effect=RuntimeError)
    def test_with_engine(self, mock_rec: MagicMock, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine()
        state = build_runtime_state()
        assert state.engine.status == "RUNNING"

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    def test_without_engine(self, mock_eng: MagicMock) -> None:
        state = build_runtime_state()
        assert state.engine.status == "Unknown"


class TestReadRuntimeEngine:
    @patch("titan.cli.common.get_runtime_engine")
    def test_running(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(status="RUNNING")
        info = _read_runtime_engine()
        assert info.status == "RUNNING"
        assert info.is_running is True
        assert info.scheduler_active is True

    @patch("titan.cli.common.get_runtime_engine")
    def test_stopped(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(status="STOPPED")
        info = _read_runtime_engine()
        assert info.status == "STOPPED"
        assert info.is_running is False

    @patch("titan.cli.common.get_runtime_engine")
    def test_paused(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(
            status="PAUSED", scheduler_active=False
        )
        info = _read_runtime_engine()
        assert info.status == "PAUSED"
        assert info.is_running is False
        assert info.scheduler_active is False

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    def test_exception(self, mock_eng: MagicMock) -> None:
        info = _read_runtime_engine()
        assert info.status == "Unknown"


class TestReadRuntimeStream:
    @patch("titan.cli.common.get_runtime_engine")
    def test_connected(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(
            stream_status="connected", subscriptions=24
        )
        info = _read_runtime_stream()
        assert info.connected is True
        assert info.symbols_tracked == 24

    @patch("titan.cli.common.get_runtime_engine")
    def test_disconnected(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(
            stream_status="disconnected", subscriptions=0
        )
        info = _read_runtime_stream()
        assert info.connected is False
        assert info.symbols_tracked == 0

    @patch("titan.cli.common.get_runtime_engine")
    def test_tick_rate_default(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine()
        info = _read_runtime_stream()
        assert info.tick_rate == "N/A"

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    def test_exception(self, mock_eng: MagicMock) -> None:
        info = _read_runtime_stream()
        assert info.connected is False


class TestReadRuntimePipeline:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_executions(self, mock_eng: MagicMock) -> None:
        from datetime import datetime, timedelta

        mock_eng.return_value = _make_mock_engine(
            pipeline_executions=1248,
            last_pipeline_time=datetime.now(UTC) - timedelta(seconds=2),
        )
        info = _read_runtime_pipeline()
        assert info.executions == 1248
        assert "sec ago" in info.last_run

    @patch("titan.cli.common.get_runtime_engine")
    def test_no_last_run(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(pipeline_executions=0)
        info = _read_runtime_pipeline()
        assert info.last_run == "Never"

    @patch("titan.cli.common.get_runtime_engine")
    def test_avg_runtime_default(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine()
        info = _read_runtime_pipeline()
        assert info.avg_runtime == "N/A"

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    def test_exception(self, mock_eng: MagicMock) -> None:
        info = _read_runtime_pipeline()
        assert info.executions == 0


class TestReadRuntimeEventBus:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_listeners(self, mock_eng: MagicMock) -> None:
        from titan.runtime.models import RuntimeEventType

        engine = _make_mock_engine()
        bus = MagicMock()

        def listener_count(et: RuntimeEventType) -> int:
            if et == RuntimeEventType.RUNTIME_STARTED:
                return 2
            if et == RuntimeEventType.STREAM_CONNECTED:
                return 1
            return 0

        bus.listener_count.side_effect = listener_count
        engine.event_bus = bus
        mock_eng.return_value = engine
        info = _read_runtime_event_bus()
        assert info.subscribers == 3
        assert info.published == 0

    @patch("titan.cli.common.get_runtime_engine")
    def test_no_listeners(self, mock_eng: MagicMock) -> None:
        engine = _make_mock_engine()
        engine.event_bus = MagicMock()
        engine.event_bus.listener_count.return_value = 0
        mock_eng.return_value = engine
        info = _read_runtime_event_bus()
        assert info.subscribers == 0
        assert info.published == 0

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    def test_exception(self, mock_eng: MagicMock) -> None:
        info = _read_runtime_event_bus()
        assert info.subscribers == 0
        assert info.published == 0


class TestReadRuntimeComponents:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_components(self, mock_eng: MagicMock) -> None:
        from titan.runtime.models import ComponentHealth, HealthStatus

        ch = (
            ComponentHealth(component_name="Runtime", status=HealthStatus.HEALTHY),
            ComponentHealth(component_name="Stream", status=HealthStatus.DEGRADED),
        )
        mock_eng.return_value = _make_mock_engine(component_health=ch)
        comps = _read_runtime_components()
        assert len(comps) == 2
        assert comps[0].name == "Runtime"
        assert comps[0].status == "healthy"
        assert comps[1].name == "Stream"
        assert comps[1].status == "degraded"

    @patch("titan.cli.common.get_runtime_engine")
    def test_empty_components(self, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(component_health=())
        comps = _read_runtime_components()
        assert comps == ()

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    def test_exception(self, mock_eng: MagicMock) -> None:
        comps = _read_runtime_components()
        assert comps == ()


class TestReadRuntimeEvents:
    @patch("titan.cli.common.get_runtime_engine")
    @patch("titan.cli.common.get_recovery_manager", side_effect=RuntimeError)
    def test_with_warnings_and_errors(
        self, mock_rec: MagicMock, mock_eng: MagicMock
    ) -> None:
        mock_eng.return_value = _make_mock_engine(
            warnings=("Stream degraded",), errors=("Pipeline timeout",)
        )
        events = _read_runtime_events()
        assert len(events) == 2
        assert events[0].level == "warning"
        assert events[1].level == "error"

    @patch("titan.cli.common.get_runtime_engine")
    @patch("titan.cli.common.get_recovery_manager", side_effect=RuntimeError)
    def test_empty_events(self, mock_rec: MagicMock, mock_eng: MagicMock) -> None:
        mock_eng.return_value = _make_mock_engine(warnings=(), errors=())
        events = _read_runtime_events()
        assert events == ()

    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)
    @patch("titan.cli.common.get_recovery_manager", side_effect=RuntimeError)
    def test_all_exceptions(self, mock_rec: MagicMock, mock_eng: MagicMock) -> None:
        events = _read_runtime_events()
        assert events == ()


# ──────────────────────────────────────────────────
# Async integration tests
# ──────────────────────────────────────────────────


class TestRuntimeAsync:
    @pytest.mark.asyncio
    async def test_runtime_screen_pushes(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from titan.tui.screens.runtime import RuntimeScreen

            await pilot.press("f2")
            assert isinstance(app.query_one("#view-runtime"), RuntimeScreen)

    @pytest.mark.asyncio
    async def test_runtime_screen_widgets_mounted(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from titan.tui.screens.runtime import RuntimeScreen

            screen = app.query_one("#view-runtime", RuntimeScreen)
            assert screen.query_one("#engine-widget") is not None
            assert screen.query_one("#stream-widget") is not None
            assert screen.query_one("#pipeline-widget") is not None
            assert screen.query_one("#eventbus-widget") is not None
            assert screen.query_one("#health-widget") is not None
            assert screen.query_one("#events-widget") is not None

    @pytest.mark.asyncio
    async def test_runtime_title_shown(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            from titan.tui.screens.runtime import RuntimeScreen

            screen = app.query_one("#view-runtime", RuntimeScreen)
            title = screen.query_one("#runtime-title", Static)
            assert "Runtime" in str(title.render())

    @pytest.mark.asyncio
    async def test_runtime_refresh_indicator(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            from titan.tui.screens.runtime import RuntimeScreen

            screen = app.query_one("#view-runtime", RuntimeScreen)
            indicator = screen.query_one("#refresh-indicator", Static)
            assert indicator is not None

    @pytest.mark.asyncio
    async def test_runtime_manual_refresh(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            from titan.tui.screens.runtime import RuntimeScreen

            screen = app.query_one("#view-runtime", RuntimeScreen)
            screen.action_refresh()
            indicator = screen.query_one("#refresh-indicator", Static)
            assert "Last refresh:" in str(indicator.render())

    @pytest.mark.asyncio
    async def test_runtime_escape_back(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f2")
            assert app._content_switcher is not None
            assert app._content_switcher.current == "view-runtime"
            await pilot.press("escape")
            assert app._content_switcher.current == "view-dashboard"

    @pytest.mark.asyncio
    async def test_f2_navigates_to_runtime(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from titan.tui.screens.runtime import RuntimeScreen

            await pilot.press("f2")
            assert app._content_switcher is not None
            assert app._content_switcher.current == "view-runtime"
            assert isinstance(app.query_one("#view-runtime"), RuntimeScreen)

    @pytest.mark.asyncio
    async def test_f1_navigates_to_dashboard(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f2")
            await pilot.press("f1")
            assert app._content_switcher is not None
            assert app._content_switcher.current == "view-dashboard"

    @pytest.mark.asyncio
    async def test_press_s_starts_engine_worker(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f2")
            mock_engine = MagicMock()
            mock_engine.is_running = False
            with patch(
                "titan.tui.screens.runtime.get_runtime_engine",
                return_value=mock_engine,
            ):
                await pilot.press("s")
                for _ in range(100):
                    if mock_engine.start.called:
                        break
                    await pilot.pause()
                assert mock_engine.start.called

    @pytest.mark.asyncio
    async def test_press_x_stops_engine_worker(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f2")
            mock_engine = MagicMock()
            mock_engine.is_running = True
            with patch(
                "titan.tui.screens.runtime.get_runtime_engine",
                return_value=mock_engine,
            ):
                await pilot.press("x")
                for _ in range(100):
                    if mock_engine.stop.called:
                        break
                    await pilot.pause()
                assert mock_engine.stop.called

    @pytest.mark.asyncio
    async def test_press_x_when_not_running_does_not_stop(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f2")
            mock_engine = MagicMock()
            mock_engine.is_running = False
            with patch(
                "titan.tui.screens.runtime.get_runtime_engine",
                return_value=mock_engine,
            ):
                await pilot.press("x")
                await pilot.pause()
                mock_engine.stop.assert_not_called()
