"""AI Research Assistant screen — read-only rendering of AI syntheses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import VerticalScroll
from textual.widgets import Static

from titan.tui.models import AIScreenState

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 5.0


class AIExplanationWidget(Static):
    """Widget displaying a single AI synthesis card."""

    def compose(self) -> Any:
        yield Static("", id="ai-card-title", classes="widget-title")
        yield Static("", id="ai-card-meta", classes="widget-subtitle")
        yield Static("", id="ai-card-content", classes="widget-body")

    def update_data(self, info: Any) -> None:
        try:
            title = self.query_one("#ai-card-title", Static)
            meta = self.query_one("#ai-card-meta", Static)
            content = self.query_one("#ai-card-content", Static)

            title.update(info.title)
            meta.update(
                f"Provider: {info.provider} | Model: {info.model} | Time: {info.timestamp_str}"
            )
            content.update(info.content)
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass


class AIAssistantScreen(VerticalScroll):
    """TUI view for AI Research Assistant explanations."""

    DEFAULT_CSS = """
    AIAssistantScreen {
        layout: vertical;
        padding: 1 2;
    }
    #ai-title {
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
    .widget-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }
    .widget-subtitle {
        color: $text-muted;
        margin-bottom: 1;
    }
    .widget-body {
        padding: 1;
    }
    .ai-card-container {
        padding: 1;
        border: solid $border;
        height: auto;
        margin-bottom: 1;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AIScreenState()
        self._state_builder: Callable[[], AIScreenState] | None = None
        self._portfolio_widget = AIExplanationWidget(classes="ai-card-container")
        self._strategy_widget = AIExplanationWidget(classes="ai-card-container")

    def compose(self) -> Any:
        yield Static("TITAN AI Research Assistant", id="ai-title")
        yield Static("", id="refresh-indicator")

        with VerticalScroll(id="ai-scroll-container"):
            yield self._portfolio_widget
            yield self._strategy_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], AIScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:  # noqa: BLE001
                self._state = AIScreenState()

        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        self._portfolio_widget.update_data(self._state.portfolio_explanation)
        self._strategy_widget.update_data(self._state.strategy_explanation)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            indicator.update(f"Last refresh: {self._state.last_refresh}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass
