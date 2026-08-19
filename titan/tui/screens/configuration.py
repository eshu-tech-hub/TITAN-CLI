"""Configuration & Deployment screen — read-only visualization of operational state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.models import ConfigurationScreenState
from titan.tui.widgets.configuration import (
    BackupWidget,
    ConfigurationWidget,
    DeploymentHistoryWidget,
    DeploymentWidget,
    EnvironmentWidget,
    ServicesWidget,
    ValidationDetailsWidget,
    VersionWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class ConfigurationScreen(Screen):
    """Configuration & Deployment screen with seven operational widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS: ClassVar[str] = """
    ConfigurationScreen {
        layout: vertical;
        padding: 1 2;
    }
    #config-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #refresh-indicator {
        text-align: right;
        height: 1;
        color: $text-muted;
        dock: top;
    }
    #widgets-container {
        height: 1fr;
    }
    #config-row-1 {
        height: auto;
    }
    #config-row-1 > * {
        width: 1fr;
    }
    #config-row-3 {
        height: auto;
    }
    #config-row-3 > * {
        width: 1fr;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("up", "scroll_up_line", "Scroll Up"),
        ("down", "scroll_down_line", "Scroll Down"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
        ("home", "scroll_top", "Scroll Top"),
        ("end", "scroll_bottom", "Scroll Bottom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ConfigurationScreenState()
        self._state_builder: Callable[[], ConfigurationScreenState] | None = None
        self._config_widget: ConfigurationWidget | None = None
        self._env_widget: EnvironmentWidget | None = None
        self._deployment_widget: DeploymentWidget | None = None
        self._version_widget: VersionWidget | None = None
        self._services_widget: ServicesWidget | None = None
        self._validation_widget: ValidationDetailsWidget | None = None
        self._backup_widget: BackupWidget | None = None
        self._history_widget: DeploymentHistoryWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Configuration & Deployment", id="config-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="widgets-container"):
            with Horizontal(id="config-row-1"):
                self._config_widget = ConfigurationWidget(id="config-widget")
                self._validation_widget = ValidationDetailsWidget(
                    id="validation-widget"
                )
                self._env_widget = EnvironmentWidget(id="env-widget")
                self._deployment_widget = DeploymentWidget(id="deployment-widget")
                self._version_widget = VersionWidget(id="version-widget")
                yield self._config_widget
                yield self._env_widget
                yield self._deployment_widget
                yield self._version_widget

            self._services_widget = ServicesWidget(id="services-widget")
            yield self._services_widget

            with Horizontal(id="config-row-3"):
                self._backup_widget = BackupWidget(id="backup-widget")
                self._history_widget = DeploymentHistoryWidget(id="history-widget")
                yield self._backup_widget
                yield self._history_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(
        self, builder: Callable[[], ConfigurationScreenState]
    ) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = ConfigurationScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._config_widget is not None:
            self._config_widget.update_data(self._state.configuration)
        if self._validation_widget is not None:
            self._validation_widget.update_data(self._state.configuration)
        if self._env_widget is not None:
            self._env_widget.update_data(self._state.environment)
        if self._deployment_widget is not None:
            self._deployment_widget.update_data(self._state.deployment)
        if self._version_widget is not None:
            self._version_widget.update_data(self._state.version)
        if self._services_widget is not None:
            self._services_widget.update_data(self._state.services)
        if self._backup_widget is not None:
            self._backup_widget.update_data(self._state.backup)
        if self._history_widget is not None:
            self._history_widget.update_data(self._state.history)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now(UTC).strftime("%H:%M:%S")
            indicator.update(f"Last refresh: {now}")
        except Exception:
            pass

    # ─── Actions ──────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_scroll_up_line(self) -> None:
        try:
            self.query_one(VerticalScroll).scroll_up()
        except Exception:
            pass

    def action_scroll_down_line(self) -> None:
        try:
            self.query_one(VerticalScroll).scroll_down()
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        try:
            self.query_one(VerticalScroll).scroll_page_up()
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        try:
            self.query_one(VerticalScroll).scroll_page_down()
        except Exception:
            pass

    def action_scroll_top(self) -> None:
        try:
            self.query_one(VerticalScroll).scroll_home()
        except Exception:
            pass

    def action_scroll_bottom(self) -> None:
        try:
            self.query_one(VerticalScroll).scroll_end()
        except Exception:
            pass

    @property
    def state(self) -> ConfigurationScreenState:
        return self._state
