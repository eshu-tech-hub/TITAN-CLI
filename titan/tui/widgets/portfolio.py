from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from textual.reactive import reactive

from titan.portfolio.models import (
    AllocationAnalysis,
    DiversificationAnalysis,
    DrawdownAnalysis,
    ExposureAnalysis,
    PortfolioPerformance,
    PortfolioSnapshot,
)


class PortfolioSummaryWidget(Static):
    """Displays high-level portfolio metrics."""

    snapshot: reactive[PortfolioSnapshot | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Portfolio Summary", classes="widget-title")
            yield Static(id="summary_data")

    def watch_snapshot(self, snapshot: PortfolioSnapshot | None) -> None:
        if snapshot:
            data = (
                f"Total Capital: ${snapshot.total_capital:,.2f}\n"
                f"Capital Used:  ${snapshot.capital_used:,.2f}\n"
                f"Available:     ${snapshot.available_capital:,.2f}\n"
                f"Total PnL:     ${snapshot.total_pnl:,.2f}\n"
                f"Positions:     {snapshot.position_count} ({snapshot.winning_positions} W / {snapshot.losing_positions} L)\n"
                f"Utilization:   {snapshot.utilization * 100:.1f}%"
            )
            self.query_one("#summary_data", Static).update(data)


class ExposureWidget(Static):
    """Displays gross and net exposure metrics."""

    exposure: reactive[ExposureAnalysis | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Exposure Analysis", classes="widget-title")
            yield Static(id="exposure_data")

    def watch_exposure(self, exposure: ExposureAnalysis | None) -> None:
        if exposure:
            data = (
                f"Gross Exp:     ${exposure.gross_exposure:,.2f}\n"
                f"Net Exp:       ${exposure.net_exposure:,.2f}\n"
                f"Long / Short:  ${exposure.long_exposure:,.2f} / ${exposure.short_exposure:,.2f}\n"
                f"Concentration: {exposure.concentration_score:.2f} (HHI)\n"
                f"Largest Pos:   {exposure.largest_position_symbol} ({exposure.largest_position_weight * 100:.1f}%)"
            )
            self.query_one("#exposure_data", Static).update(data)


class AllocationWidget(Static):
    """Displays capital allocation by asset class and instrument."""

    allocation: reactive[AllocationAnalysis | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Capital Allocation", classes="widget-title")
            yield Static(id="allocation_data")

    def watch_allocation(self, allocation: AllocationAnalysis | None) -> None:
        if allocation:
            lines = []
            for asset, weight in sorted(allocation.by_asset_class.items()):
                lines.append(f"{asset}: {weight * 100:.1f}%")
            self.query_one("#allocation_data", Static).update(
                "\n".join(lines) if lines else "No Data"
            )


class DiversificationWidget(Static):
    """Displays diversification score and metrics."""

    diversification: reactive[DiversificationAnalysis | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Diversification", classes="widget-title")
            yield Static(id="div_data")

    def watch_diversification(self, div: DiversificationAnalysis | None) -> None:
        if div:
            data = (
                f"Score:         {div.diversification_score:.1f} / 100\n"
                f"Symbols:       {div.number_of_symbols}\n"
                f"Strategies:    {div.number_of_strategies}"
            )
            self.query_one("#div_data", Static).update(data)


class DrawdownWidget(Static):
    """Displays drawdown and equity metrics."""

    drawdown: reactive[DrawdownAnalysis | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Drawdown Analysis", classes="widget-title")
            yield Static(id="dd_data")

    def watch_drawdown(self, dd: DrawdownAnalysis | None) -> None:
        if dd:
            data = (
                f"Current DD:    ${dd.current_drawdown:,.2f}\n"
                f"Max DD:        ${dd.max_drawdown:,.2f}\n"
                f"Peak Equity:   ${dd.peak_equity:,.2f}\n"
                f"Current Eq:    ${dd.current_equity:,.2f}\n"
                f"Recovery:      {dd.recovery_percentage:.1f}%"
            )
            self.query_one("#dd_data", Static).update(data)


class PerformanceWidget(Static):
    """Displays institutional performance metrics."""

    performance: reactive[PortfolioPerformance | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Performance Metrics", classes="widget-title")
            yield Static(id="perf_data")

    def watch_performance(self, perf: PortfolioPerformance | None) -> None:
        if perf:
            data = (
                f"Win / Loss:    {perf.win_rate * 100:.1f}% / {perf.loss_rate * 100:.1f}%\n"
                f"Profit Factor: {perf.profit_factor:.2f}\n"
                f"Expectancy:    ${perf.expectancy:,.2f}\n"
                f"Avg Win:       ${perf.average_winner:,.2f}\n"
                f"Avg Loss:      ${perf.average_loser:,.2f}\n"
                f"Avg Hold Time: {perf.average_holding_time:.1f}s"
            )
            self.query_one("#perf_data", Static).update(data)


class SectorExposureWidget(Static):
    """Displays exposure breakdown by sector."""

    allocation: reactive[AllocationAnalysis | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Sector Exposure", classes="widget-title")
            yield Static(id="sector_data")

    def watch_allocation(self, allocation: AllocationAnalysis | None) -> None:
        if allocation:
            lines = []
            for sector, weight in sorted(
                allocation.by_sector.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"{sector}: {weight * 100:.1f}%")
            self.query_one("#sector_data", Static).update(
                "\n".join(lines) if lines else "No Data"
            )


class StrategyPerformanceWidget(Static):
    """Displays performance breakdown by strategy."""

    allocation: reactive[AllocationAnalysis | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Strategy Breakdown", classes="widget-title")
            yield Static(id="strategy_data")

    def watch_allocation(self, allocation: AllocationAnalysis | None) -> None:
        if allocation:
            lines = []
            for strategy, weight in sorted(
                allocation.by_strategy.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"{strategy}: {weight * 100:.1f}%")
            self.query_one("#strategy_data", Static).update(
                "\n".join(lines) if lines else "No Data"
            )
