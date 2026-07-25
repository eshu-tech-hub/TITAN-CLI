"""Tests for Market Intelligence TUI Screen."""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, DataTable

from titan.tui.layout import (
    _read_evidence,
    _read_greeks,
    _read_liquidity,
    _read_market_events,
    _read_market_status,
    _read_open_interest,
    _read_option_chain,
    _read_regime,
    _read_volatility,
    build_market_state,
)
from titan.tui.models import (
    EvidenceSummaryInfo,
    GreeksSummaryInfo,
    LiquidityInfo,
    MarketEventEntry,
    MarketScreenState,
    MarketStatusInfo,
    OpenInterestSummaryInfo,
    OptionChainSummaryInfo,
    RegimeInfo,
    VolatilityInfo,
)
from titan.tui.screens.market import MarketScreen
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
    _format_float,
    _format_status,
)


class DummyApp(App):
    """Dummy app for testing widgets outside screen."""

    def compose(self) -> ComposeResult:
        yield MarketStatusWidget()
        yield RegimeWidget()
        yield VolatilityWidget()
        yield LiquidityWidget()
        yield OptionChainWidget()
        yield OpenInterestWidget()
        yield GreeksWidget()
        yield EvidenceWidget()
        yield MarketEventsWidget()


# ─── Model Tests ──────────────────────────────────────────────────────────────


class TestMarketModels:
    """Test Market Intelligence DTOs."""

    @pytest.mark.parametrize(
        "model_cls",
        [
            MarketStatusInfo,
            RegimeInfo,
            VolatilityInfo,
            LiquidityInfo,
            OptionChainSummaryInfo,
            OpenInterestSummaryInfo,
            GreeksSummaryInfo,
            EvidenceSummaryInfo,
            MarketEventEntry,
            MarketScreenState,
        ],
    )
    def test_is_dataclass(self, model_cls: type) -> None:
        assert is_dataclass(model_cls)

    @pytest.mark.parametrize(
        "model_cls, fields",
        [
            (
                MarketStatusInfo,
                [
                    "runtime_status",
                    "broker_status",
                    "active_subscriptions",
                    "last_quote_time",
                ],
            ),
            (
                RegimeInfo,
                [
                    "regime",
                    "trend_strength",
                    "participation",
                    "institutional_confirmation",
                    "confidence",
                ],
            ),
            (
                VolatilityInfo,
                [
                    "current_iv",
                    "current_hv",
                    "iv_rank",
                    "iv_percentile",
                    "regime",
                    "trend",
                    "overall_bias",
                ],
            ),
            (
                LiquidityInfo,
                [
                    "spread",
                    "spread_percent",
                    "depth_score",
                    "execution_score",
                    "execution_grade",
                ],
            ),
            (
                OptionChainSummaryInfo,
                [
                    "overall_bias",
                    "pcr",
                    "support",
                    "resistance",
                    "bullish_score",
                    "bearish_score",
                ],
            ),
            (
                OpenInterestSummaryInfo,
                ["bias", "score", "confidence", "bullish_factors", "bearish_factors"],
            ),
            (
                GreeksSummaryInfo,
                ["net_delta", "net_gamma", "net_theta", "net_vega", "overall_bias"],
            ),
            (
                EvidenceSummaryInfo,
                [
                    "overall_score",
                    "overall_signal",
                    "confidence",
                    "evidence_count",
                    "top_factors",
                ],
            ),
            (MarketEventEntry, ["timestamp", "source", "message", "severity"]),
            (
                MarketScreenState,
                [
                    "market_status",
                    "regime",
                    "volatility",
                    "liquidity",
                    "option_chain",
                    "open_interest",
                    "greeks",
                    "evidence",
                    "events",
                    "last_refresh",
                ],
            ),
        ],
    )
    def test_has_fields(self, model_cls: type, fields: list[str]) -> None:
        obj = model_cls()
        for field in fields:
            assert hasattr(obj, field)

    @pytest.mark.parametrize(
        "model_cls",
        [
            MarketStatusInfo,
            RegimeInfo,
            VolatilityInfo,
            LiquidityInfo,
            OptionChainSummaryInfo,
            OpenInterestSummaryInfo,
            GreeksSummaryInfo,
            EvidenceSummaryInfo,
            MarketEventEntry,
            MarketScreenState,
        ],
    )
    def test_json_serializable(self, model_cls: type) -> None:
        obj = model_cls()
        json_str = json.dumps(asdict(obj))
        assert isinstance(json_str, str)

    def test_frozen_immutability(self) -> None:
        info = MarketStatusInfo()
        with pytest.raises(Exception):
            info.runtime_status = "active"  # type: ignore


# ─── Reader Tests ─────────────────────────────────────────────────────────────


class TestMarketReaders:
    """Test Market layout readers."""

    def test_read_market_status(self) -> None:
        res = _read_market_status()
        assert isinstance(res, MarketStatusInfo)
        assert res.runtime_status in ("Unavailable", "STOPPED", "STARTING", "Live")

    def test_read_regime(self) -> None:
        assert isinstance(_read_regime(), RegimeInfo)

    def test_read_volatility(self) -> None:
        assert isinstance(_read_volatility(), VolatilityInfo)

    def test_read_liquidity(self) -> None:
        assert isinstance(_read_liquidity(), LiquidityInfo)

    def test_read_option_chain(self) -> None:
        assert isinstance(_read_option_chain(), OptionChainSummaryInfo)

    def test_read_open_interest(self) -> None:
        assert isinstance(_read_open_interest(), OpenInterestSummaryInfo)

    def test_read_greeks(self) -> None:
        assert isinstance(_read_greeks(), GreeksSummaryInfo)

    def test_read_evidence(self) -> None:
        assert isinstance(_read_evidence(), EvidenceSummaryInfo)

    def test_read_market_events(self) -> None:
        assert isinstance(_read_market_events(), tuple)
        assert len(_read_market_events()) == 0

    def test_build_market_state(self) -> None:
        state = build_market_state()
        assert isinstance(state, MarketScreenState)
        assert isinstance(state.market_status, MarketStatusInfo)
        assert state.last_refresh != ""


# ─── Helper Tests ─────────────────────────────────────────────────────────────


class TestMarketHelpers:
    """Test formatters and CSS helpers."""

    @pytest.mark.parametrize(
        "val, suffix, expected",
        [
            (1.234, "", "1.23"),
            (1.2, "%", "1.20%"),
            (0.0, "", "0.00"),
        ],
    )
    def test_format_float(self, val: float, suffix: str, expected: str) -> None:
        assert _format_float(val, suffix) == expected

    @pytest.mark.parametrize(
        "status, expected",
        [
            ("bullish", "value-healthy"),
            ("healthy", "value-healthy"),
            ("high", "value-healthy"),
            ("bearish", "value-unhealthy"),
            ("unhealthy", "value-unhealthy"),
            ("low", "value-unhealthy"),
            ("neutral", "value-degraded"),
            ("degraded", "value-degraded"),
            ("medium", "value-degraded"),
            ("Unavailable", "default-class"),
            ("", "default-class"),
            ("unknown", "default-class"),
        ],
    )
    def test_format_status(self, status: str, expected: str) -> None:
        assert _format_status(status) == expected


# ─── Widget Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestMarketWidgets:
    """Test Market intelligence widgets."""

    @pytest.mark.parametrize(
        "widget_cls, model_cls",
        [
            (MarketStatusWidget, MarketStatusInfo),
            (RegimeWidget, RegimeInfo),
            (VolatilityWidget, VolatilityInfo),
            (LiquidityWidget, LiquidityInfo),
            (OptionChainWidget, OptionChainSummaryInfo),
            (OpenInterestWidget, OpenInterestSummaryInfo),
            (GreeksWidget, GreeksSummaryInfo),
            (EvidenceWidget, EvidenceSummaryInfo),
        ],
    )
    def test_widget_init(self, widget_cls: type, model_cls: type) -> None:
        w = widget_cls()
        assert isinstance(w._info, model_cls)

    @pytest.mark.parametrize(
        "widget_cls",
        [
            MarketStatusWidget,
            RegimeWidget,
            VolatilityWidget,
            LiquidityWidget,
            OptionChainWidget,
            OpenInterestWidget,
            GreeksWidget,
            EvidenceWidget,
            MarketEventsWidget,
        ],
    )
    async def test_widget_compose_without_app(self, widget_cls: type) -> None:
        app = DummyApp()
        async with app.run_test():
            w = widget_cls()
            await app.mount(w)
            assert len(w.children) > 0

    @pytest.mark.parametrize(
        "widget_cls, default_info",
        [
            (MarketStatusWidget, MarketStatusInfo()),
            (RegimeWidget, RegimeInfo()),
            (VolatilityWidget, VolatilityInfo()),
            (LiquidityWidget, LiquidityInfo()),
            (OptionChainWidget, OptionChainSummaryInfo()),
            (OpenInterestWidget, OpenInterestSummaryInfo()),
            (GreeksWidget, GreeksSummaryInfo()),
            (EvidenceWidget, EvidenceSummaryInfo()),
            (MarketEventsWidget, ()),
        ],
    )
    def test_widget_update_pre_mount(self, widget_cls: type, default_info: Any) -> None:
        # update_data should quietly return if DOM is not mounted
        w = widget_cls()
        w.update_data(default_info)

    async def test_widgets_full_lifecycle(self) -> None:
        app = DummyApp()
        async with app.run_test():
            for w1 in app.query(MarketStatusWidget):
                w1.update_data(MarketStatusInfo(runtime_status="Live"))
                assert (
                    str(w1.query_one("#market-runtime-status", Label).render())
                    == "Live"
                )

            for w2 in app.query(RegimeWidget):
                w2.update_data(RegimeInfo(regime="Bullish"))
                assert str(w2.query_one("#regime-status", Label).render()) == "Bullish"

            for w3 in app.query(VolatilityWidget):
                w3.update_data(VolatilityInfo(current_iv=0.2))
                assert str(w3.query_one("#vol-iv", Label).render()) == "0.20%"

            for w4 in app.query(LiquidityWidget):
                w4.update_data(LiquidityInfo(spread=0.05))
                assert str(w4.query_one("#liq-spread", Label).render()) == "0.05"

            for w5 in app.query(OptionChainWidget):
                w5.update_data(OptionChainSummaryInfo(overall_bias="Bullish"))
                assert str(w5.query_one("#opt-bias", Label).render()) == "Bullish"

            for w6 in app.query(OpenInterestWidget):
                w6.update_data(OpenInterestSummaryInfo(bias="Bearish"))
                assert str(w6.query_one("#oi-bias", Label).render()) == "Bearish"

            for w7 in app.query(GreeksWidget):
                w7.update_data(GreeksSummaryInfo(net_delta=100.0))
                assert str(w7.query_one("#grk-delta", Label).render()) == "100.00"

            for w8 in app.query(EvidenceWidget):
                w8.update_data(EvidenceSummaryInfo(overall_signal="Strong Bullish"))
                assert (
                    str(w8.query_one("#ev-signal", Label).render()) == "Strong Bullish"
                )

            for w9 in app.query(MarketEventsWidget):
                w9.update_data(
                    (
                        MarketEventEntry(
                            timestamp="10:00",
                            source="sys",
                            message="test",
                            severity="info",
                        ),
                    )
                )
                table = w9.query_one("#events-table", DataTable)
                assert table.row_count == 1
                w9.update_data(())
                assert table.row_count == 1  # Empty state row


# ─── Screen Tests ─────────────────────────────────────────────────────────────


class MarketApp(App):
    def on_mount(self) -> None:
        self.push_screen(MarketScreen())


@pytest.mark.asyncio
class TestMarketScreen:
    """Test MarketScreen lifecycle and navigation."""

    async def test_screen_lifecycle(self) -> None:
        app = MarketApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            screen = app.screen
            assert isinstance(screen, MarketScreen)
            assert screen._refresh_task is not None
            assert not screen._refresh_task.done()

            # Test refresh action
            screen.action_refresh_data()
            assert screen.state.last_refresh != ""

    async def test_screen_navigation_actions(self) -> None:
        app = MarketApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            screen = app.screen
            assert isinstance(screen, MarketScreen)

            # Scroll actions shouldn't crash
            screen.action_scroll_down()
            screen.action_scroll_up()
            screen.action_page_down()
            screen.action_page_up()
            screen.action_scroll_end()
            screen.action_scroll_home()

            # Ensure the vertical scroll exists
            vs = screen.query_one("#market-scroll", VerticalScroll)
            assert vs is not None

    async def test_screen_unmount(self) -> None:
        app = MarketApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            screen = app.screen
            assert isinstance(screen, MarketScreen)
            task = screen._refresh_task
            await app.pop_screen()
            await pilot.pause(0.1)
            if task:
                assert task.cancelled()
