from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from titan.core.evidence import Evidence


class PortfolioScoreBand(str, Enum):
    """Health band for the overall portfolio score (0 = best, 100 = worst)."""

    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    CRITICAL = "critical"


class CorrelationLevel(str, Enum):
    """Correlation strength between portfolio positions."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class HedgingAction(str, Enum):
    """Recommended hedging action for the portfolio."""

    NO_HEDGE_REQUIRED = "no_hedge_required"
    REDUCE_EXPOSURE = "reduce_exposure"
    INCREASE_HEDGE = "increase_hedge"
    DIVERSIFY = "diversify"


@dataclass(frozen=True, slots=True)
class OpenPosition:
    """A single open position in the portfolio.

    Attributes:
        symbol: Instrument symbol.
        instrument_type: Type of instrument (underlying, option, etc.).
        direction: Position direction (long/short/option_buying/option_selling).
        quantity: Number of units/contracts held.
        entry_price: Average entry price.
        current_price: Current market price.
        market_value: Current market value of the position.
        pnl: Unrealised profit or loss.
        sector: Asset sector classification.
        weight: Position weight as fraction of total portfolio capital.
        delta: Option delta (None for non-option positions).
        gamma: Option gamma (None for non-option positions).
        vega: Option vega (None for non-option positions).
        theta: Option theta (None for non-option positions).
    """

    symbol: str
    instrument_type: str
    direction: str
    quantity: int
    entry_price: float
    current_price: float
    market_value: float
    pnl: float = 0.0
    sector: str = ""
    weight: float = 0.0
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None


@dataclass(frozen=True, slots=True)
class ExistingPortfolio:
    """The current portfolio state, supplied externally.

    Attributes:
        positions: Tuple of open positions.
        total_capital: Total portfolio capital.
        cash_reserve: Cash held in reserve.
        name: Optional portfolio name.
    """

    positions: tuple[OpenPosition, ...] = field(default_factory=tuple)
    total_capital: float = 0.0
    cash_reserve: float = 0.0
    name: str = ""


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Current portfolio state derived by the PositionAnalyzer.

    Attributes:
        total_capital: Total portfolio capital.
        cash_reserve: Cash held in reserve.
        capital_used: Capital deployed in positions.
        available_capital: Remaining deployable capital.
        total_market_value: Sum of all position market values.
        total_pnl: Aggregate unrealised P&L.
        position_count: Number of open positions.
        winning_positions: Number of positions with positive P&L.
        losing_positions: Number of positions with negative P&L.
        utilization: Capital used / total capital.
    """

    total_capital: float = 0.0
    cash_reserve: float = 0.0
    capital_used: float = 0.0
    available_capital: float = 0.0
    total_market_value: float = 0.0
    total_pnl: float = 0.0
    position_count: int = 0
    winning_positions: int = 0
    losing_positions: int = 0
    utilization: float = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioExposure:
    """Aggregate portfolio Greeks and directional exposure.

    Attributes:
        net_delta: Sum of all position deltas.
        net_gamma: Sum of all position gammas.
        net_vega: Sum of all position vegas.
        net_theta: Sum of all position thetas.
        directional_bias: Net directional bias (positive = bullish, negative = bearish).
        sector_concentration: Highest single-sector weight.
        symbol_concentration: Highest single-symbol weight.
    """

    net_delta: float | None = None
    net_gamma: float | None = None
    net_vega: float | None = None
    net_theta: float | None = None
    directional_bias: float = 0.0
    sector_concentration: float = 0.0
    symbol_concentration: float = 0.0


@dataclass(frozen=True, slots=True)
class SectorExposure:
    """Exposure breakdown by sector.

    Attributes:
        sector: Sector name.
        total_value: Total market value in this sector.
        weight: Sector weight as fraction of total capital.
        position_count: Number of positions in this sector.
    """

    sector: str
    total_value: float
    weight: float
    position_count: int


@dataclass(frozen=True, slots=True)
class CorrelationAnalysis:
    """Cross-position correlation assessment.

    Attributes:
        highly_correlated_pairs: Number of highly correlated position pairs.
        duplicate_exposure: Whether duplicate exposure to the same symbol exists.
        index_concentration: Whether the portfolio is concentrated in an index.
        sector_correlation: Highest inter-sector correlation level.
        overall_correlation_level: Aggregate correlation risk level.
    """

    highly_correlated_pairs: int = 0
    duplicate_exposure: bool = False
    index_concentration: bool = False
    sector_correlation: CorrelationLevel = CorrelationLevel.LOW
    overall_correlation_level: CorrelationLevel = CorrelationLevel.LOW


@dataclass(frozen=True, slots=True)
class HedgingRecommendation:
    """Structured hedging recommendation.

    Attributes:
        action: Recommended hedging action.
        reason: Human-readable reason for the recommendation.
        suggested_instruments: Suggested hedging instruments.
        max_cost: Maximum cost of the recommended hedge.
    """

    action: HedgingAction = HedgingAction.NO_HEDGE_REQUIRED
    reason: str = ""
    suggested_instruments: tuple[str, ...] = field(default_factory=tuple)
    max_cost: float = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioDecisionContext:
    """Actionable decisions from the Portfolio Intelligence Engine.

    Attributes:
        allow_trade: Whether the new trade can be accepted.
        reduce_position: Whether existing positions should be reduced.
        block_trade: Whether the new trade is blocked.
        hedging_required: Whether portfolio hedging is needed.
        max_contracts: Maximum contracts for the new trade.
        remaining_risk_capacity: How much risk the portfolio can absorb.
        remaining_capital: How much capital remains for new trades.
        confidence: Confidence in the portfolio assessment (0.0-1.0).
    """

    allow_trade: bool = False
    reduce_position: bool = False
    block_trade: bool = False
    hedging_required: bool = False
    max_contracts: int = 0
    remaining_risk_capacity: float = 0.0
    remaining_capital: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioExplanation:
    """Structured explanation of the portfolio analysis.

    Attributes:
        portfolio_summary: Summary of the current portfolio state.
        exposure: Explanation of portfolio exposure.
        correlation: Explanation of correlation risks.
        capital_allocation: Explanation of capital allocation.
        hedging: Explanation of hedging recommendations.
        recommendation: Summary recommendation.
    """

    portfolio_summary: str = ""
    exposure: str = ""
    correlation: str = ""
    capital_allocation: str = ""
    hedging: str = ""
    recommendation: str = ""


@dataclass(frozen=True, slots=True)
class ExposureAnalysis:
    """Institutional view of portfolio exposure."""

    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    position_count: int = 0
    largest_position_symbol: str = ""
    largest_position_weight: float = 0.0
    smallest_position_symbol: str = ""
    smallest_position_weight: float = 0.0
    concentration_score: float = 0.0


@dataclass(frozen=True, slots=True)
class AllocationAnalysis:
    """Breakdown of capital allocation."""

    by_instrument: Mapping[str, float] = field(default_factory=dict)
    by_strategy: Mapping[str, float] = field(default_factory=dict)
    by_sector: Mapping[str, float] = field(default_factory=dict)
    by_asset_class: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DiversificationAnalysis:
    """Measurement of portfolio diversification."""

    number_of_symbols: int = 0
    number_of_strategies: int = 0
    sector_distribution: Mapping[str, float] = field(default_factory=dict)
    concentration_risk: float = 0.0
    diversification_score: float = 0.0


@dataclass(frozen=True, slots=True)
class DrawdownAnalysis:
    """Drawdown and equity curve metrics."""

    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0
    recovery_percentage: float = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioPerformance:
    """Institutional portfolio performance metrics."""

    win_rate: float = 0.0
    loss_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    average_winner: float = 0.0
    average_loser: float = 0.0
    average_holding_time: float = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioAnalysis:
    """Complete Portfolio Intelligence Engine output.

    Attributes:
        portfolio_name: Name of the portfolio analysed.
        snapshot: Current portfolio snapshot.
        exposure: Portfolio Greeks and directional exposure.
        sector_exposures: Breakdown by sector.
        correlation: Cross-position correlation assessment.
        hedging: Hedging recommendation.
        portfolio_score: Portfolio health score (0-100).
        portfolio_band: Portfolio health band.
        decision_context: Actionable portfolio decisions.
        allow_trade: Whether the proposed trade is allowed.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured explanation.
        warnings: Non-fatal warnings.
        metadata: Producer context.
        timestamp: When the analysis was computed.
    """

    portfolio_name: str = ""
    snapshot: PortfolioSnapshot = field(default_factory=PortfolioSnapshot)
    exposure: PortfolioExposure = field(default_factory=PortfolioExposure)
    sector_exposures: tuple[SectorExposure, ...] = field(default_factory=tuple)
    correlation: CorrelationAnalysis = field(default_factory=CorrelationAnalysis)
    hedging: HedgingRecommendation = field(default_factory=HedgingRecommendation)
    portfolio_score: float = 0.0
    portfolio_band: PortfolioScoreBand = PortfolioScoreBand.EXCELLENT
    decision_context: PortfolioDecisionContext = field(
        default_factory=PortfolioDecisionContext
    )
    allow_trade: bool = False
    evidence: Evidence | None = None
    explanation: PortfolioExplanation | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
