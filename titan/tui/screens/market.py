"""Market Intelligence dashboard screen."""

import asyncio
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll

from titan.tui.models import MarketScreenState
from titan.tui.widgets.market import (
    EvidenceWidget,
    GreeksWidget,
    LiquidityWidget,
    MarketEventsWidget,
    MarketStatusWidget,
    OpenInterestWidget,
    OptionChainWidget,
    RegimeWidget,
    VolatilityWidget,
)


class MarketScreen(VerticalScroll):
    """Market Intelligence view."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("r", "refresh_data", "Refresh"),
        Binding("escape", "back", "Back"),
        Binding("up", "scroll_up", "Scroll Up", show=False),
        Binding("down", "scroll_down", "Scroll Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("home", "scroll_home", "Home", show=False),
        Binding("end", "scroll_end", "End", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.state = MarketScreenState()
        self._refresh_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="market-scroll"):
            with Horizontal(classes="row"):
                yield MarketStatusWidget()
                yield RegimeWidget()
                yield VolatilityWidget()
                yield LiquidityWidget()
            with Horizontal(classes="row"):
                yield OptionChainWidget()
                yield OpenInterestWidget()
                yield GreeksWidget()
                yield EvidenceWidget()
            with Horizontal(classes="row"):
                yield MarketEventsWidget()

    def on_mount(self) -> None:
        self._refresh_state()
        self._refresh_task = asyncio.create_task(self._tick_refresh())

    def on_unmount(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()

    async def _tick_refresh(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            self._refresh_state()

    def _refresh_state(self) -> None:
        from titan.tui.layout import build_market_state

        self.state = build_market_state()
        self._update_widgets()

    def _update_widgets(self) -> None:
        for w_market in self.query(MarketStatusWidget):
            w_market.update_data(self.state.market_status)
        for w_regime in self.query(RegimeWidget):
            w_regime.update_data(self.state.regime)
        for w_vol in self.query(VolatilityWidget):
            w_vol.update_data(self.state.volatility)
        for w_liq in self.query(LiquidityWidget):
            w_liq.update_data(self.state.liquidity)
        for w_opt in self.query(OptionChainWidget):
            w_opt.update_data(self.state.option_chain)
        for w_oi in self.query(OpenInterestWidget):
            w_oi.update_data(self.state.open_interest)
        for w_grk in self.query(GreeksWidget):
            w_grk.update_data(self.state.greeks)
        for w_ev in self.query(EvidenceWidget):
            w_ev.update_data(self.state.evidence)
        for w_events in self.query(MarketEventsWidget):
            w_events.update_data(self.state.events)

    def action_refresh_data(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_scroll_up(self) -> None:
        self.query_one("#market-scroll", VerticalScroll).scroll_up()

    def action_scroll_down(self) -> None:
        self.query_one("#market-scroll", VerticalScroll).scroll_down()

    def action_page_up(self) -> None:
        self.query_one("#market-scroll", VerticalScroll).scroll_page_up()

    def action_page_down(self) -> None:
        self.query_one("#market-scroll", VerticalScroll).scroll_page_down()

    def action_scroll_home(self) -> None:
        self.query_one("#market-scroll", VerticalScroll).scroll_home()

    def action_scroll_end(self) -> None:
        self.query_one("#market-scroll", VerticalScroll).scroll_end()
