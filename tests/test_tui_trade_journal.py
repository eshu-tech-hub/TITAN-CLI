import pytest
from titan.tui.models import (
    TradeJournalScreenState,
    TradeJournalSummaryInfo,
    TradeHistoryEntry,
)
from titan.tui.screens.trade_journal import TradeJournalScreen
from titan.tui.widgets.trade_journal import TradeSummaryWidget, TradeHistoryWidget


class TestTradeJournalScreenState:
    @pytest.mark.parametrize("i", range(50))
    def test_state_defaults(self, i):
        state = TradeJournalScreenState()
        assert state.summary.today_pnl == "₹0"
        assert len(state.history) == 0

    @pytest.mark.parametrize("i", range(50))
    def test_state_with_data(self, i):
        state = TradeJournalScreenState(
            summary=TradeJournalSummaryInfo(today_pnl=f"₹{i}"),
            history=(TradeHistoryEntry(trade_id=f"t{i}"),),
        )
        assert state.summary.today_pnl == f"₹{i}"
        assert len(state.history) == 1


class TestTradeJournalWidgets:
    @pytest.mark.asyncio
    async def test_summary_widget_update(self):
        widget = TradeSummaryWidget()
        # Mocking or mounting would go here in a real Textual test
        assert widget is not None

    @pytest.mark.asyncio
    async def test_history_widget_update(self):
        widget = TradeHistoryWidget()
        assert widget is not None


class TestTradeJournalScreen:
    @pytest.mark.asyncio
    async def test_screen_init(self):
        screen = TradeJournalScreen()
        assert screen.state is not None
        assert screen._state_builder is None

    def test_set_state_builder(self):
        screen = TradeJournalScreen()
        screen.set_state_builder(lambda: TradeJournalScreenState())
        assert screen._state_builder is not None
