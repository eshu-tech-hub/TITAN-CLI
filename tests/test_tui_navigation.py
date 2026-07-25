"""Tests for TITAN TUI navigation, routing, shell, sidebar, header, status bar, help."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from titan.tui.router import ScreenRouter
from titan.tui.theme import (
    DARK,
    LIGHT,
    ThemeColors,
    get_theme,
    set_theme,
)
from titan.tui.widgets.header import HeaderWidget
from titan.tui.widgets.sidebar import SidebarWidget
from titan.tui.widgets.status_bar import StatusBarWidget

# ──────────────────────────────────────────────────
# Theme tests
# ──────────────────────────────────────────────────


class TestThemeColors:
    def test_defaults(self) -> None:
        c = ThemeColors()
        assert c.bg == "#1a1a2e"
        assert c.text == "#e0e0e0"
        assert c.primary == "#4a9eff"

    def test_frozen(self) -> None:
        c = ThemeColors()
        with pytest.raises(AttributeError):
            c.bg = "#000"  # type: ignore[misc]

    def test_custom(self) -> None:
        c = ThemeColors(bg="#fff", text="#000")
        assert c.bg == "#fff"
        assert c.text == "#000"


class TestThemeModule:
    def test_get_theme_returns_dark(self) -> None:
        set_theme(DARK)
        assert get_theme() is DARK

    def test_set_theme(self) -> None:
        original = get_theme()
        set_theme(LIGHT)
        assert get_theme() is LIGHT
        set_theme(DARK)
        assert get_theme() is original

    def test_dark_is_theme_colors(self) -> None:
        assert isinstance(DARK, ThemeColors)

    def test_light_is_theme_colors(self) -> None:
        assert isinstance(LIGHT, ThemeColors)


# ──────────────────────────────────────────────────
# Router tests
# ──────────────────────────────────────────────────


def _make_screen(name: str = "test") -> MagicMock:
    screen = MagicMock()
    screen.name = name
    return screen


class TestScreenRouterInit:
    def test_defaults(self) -> None:
        r = ScreenRouter()
        assert r.current == "dashboard"
        assert r.default == "dashboard"
        assert r.history == []
        assert r.screen_names == []

    def test_custom_default(self) -> None:
        r = ScreenRouter(default="runtime")
        assert r.default == "runtime"
        assert r.current == "runtime"


class TestScreenRouterRegister:
    def test_register(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        assert "dashboard" in r.screen_names

    def test_register_preserves_order(self) -> None:
        r = ScreenRouter()
        r.register("c", lambda: _make_screen("c"))
        r.register("a", lambda: _make_screen("a"))
        r.register("b", lambda: _make_screen("b"))
        assert r.screen_names == ["c", "a", "b"]

    def test_register_sets_default(self) -> None:
        r = ScreenRouter()
        r.register("runtime", lambda: _make_screen("r"), is_default=True)
        assert r.default == "runtime"

    def test_register_no_duplicate_names(self) -> None:
        r = ScreenRouter()
        r.register("x", lambda: _make_screen("x"))
        r.register("x", lambda: _make_screen("x2"))
        assert r.screen_names.count("x") == 1

    def test_get_screen_names_returns_copy(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        names = r.get_screen_names()
        names.append("b")
        assert "b" not in r.screen_names


class TestScreenRouterCreate:
    def test_create(self) -> None:
        r = ScreenRouter()
        mock = _make_screen("d")
        r.register("dashboard", lambda: mock)
        s = r.create("dashboard")
        assert s is mock

    def test_create_unregistered_raises(self) -> None:
        r = ScreenRouter()
        with pytest.raises(KeyError, match="not registered"):
            r.create("unknown")

    def test_create_passes_kwargs(self) -> None:
        r = ScreenRouter()
        factory = MagicMock(return_value=_make_screen("d"))
        r.register("dashboard", factory)
        r.create("dashboard", foo="bar")
        factory.assert_called_once_with(foo="bar")


class TestScreenRouterGetOrCreate:
    def test_get_or_create_caches(self) -> None:
        r = ScreenRouter()
        mock = _make_screen("d")
        r.register("dashboard", lambda: mock)
        s1 = r.get_or_create("dashboard")
        s2 = r.get_or_create("dashboard")
        assert s1 is s2

    def test_get_or_create_unregistered_raises(self) -> None:
        r = ScreenRouter()
        with pytest.raises(KeyError):
            r.get_or_create("unknown")


class TestScreenRouterInvalidate:
    def test_invalidate_single(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.get_or_create("dashboard")
        r.invalidate("dashboard")
        assert "dashboard" not in r._cache

    def test_invalidate_all(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.register("b", lambda: _make_screen("b"))
        r.get_or_create("a")
        r.get_or_create("b")
        r.invalidate()
        assert len(r._cache) == 0

    def test_invalidate_nonexistent_no_error(self) -> None:
        r = ScreenRouter()
        r.invalidate("nonexistent")


class TestScreenRouterNavigate:
    def test_navigate_sets_current(self) -> None:
        r = ScreenRouter()
        r.register("runtime", lambda: _make_screen("r"))
        s = r.navigate("runtime")
        assert r.current == "runtime"
        assert s is not None

    def test_navigate_pushes_history(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("runtime", lambda: _make_screen("r"))
        r.navigate("runtime")
        assert r.history == ["dashboard"]

    def test_navigate_same_screen_no_history(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.navigate("dashboard")
        assert r.history == []

    def test_navigate_unregistered_raises(self) -> None:
        r = ScreenRouter()
        with pytest.raises(KeyError, match="not registered"):
            r.navigate("unknown")

    def test_navigate_deep_history(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.register("b", lambda: _make_screen("b"))
        r.register("c", lambda: _make_screen("c"))
        r.navigate("a")
        r.navigate("b")
        r.navigate("c")
        assert r.history == ["dashboard", "a", "b"]
        assert r.current == "c"


class TestScreenRouterGoBack:
    def test_go_back_returns_previous(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("runtime", lambda: _make_screen("r"))
        r.navigate("runtime")
        s = r.go_back()
        assert r.current == "dashboard"
        assert s is not None

    def test_go_back_empty_returns_none(self) -> None:
        r = ScreenRouter()
        assert r.go_back() is None

    def test_go_back_multiple(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.register("b", lambda: _make_screen("b"))
        r.navigate("a")
        r.navigate("b")
        r.go_back()
        assert r.current == "a"
        r.go_back()
        assert r.current == "dashboard"

    def test_can_go_back(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        assert r.can_go_back() is False
        r.navigate("a")
        assert r.can_go_back() is True
        r.go_back()
        assert r.can_go_back() is False


class TestScreenRouterResetHistory:
    def test_reset_history(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.reset_history()
        assert r.history == []
        assert r.current == "dashboard"


# ──────────────────────────────────────────────────
# HeaderWidget tests
# ──────────────────────────────────────────────────


class TestHeaderWidget:
    def test_init(self) -> None:
        h = HeaderWidget()
        assert h._version == "TITAN"
        assert h._hostname == ""
        assert h._profile == "default"
        assert h._uptime == "00:00:00"
        assert h._runtime_status == "Stopped"

    def test_update_data_version(self) -> None:
        h = HeaderWidget()
        h.update_data(version="2.0.0")
        assert h._version == "2.0.0"

    def test_update_data_hostname(self) -> None:
        h = HeaderWidget()
        h.update_data(hostname="node-01")
        assert h._hostname == "node-01"

    def test_update_data_profile(self) -> None:
        h = HeaderWidget()
        h.update_data(profile="production")
        assert h._profile == "production"

    def test_update_data_uptime(self) -> None:
        h = HeaderWidget()
        h.update_data(uptime="01:30:00")
        assert h._uptime == "01:30:00"

    def test_update_data_runtime_status(self) -> None:
        h = HeaderWidget()
        h.update_data(runtime_status="Running")
        assert h._runtime_status == "Running"

    def test_update_data_multiple_fields(self) -> None:
        h = HeaderWidget()
        h.update_data(version="3.0", hostname="h1", uptime="10:00")
        assert h._version == "3.0"
        assert h._hostname == "h1"
        assert h._uptime == "10:00"

    def test_render_returns_empty(self) -> None:
        h = HeaderWidget()
        assert h.render() == ""

    def test_update_clock_no_error(self) -> None:
        h = HeaderWidget()
        h.update_clock()


# ──────────────────────────────────────────────────
# SidebarWidget tests
# ──────────────────────────────────────────────────


class TestSidebarWidget:
    def test_init(self) -> None:
        s = SidebarWidget()
        assert s._active == "dashboard"

    def test_active_property(self) -> None:
        s = SidebarWidget()
        assert s.active == "dashboard"

    def test_set_active(self) -> None:
        s = SidebarWidget()
        s.set_active("runtime")
        assert s._active == "runtime"

    def test_set_active_before_compose(self) -> None:
        s = SidebarWidget()
        s.set_active("runtime")
        assert s._active == "runtime"

    def test_render_returns_empty(self) -> None:
        s = SidebarWidget()
        assert s.render() == ""

    def test_sections_defined(self) -> None:
        assert len(SidebarWidget.SECTIONS) > 0

    def test_sections_include_dashboard(self) -> None:
        names = [key for _, key in SidebarWidget.SECTIONS]
        assert "dashboard" in names

    def test_sections_include_help(self) -> None:
        names = [key for _, key in SidebarWidget.SECTIONS]
        assert "help" in names

    def test_sections_include_separator(self) -> None:
        keys = [key for _, key in SidebarWidget.SECTIONS]
        assert None in keys


# ──────────────────────────────────────────────────
# StatusBarWidget tests
# ──────────────────────────────────────────────────


class TestStatusBarWidget:
    def test_init(self) -> None:
        s = StatusBarWidget()
        assert s._environment == "Development"
        assert s._runtime_status == "Stopped"
        assert s._broker_status == "Disconnected"
        assert s._mode == "Paper"
        assert s._refresh_interval == 1.0

    def test_update_data_environment(self) -> None:
        s = StatusBarWidget()
        s.update_data(environment="Production")
        assert s._environment == "Production"

    def test_update_data_runtime_status(self) -> None:
        s = StatusBarWidget()
        s.update_data(runtime_status="Running")
        assert s._runtime_status == "Running"

    def test_update_data_broker_status(self) -> None:
        s = StatusBarWidget()
        s.update_data(broker_status="Connected")
        assert s._broker_status == "Connected"

    def test_update_data_mode(self) -> None:
        s = StatusBarWidget()
        s.update_data(mode="Live")
        assert s._mode == "Live"

    def test_update_data_refresh_interval(self) -> None:
        s = StatusBarWidget()
        s.update_data(refresh_interval=5.0)
        assert s._refresh_interval == 5.0

    def test_update_data_multiple(self) -> None:
        s = StatusBarWidget()
        s.update_data(environment="Prod", mode="Live", refresh_interval=2.0)
        assert s._environment == "Prod"
        assert s._mode == "Live"
        assert s._refresh_interval == 2.0

    def test_render_returns_empty(self) -> None:
        s = StatusBarWidget()
        assert s.render() == ""

    def test_update_time_no_error(self) -> None:
        s = StatusBarWidget()
        s.update_time()


# ──────────────────────────────────────────────────
# HelpScreen tests
# ──────────────────────────────────────────────────


class TestHelpScreen:
    def test_bindings_exist(self) -> None:
        from titan.tui.screens.help import HelpScreen

        keys = [b[0] for b in HelpScreen.BINDINGS]
        assert "escape" in keys
        assert "q" in keys
        assert "f11" in keys

    def test_import(self) -> None:
        from titan.tui.screens.help import SHORTCUTS

        assert len(SHORTCUTS) > 0

    def test_shortcuts_sections(self) -> None:
        from titan.tui.screens.help import SHORTCUTS

        section_names = [s[0] for s in SHORTCUTS]
        assert "Global Navigation" in section_names
        assert "Controls" in section_names
        assert "Screen-Specific" in section_names


# ──────────────────────────────────────────────────
# Screen __init__ exports
# ──────────────────────────────────────────────────


class TestScreenExports:
    def test_exports(self) -> None:
        from titan.tui.screens import (
            DashboardScreen,
            HelpScreen,
            PaperScreen,
            RuntimeScreen,
        )

        assert DashboardScreen is not None
        assert HelpScreen is not None
        assert PaperScreen is not None
        assert RuntimeScreen is not None


# ──────────────────────────────────────────────────
# ShellApp tests
# ──────────────────────────────────────────────────


class TestShellApp:
    def test_import(self) -> None:
        from titan.tui.shell import ShellApp

        assert ShellApp is not None

    def test_creation(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        assert app is not None

    def test_router_default(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        assert app.router.current == "dashboard"

    def test_register_screen(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen("dashboard", lambda: MagicMock())
        assert "dashboard" in app.router.screen_names

    def test_set_state_builder(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()

        def builder() -> MagicMock:
            return MagicMock()

        app.set_state_builder("dashboard", builder)
        assert app._state_builders["dashboard"] is builder

    def test_bindings_include_f1_f12(self) -> None:
        from titan.tui.shell import ShellApp

        keys = [b[0] for b in ShellApp.BINDINGS]
        assert "f1" in keys
        assert "f12" in keys

    def test_bindings_include_ctrl_r(self) -> None:
        from titan.tui.shell import ShellApp

        keys = [b[0] for b in ShellApp.BINDINGS]
        assert "ctrl+r" in keys

    def test_bindings_include_ctrl_q(self) -> None:
        from titan.tui.shell import ShellApp

        keys = [b[0] for b in ShellApp.BINDINGS]
        assert "ctrl+q" in keys

    def test_bindings_include_escape(self) -> None:
        from titan.tui.shell import ShellApp

        keys = [b[0] for b in ShellApp.BINDINGS]
        assert "escape" in keys

    def test_header_initially_none(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        assert app.header is None

    def test_sidebar_initially_none(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        assert app.sidebar is None

    def test_status_bar_initially_none(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        assert app.status_bar is None


# ──────────────────────────────────────────────────
# Layout backward compatibility
# ──────────────────────────────────────────────────


class TestLayoutBackwardCompat:
    def test_titan_app_import(self) -> None:
        from titan.tui.layout import TITANApp

        assert TITANApp is not None

    def test_titan_app_creation(self) -> None:
        from titan.tui.layout import TITANApp

        app = TITANApp()
        assert app is not None

    def test_titan_app_bindings(self) -> None:
        from titan.tui.layout import TITANApp

        keys = [b[0] for b in TITANApp.BINDINGS]
        assert "f1" in keys
        assert "f2" in keys
        assert "f3" in keys
        assert "q" in keys


# ──────────────────────────────────────────────────
# Router integration with ShellApp
# ──────────────────────────────────────────────────


class TestRouterIntegration:
    def test_navigate_and_back(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("runtime", lambda: _make_screen("r"))
        r.register("paper", lambda: _make_screen("p"))
        r.navigate("runtime")
        r.navigate("paper")
        assert r.current == "paper"
        assert len(r.history) == 2
        r.go_back()
        assert r.current == "runtime"
        r.go_back()
        assert r.current == "dashboard"

    def test_navigate_resets_history_on_default(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.navigate("dashboard")
        assert r.history == []

    def test_invalidate_and_recreate(self) -> None:
        r = ScreenRouter()
        call_count = 0

        def factory() -> MagicMock:
            nonlocal call_count
            call_count += 1
            return _make_screen("d")

        r.register("dashboard", factory)
        s1 = r.get_or_create("dashboard")
        s2 = r.get_or_create("dashboard")
        assert s1 is s2
        assert call_count == 1
        r.invalidate("dashboard")
        s3 = r.get_or_create("dashboard")
        assert s3 is not s1
        assert call_count == 2

    def test_full_navigation_flow(self) -> None:
        r = ScreenRouter(default="dashboard")
        for name in ["dashboard", "runtime", "paper", "help"]:
            r.register(name, lambda n=name: _make_screen(n))
        r.navigate("runtime")
        r.navigate("paper")
        r.navigate("help")
        assert r.current == "help"
        assert r.history == ["dashboard", "runtime", "paper"]
        r.go_back()
        assert r.current == "paper"
        r.go_back()
        assert r.current == "runtime"
        r.go_back()
        assert r.current == "dashboard"
        assert not r.can_go_back()


# ──────────────────────────────────────────────────
# Async integration tests (ShellApp)
# ──────────────────────────────────────────────────


class TestShellAppAsync:
    @pytest.mark.asyncio
    async def test_shell_app_mounts(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.header is not None
            assert app.sidebar is not None
            assert app.status_bar is not None

    @pytest.mark.asyncio
    async def test_shell_header_mounted(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#app-header") is not None

    @pytest.mark.asyncio
    async def test_shell_sidebar_mounted(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#app-sidebar") is not None

    @pytest.mark.asyncio
    async def test_shell_status_bar_mounted(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#app-status") is not None

    @pytest.mark.asyncio
    async def test_shell_f12_opens_help(self) -> None:
        from titan.tui.screens.help import HelpScreen
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        app.register_screen("help", lambda: HelpScreen())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f12")
            assert isinstance(app.screen, HelpScreen)

    @pytest.mark.asyncio
    async def test_help_escape_returns(self) -> None:
        from titan.tui.screens.dashboard import DashboardScreen
        from titan.tui.screens.help import HelpScreen
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen("dashboard", lambda: DashboardScreen())
        app.register_screen("help", lambda: HelpScreen())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f12")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("escape")
            assert isinstance(app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_sidebar_active_updates(self) -> None:
        from titan.tui.screens.dashboard import DashboardScreen
        from titan.tui.screens.help import HelpScreen
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen("dashboard", lambda: DashboardScreen())
        app.register_screen("help", lambda: HelpScreen())
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.sidebar is not None
            assert app.sidebar.active == "dashboard"
            await pilot.press("f12")
            assert app.sidebar.active == "help"

    @pytest.mark.asyncio
    async def test_shell_title(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "TITAN" in app.title

    @pytest.mark.asyncio
    async def test_router_current_after_mount(self) -> None:
        from titan.tui.shell import ShellApp

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.router.current == "dashboard"

    @pytest.mark.asyncio
    async def test_shell_f2_opens_runtime(self) -> None:
        from titan.tui.shell import ShellApp
        from titan.tui.screens.runtime import RuntimeScreen

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        app.register_screen("runtime", lambda: RuntimeScreen())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f2")
            assert isinstance(app.screen, RuntimeScreen)

    @pytest.mark.asyncio
    async def test_shell_f3_opens_paper(self) -> None:
        from titan.tui.shell import ShellApp
        from titan.tui.screens.paper import PaperScreen

        app = ShellApp()
        app.register_screen(
            "dashboard",
            lambda: __import__(
                "titan.tui.screens.dashboard", fromlist=["DashboardScreen"]
            ).DashboardScreen(),
        )
        app.register_screen("paper", lambda: PaperScreen())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f3")
            assert isinstance(app.screen, PaperScreen)


# ──────────────────────────────────────────────────
# Additional router edge cases
# ──────────────────────────────────────────────────


class TestRouterEdgeCases:
    def test_navigate_same_screen_no_push(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.navigate("a")
        r.navigate("a")
        assert len(r.history) == 1  # only "dashboard" pushed once

    def test_go_back_after_navigate_to_default(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.navigate("dashboard")
        assert r.go_back() is None

    def test_history_snapshot(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        h = r.history
        h.append("b")
        assert "b" not in r.history

    def test_screen_names_snapshot(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        names = r.screen_names
        names.append("b")
        assert "b" not in r.screen_names

    def test_register_many_screens(self) -> None:
        r = ScreenRouter()
        for i in range(20):
            r.register(f"screen_{i}", lambda n=i: _make_screen(n))
        assert len(r.screen_names) == 20

    def test_navigate_deep_then_back_all(self) -> None:
        r = ScreenRouter()
        for i in range(10):
            r.register(f"s{i}", lambda n=i: _make_screen(n))
        for i in range(10):
            r.navigate(f"s{i}")
        assert len(r.history) == 10
        for _ in range(10):
            r.go_back()
        assert r.current == "dashboard"
        assert not r.can_go_back()


# ──────────────────────────────────────────────────
# Additional widget tests
# ──────────────────────────────────────────────────


class TestHeaderWidgetEdgeCases:
    def test_all_fields_update(self) -> None:
        h = HeaderWidget()
        h.update_data(
            version="5.0",
            hostname="node-1",
            profile="prod",
            uptime="99:99:99",
            runtime_status="Running",
        )
        assert h._version == "5.0"
        assert h._hostname == "node-1"
        assert h._profile == "prod"
        assert h._uptime == "99:99:99"
        assert h._runtime_status == "Running"

    def test_update_clock_sets_time(self) -> None:
        h = HeaderWidget()
        h.update_clock()
        assert h._clock != ""

    def test_partial_update_preserves_existing(self) -> None:
        h = HeaderWidget()
        h.update_data(version="1.0")
        h.update_data(hostname="h1")
        assert h._version == "1.0"
        assert h._hostname == "h1"


class TestStatusBarWidgetEdgeCases:
    def test_all_fields_update(self) -> None:
        s = StatusBarWidget()
        s.update_data(
            environment="Prod",
            runtime_status="Running",
            broker_status="Connected",
            mode="Live",
            refresh_interval=2.0,
        )
        assert s._environment == "Prod"
        assert s._runtime_status == "Running"
        assert s._broker_status == "Connected"
        assert s._mode == "Live"
        assert s._refresh_interval == 2.0

    def test_update_time_sets_value(self) -> None:
        s = StatusBarWidget()
        s.update_time()
        assert s._time != ""

    def test_partial_update_preserves_existing(self) -> None:
        s = StatusBarWidget()
        s.update_data(environment="Prod")
        s.update_data(mode="Live")
        assert s._environment == "Prod"
        assert s._mode == "Live"


class TestSidebarWidgetEdgeCases:
    def test_set_active_same_value(self) -> None:
        s = SidebarWidget()
        s.set_active("dashboard")
        assert s.active == "dashboard"

    def test_set_active_changes(self) -> None:
        s = SidebarWidget()
        s.set_active("runtime")
        assert s.active == "runtime"
        s.set_active("paper")
        assert s.active == "paper"

    def test_sections_have_all_required(self) -> None:
        keys = [key for _, key in SidebarWidget.SECTIONS if key is not None]
        required = ["dashboard", "runtime", "paper", "help"]
        for name in required:
            assert name in keys

    def test_separator_entries(self) -> None:
        separators = [label for label, key in SidebarWidget.SECTIONS if key is None]
        assert len(separators) > 0


class TestThemeEdgeCases:
    def test_dark_colors_distinct_from_light(self) -> None:
        assert DARK.bg != LIGHT.bg
        assert DARK.text != LIGHT.text

    def test_theme_swap_and_back(self) -> None:
        original = get_theme()
        set_theme(LIGHT)
        assert get_theme() is LIGHT
        set_theme(DARK)
        assert get_theme() is DARK
        assert get_theme() is original


# ──────────────────────────────────────────────────
# Additional navigation edge cases
# ──────────────────────────────────────────────────


class TestRouterNavigationEdge:
    def test_navigate_default_no_push(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.navigate("dashboard")
        assert r.history == []

    def test_navigate_from_default_pushes_default(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        assert r.history == ["dashboard"]

    def test_navigate_to_default_clears_history(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        r.register("b", lambda: _make_screen("b"))
        r.navigate("a")
        r.navigate("b")
        assert len(r.history) == 2
        r.navigate("dashboard")
        assert r.history == []

    def test_go_back_to_default_then_navigate(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.go_back()
        assert r.current == "dashboard"
        assert not r.can_go_back()

    def test_invalidate_current_screen(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.invalidate("a")
        s2 = r.get_or_create("a")
        assert s2 is not None

    def test_reset_history(self) -> None:
        r = ScreenRouter()
        r.register("dashboard", lambda: _make_screen("d"))
        r.register("a", lambda: _make_screen("a"))
        r.navigate("a")
        r.navigate("a")
        assert len(r.history) > 0
        r.reset_history()
        assert r.history == []
        assert r.current == "dashboard"

    def test_get_screen_names_returns_ordered(self) -> None:
        r = ScreenRouter()
        r.register("z", lambda: _make_screen("z"))
        r.register("a", lambda: _make_screen("a"))
        r.register("m", lambda: _make_screen("m"))
        assert r.get_screen_names() == ["z", "a", "m"]

    def test_register_duplicate_does_not_append(self) -> None:
        r = ScreenRouter()
        r.register("a", lambda: _make_screen("a"))
        r.register("a", lambda: _make_screen("a2"))
        assert r.screen_names.count("a") == 1

    def test_invalidate_all(self) -> None:
        r = ScreenRouter()
        for i in range(5):
            r.register(f"s{i}", lambda n=i: _make_screen(n))
        for i in range(5):
            r.navigate(f"s{i}")
        r.invalidate()
        assert len(r._cache) == 0
