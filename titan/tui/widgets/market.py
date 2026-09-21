"""Market Intelligence dashboard widgets."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label

from titan.tui.models import (
    EvidenceSummaryInfo,
    GreeksSummaryInfo,
    LiquidityInfo,
    MarketStatusInfo,
    OpenInterestSummaryInfo,
    OptionChainSummaryInfo,
    RegimeInfo,
    VolatilityInfo,
)


def _format_float(val: float, suffix: str = "") -> str:
    return f"{val:.2f}{suffix}"


def _format_status(status: str) -> str:
    if not status or status == "Unavailable":
        return "default-class"
    low = status.lower()
    if low in ("bullish", "healthy", "high"):
        return "value-healthy"
    if low in ("bearish", "unhealthy", "low"):
        return "value-unhealthy"
    if low in ("neutral", "degraded", "medium"):
        return "value-degraded"
    return "default-class"


class MarketStatusWidget(Widget):
    """Displays market stream and broker connection status."""

    def __init__(self) -> None:
        super().__init__()
        self._info = MarketStatusInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Market Status", classes="panel-title")
            yield Label("Runtime Status:", classes="label")
            yield Label(
                self._info.runtime_status, id="market-runtime-status", classes="value"
            )
            yield Label("Broker Status:", classes="label")
            yield Label(
                self._info.broker_status, id="market-broker-status", classes="value"
            )
            yield Label("Active Subscriptions:", classes="label")
            yield Label(
                str(self._info.active_subscriptions),
                id="market-subscriptions",
                classes="value",
            )
            yield Label("Last Quote Time:", classes="label")
            yield Label(
                self._info.last_quote_time or "N/A",
                id="market-quote-time",
                classes="value",
            )

    def update_data(self, info: MarketStatusInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                self.query_one("#market-runtime-status", Label).update(
                    info.runtime_status
                )
                self.query_one("#market-broker-status", Label).update(
                    info.broker_status
                )
                self.query_one("#market-subscriptions", Label).update(
                    str(info.active_subscriptions)
                )
                self.query_one("#market-quote-time", Label).update(
                    info.last_quote_time or "N/A"
                )
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class RegimeWidget(Widget):
    """Displays market regime intelligence."""

    def __init__(self) -> None:
        super().__init__()
        self._info = RegimeInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Market Regime", classes="panel-title")
            yield Label("Regime:", classes="label")
            yield Label(
                self._info.regime,
                id="regime-status",
                classes=f"value {_format_status(self._info.regime)}",
            )
            yield Label("Trend Strength:", classes="label")
            yield Label(
                self._info.trend_strength or "N/A", id="regime-trend", classes="value"
            )
            yield Label("Participation:", classes="label")
            yield Label(
                self._info.participation or "N/A",
                id="regime-participation",
                classes="value",
            )
            yield Label("Inst. Confirmation:", classes="label")
            yield Label(
                self._info.institutional_confirmation or "N/A",
                id="regime-inst",
                classes="value",
            )
            yield Label("Confidence:", classes="label")
            yield Label(
                f"{self._info.confidence * 100:.1f}%",
                id="regime-confidence",
                classes="value",
            )

    def update_data(self, info: RegimeInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                lbl = self.query_one("#regime-status", Label)
                lbl.update(info.regime)
                lbl.classes = f"value {_format_status(info.regime)}"
                self.query_one("#regime-trend", Label).update(
                    info.trend_strength or "N/A"
                )
                self.query_one("#regime-participation", Label).update(
                    info.participation or "N/A"
                )
                self.query_one("#regime-inst", Label).update(
                    info.institutional_confirmation or "N/A"
                )
                self.query_one("#regime-confidence", Label).update(
                    f"{info.confidence * 100:.1f}%"
                )
            except Exception:  # noqa: BLE001, S110
                pass


class VolatilityWidget(Widget):
    """Displays volatility intelligence."""

    def __init__(self) -> None:
        super().__init__()
        self._info = VolatilityInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Volatility", classes="panel-title")
            yield Label("Current IV:", classes="label")
            yield Label(
                _format_float(self._info.current_iv, "%"), id="vol-iv", classes="value"
            )
            yield Label("Current HV:", classes="label")
            yield Label(
                _format_float(self._info.current_hv, "%"), id="vol-hv", classes="value"
            )
            yield Label("IV Rank:", classes="label")
            yield Label(
                _format_float(self._info.iv_rank), id="vol-ivr", classes="value"
            )
            yield Label("IV Percentile:", classes="label")
            yield Label(
                _format_float(self._info.iv_percentile), id="vol-ivp", classes="value"
            )
            yield Label("Regime:", classes="label")
            yield Label(self._info.regime, id="vol-regime", classes="value")
            yield Label("Trend:", classes="label")
            yield Label(self._info.trend, id="vol-trend", classes="value")
            yield Label("Overall Bias:", classes="label")
            yield Label(
                self._info.overall_bias,
                id="vol-bias",
                classes=f"value {_format_status(self._info.overall_bias)}",
            )

    def update_data(self, info: VolatilityInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                self.query_one("#vol-iv", Label).update(
                    _format_float(info.current_iv, "%")
                )
                self.query_one("#vol-hv", Label).update(
                    _format_float(info.current_hv, "%")
                )
                self.query_one("#vol-ivr", Label).update(_format_float(info.iv_rank))
                self.query_one("#vol-ivp", Label).update(
                    _format_float(info.iv_percentile)
                )
                self.query_one("#vol-regime", Label).update(info.regime)
                self.query_one("#vol-trend", Label).update(info.trend)
                lbl = self.query_one("#vol-bias", Label)
                lbl.update(info.overall_bias)
                lbl.classes = f"value {_format_status(info.overall_bias)}"
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class LiquidityWidget(Widget):
    """Displays liquidity intelligence."""

    def __init__(self) -> None:
        super().__init__()
        self._info = LiquidityInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Liquidity", classes="panel-title")
            yield Label("Spread:", classes="label")
            yield Label(
                _format_float(self._info.spread), id="liq-spread", classes="value"
            )
            yield Label("Spread %:", classes="label")
            yield Label(
                _format_float(self._info.spread_percent, "%"),
                id="liq-spread-pct",
                classes="value",
            )
            yield Label("Depth Score:", classes="label")
            yield Label(
                _format_float(self._info.depth_score), id="liq-depth", classes="value"
            )
            yield Label("Execution Score:", classes="label")
            yield Label(
                _format_float(self._info.execution_score),
                id="liq-exec",
                classes="value",
            )
            yield Label("Grade:", classes="label")
            yield Label(self._info.execution_grade, id="liq-grade", classes="value")

    def update_data(self, info: LiquidityInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                self.query_one("#liq-spread", Label).update(_format_float(info.spread))
                self.query_one("#liq-spread-pct", Label).update(
                    _format_float(info.spread_percent, "%")
                )
                self.query_one("#liq-depth", Label).update(
                    _format_float(info.depth_score)
                )
                self.query_one("#liq-exec", Label).update(
                    _format_float(info.execution_score)
                )
                self.query_one("#liq-grade", Label).update(info.execution_grade)
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class OptionChainWidget(Widget):
    """Displays option chain summary."""

    def __init__(self) -> None:
        super().__init__()
        self._info = OptionChainSummaryInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Option Chain", classes="panel-title")
            yield Label("Bias:", classes="label")
            yield Label(
                self._info.overall_bias,
                id="opt-bias",
                classes=f"value {_format_status(self._info.overall_bias)}",
            )
            yield Label("Put/Call Ratio:", classes="label")
            yield Label(_format_float(self._info.pcr), id="opt-pcr", classes="value")
            yield Label("Support Level:", classes="label")
            yield Label(
                _format_float(self._info.support), id="opt-support", classes="value"
            )
            yield Label("Resistance Level:", classes="label")
            yield Label(
                _format_float(self._info.resistance),
                id="opt-resistance",
                classes="value",
            )
            yield Label("Bullish Score:", classes="label")
            yield Label(
                _format_float(self._info.bullish_score),
                id="opt-bull",
                classes="value-healthy",
            )
            yield Label("Bearish Score:", classes="label")
            yield Label(
                _format_float(self._info.bearish_score),
                id="opt-bear",
                classes="value-unhealthy",
            )

    def update_data(self, info: OptionChainSummaryInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                lbl = self.query_one("#opt-bias", Label)
                lbl.update(info.overall_bias)
                lbl.classes = f"value {_format_status(info.overall_bias)}"
                self.query_one("#opt-pcr", Label).update(_format_float(info.pcr))
                self.query_one("#opt-support", Label).update(
                    _format_float(info.support)
                )
                self.query_one("#opt-resistance", Label).update(
                    _format_float(info.resistance)
                )
                self.query_one("#opt-bull", Label).update(
                    _format_float(info.bullish_score)
                )
                self.query_one("#opt-bear", Label).update(
                    _format_float(info.bearish_score)
                )
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class OpenInterestWidget(Widget):
    """Displays open interest summary."""

    def __init__(self) -> None:
        super().__init__()
        self._info = OpenInterestSummaryInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Open Interest", classes="panel-title")
            yield Label("Bias:", classes="label")
            yield Label(
                self._info.bias,
                id="oi-bias",
                classes=f"value {_format_status(self._info.bias)}",
            )
            yield Label("Score:", classes="label")
            yield Label(_format_float(self._info.score), id="oi-score", classes="value")
            yield Label("Confidence:", classes="label")
            yield Label(
                f"{self._info.confidence * 100:.1f}%", id="oi-conf", classes="value"
            )

    def update_data(self, info: OpenInterestSummaryInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                lbl = self.query_one("#oi-bias", Label)
                lbl.update(info.bias)
                lbl.classes = f"value {_format_status(info.bias)}"
                self.query_one("#oi-score", Label).update(_format_float(info.score))
                self.query_one("#oi-conf", Label).update(
                    f"{info.confidence * 100:.1f}%"
                )
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class GreeksWidget(Widget):
    """Displays Greeks summary."""

    def __init__(self) -> None:
        super().__init__()
        self._info = GreeksSummaryInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Greeks", classes="panel-title")
            yield Label("Net Delta:", classes="label")
            yield Label(
                _format_float(self._info.net_delta), id="grk-delta", classes="value"
            )
            yield Label("Net Gamma:", classes="label")
            yield Label(
                _format_float(self._info.net_gamma), id="grk-gamma", classes="value"
            )
            yield Label("Net Theta:", classes="label")
            yield Label(
                _format_float(self._info.net_theta), id="grk-theta", classes="value"
            )
            yield Label("Net Vega:", classes="label")
            yield Label(
                _format_float(self._info.net_vega), id="grk-vega", classes="value"
            )
            yield Label("Bias:", classes="label")
            yield Label(
                self._info.overall_bias,
                id="grk-bias",
                classes=f"value {_format_status(self._info.overall_bias)}",
            )

    def update_data(self, info: GreeksSummaryInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                self.query_one("#grk-delta", Label).update(
                    _format_float(info.net_delta)
                )
                self.query_one("#grk-gamma", Label).update(
                    _format_float(info.net_gamma)
                )
                self.query_one("#grk-theta", Label).update(
                    _format_float(info.net_theta)
                )
                self.query_one("#grk-vega", Label).update(_format_float(info.net_vega))
                lbl = self.query_one("#grk-bias", Label)
                lbl.update(info.overall_bias)
                lbl.classes = f"value {_format_status(info.overall_bias)}"
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class EvidenceWidget(Widget):
    """Displays fused evidence summary."""

    def __init__(self) -> None:
        super().__init__()
        self._info = EvidenceSummaryInfo()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel"):
            yield Label("Fused Evidence", classes="panel-title")
            yield Label("Overall Signal:", classes="label")
            yield Label(
                self._info.overall_signal,
                id="ev-signal",
                classes=f"value {_format_status(self._info.overall_signal)}",
            )
            yield Label("Score:", classes="label")
            yield Label(
                _format_float(self._info.overall_score), id="ev-score", classes="value"
            )
            yield Label("Confidence:", classes="label")
            yield Label(
                f"{self._info.confidence * 100:.1f}%", id="ev-conf", classes="value"
            )
            yield Label("Evidence Count:", classes="label")
            yield Label(str(self._info.evidence_count), id="ev-count", classes="value")

    def update_data(self, info: EvidenceSummaryInfo) -> None:
        self._info = info
        if hasattr(self, "_nodes"):
            try:
                lbl = self.query_one("#ev-signal", Label)
                lbl.update(info.overall_signal)
                lbl.classes = f"value {_format_status(info.overall_signal)}"
                self.query_one("#ev-score", Label).update(
                    _format_float(info.overall_score)
                )
                self.query_one("#ev-conf", Label).update(
                    f"{info.confidence * 100:.1f}%"
                )
                self.query_one("#ev-count", Label).update(str(info.evidence_count))
            except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
                pass


class MarketEventsWidget(Widget):
    """Displays dynamic market events."""

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel dynamic-list"):
            yield Label("Market Events", classes="panel-title")
            yield DataTable(id="events-table")

    def on_mount(self) -> None:
        table = self.query_one("#events-table", DataTable)
        table.cursor_type = "none"
        table.zebra_stripes = True
        table.add_columns("Time", "Source", "Message", "Severity")

    def update_data(self, events: tuple) -> None:
        if not hasattr(self, "_nodes"):
            return

        try:
            table = self.query_one("#events-table", DataTable)
            table.clear()

            if not events:
                table.add_row("", "", "No recent events", "")
                return

            for ev in events:
                table.add_row(ev.timestamp, ev.source, ev.message, ev.severity)
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass
