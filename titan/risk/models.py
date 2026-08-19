from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from titan.core.evidence import Evidence
from titan.events.models import EventAnalysis, NewsAnalysis
from titan.intelligence.fusion.models import IntelligenceFusion
from titan.market.intelligence.models import MarketRegimeAnalysis
from titan.options.analytics.models import (
    DealerPositioningAnalysis,
    GammaExposureAnalysis,
    LiquidityAnalysis,
    VolatilityAnalysis,
)
from titan.trading.models import TradeQualification


class RiskProfile(str, Enum):
    """Risk tolerance profile for position sizing and capital allocation."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    INSTITUTIONAL = "institutional"


class RiskScoreBand(str, Enum):
    """Risk score band classification from 0 to 100."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class RiskDimension(str, Enum):
    """Risk dimensions assessed during exposure analysis."""

    DIRECTIONAL = "directional"
    VOLATILITY = "volatility"
    EVENT = "event"
    SECTOR = "sector"
    LIQUIDITY = "liquidity"


class ExposureLevel(str, Enum):
    """Exposure assessment level for a risk dimension."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True, slots=True)
class RiskProfileConfig:
    """Configuration parameters for a risk profile.

    Attributes:
        max_risk_per_trade_pct: Maximum risk per trade as fraction of capital.
        max_position_size_pct: Maximum position size as fraction of capital.
        max_leverage: Maximum allowed leverage.
        max_daily_loss_pct: Maximum daily loss limit as fraction of capital.
        max_concentration_pct: Maximum single-position concentration.
        stop_loss_atr_multiplier: ATR multiplier for stop loss placement.
        target_atr_multipliers: ATR multipliers for target levels.
        kelly_fraction: Fraction of Kelly Criterion to use.
        min_confidence_threshold: Minimum confidence to enter a trade.
    """

    max_risk_per_trade_pct: float
    max_position_size_pct: float
    max_leverage: float
    max_daily_loss_pct: float
    max_concentration_pct: float
    stop_loss_atr_multiplier: float
    target_atr_multipliers: tuple[float, float, float]
    kelly_fraction: float
    min_confidence_threshold: float


RISK_PROFILE_MAP: Mapping[RiskProfile, RiskProfileConfig] = {
    RiskProfile.CONSERVATIVE: RiskProfileConfig(
        max_risk_per_trade_pct=0.02,
        max_position_size_pct=0.10,
        max_leverage=1.0,
        max_daily_loss_pct=0.03,
        max_concentration_pct=0.10,
        stop_loss_atr_multiplier=1.0,
        target_atr_multipliers=(1.0, 1.5, 2.0),
        kelly_fraction=0.25,
        min_confidence_threshold=0.6,
    ),
    RiskProfile.MODERATE: RiskProfileConfig(
        max_risk_per_trade_pct=0.03,
        max_position_size_pct=0.15,
        max_leverage=1.5,
        max_daily_loss_pct=0.05,
        max_concentration_pct=0.15,
        stop_loss_atr_multiplier=1.5,
        target_atr_multipliers=(1.5, 2.5, 3.5),
        kelly_fraction=0.50,
        min_confidence_threshold=0.5,
    ),
    RiskProfile.AGGRESSIVE: RiskProfileConfig(
        max_risk_per_trade_pct=0.05,
        max_position_size_pct=0.25,
        max_leverage=2.0,
        max_daily_loss_pct=0.08,
        max_concentration_pct=0.25,
        stop_loss_atr_multiplier=2.0,
        target_atr_multipliers=(2.0, 3.0, 5.0),
        kelly_fraction=0.75,
        min_confidence_threshold=0.4,
    ),
    RiskProfile.INSTITUTIONAL: RiskProfileConfig(
        max_risk_per_trade_pct=0.01,
        max_position_size_pct=0.05,
        max_leverage=1.0,
        max_daily_loss_pct=0.02,
        max_concentration_pct=0.05,
        stop_loss_atr_multiplier=0.5,
        target_atr_multipliers=(0.5, 1.0, 1.5),
        kelly_fraction=0.10,
        min_confidence_threshold=0.7,
    ),
}


@dataclass(frozen=True, slots=True)
class RiskScore:
    """Normalised risk score from 0 (lowest risk) to 100 (highest risk).

    Attributes:
        value: Risk score from 0 to 100.
        band: Risk score band classification.
    """

    value: float
    band: RiskScoreBand

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise ValueError("RiskScore value must be between 0 and 100.")


@dataclass(frozen=True, slots=True)
class PositionSizing:
    """Position sizing output from the Position Sizing Engine.

    Attributes:
        maximum_capital: Maximum capital allocated to this trade.
        risk_per_trade: Maximum monetary risk for this trade.
        units: Number of units (shares) to trade.
        contracts: Number of option contracts to trade.
        maximum_quantity: Maximum allowed quantity.
        capital_utilization: Ratio of used capital to available (0-1).
    """

    maximum_capital: float
    risk_per_trade: float
    units: int
    contracts: int
    maximum_quantity: int
    capital_utilization: float


@dataclass(frozen=True, slots=True)
class StopLossPlan:
    """Stop loss plan output from the Stop Loss Engine.

    Attributes:
        technical_stop: Price level based on technical structure.
        volatility_stop: Price level based on ATR or IV.
        time_stop: Time-based stop description.
        invalidation_level: Price level invalidating the trade thesis.
        emergency_stop: Maximum acceptable loss price level.
        recommended_stop: The recommended stop price level.
    """

    technical_stop: float | None = None
    volatility_stop: float | None = None
    time_stop: str | None = None
    invalidation_level: float | None = None
    emergency_stop: float | None = None
    recommended_stop: float = 0.0


@dataclass(frozen=True, slots=True)
class TargetPlan:
    """Target plan output from the Target Engine.

    Attributes:
        target_1: First profit target price level.
        target_2: Second profit target price level.
        target_3: Third profit target price level.
        trailing_stop_trigger: Price level to activate trailing stop.
        expected_risk_reward: Expected risk-reward ratio.
    """

    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0
    trailing_stop_trigger: float = 0.0
    expected_risk_reward: float = 0.0


@dataclass(frozen=True, slots=True)
class CapitalAllocation:
    """Capital allocation output from the Capital Allocation Engine.

    Attributes:
        capital_used: Capital currently deployed in positions.
        available_capital: Remaining capital available for trading.
        daily_exposure: Total daily exposure from current positions.
        weekly_exposure: Total weekly exposure from current positions.
        maximum_allocation: Maximum allocation for this trade.
        portfolio_concentration: Largest position as fraction of total capital.
    """

    capital_used: float = 0.0
    available_capital: float = 0.0
    daily_exposure: float = 0.0
    weekly_exposure: float = 0.0
    maximum_allocation: float = 0.0
    portfolio_concentration: float = 0.0


@dataclass(frozen=True, slots=True)
class ExposureAssessment:
    """Exposure assessment output from the Exposure Engine.

    Attributes:
        directional_exposure: Assessment of directional risk.
        volatility_exposure: Assessment of volatility risk.
        event_exposure: Assessment of event-driven risk.
        sector_exposure: Assessment of sector concentration risk.
        liquidity_exposure: Assessment of liquidity risk.
        overall_portfolio_risk: Overall portfolio risk assessment.
    """

    directional_exposure: ExposureLevel = ExposureLevel.LOW
    volatility_exposure: ExposureLevel = ExposureLevel.LOW
    event_exposure: ExposureLevel = ExposureLevel.LOW
    sector_exposure: ExposureLevel = ExposureLevel.LOW
    liquidity_exposure: ExposureLevel = ExposureLevel.LOW
    overall_portfolio_risk: ExposureLevel = ExposureLevel.LOW


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Decision context generated by the Risk Engine.

    Attributes:
        reduce_size: Whether position size should be reduced.
        normal_size: Whether normal position sizing is appropriate.
        increase_size: Whether position size can be increased.
        avoid_trade: Whether the trade should be avoided entirely.
        hedging_required: Whether hedging is required.
        maximum_contracts: Maximum number of contracts recommended.
        confidence: Confidence in the risk assessment (0-1).
    """

    reduce_size: bool = False
    normal_size: bool = False
    increase_size: bool = False
    avoid_trade: bool = False
    hedging_required: bool = False
    maximum_contracts: int = 0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class RiskExplanation:
    """Structured explanation of the risk analysis.

    Attributes:
        position_size: Explanation of position sizing decision.
        capital_allocation: Explanation of capital allocation.
        stop_loss: Explanation of stop loss placement.
        targets: Explanation of target selection.
        exposure: Explanation of exposure assessment.
        overall_risk_assessment: Summary risk assessment.
    """

    position_size: str = ""
    capital_allocation: str = ""
    stop_loss: str = ""
    targets: str = ""
    exposure: str = ""
    overall_risk_assessment: str = ""


@dataclass(frozen=True, slots=True)
class PositionInfo:
    """Current position information for capital allocation calculations.

    Attributes:
        symbol: Instrument symbol.
        direction: Position direction (long/short).
        quantity: Number of units held.
        entry_price: Average entry price.
        current_price: Current market price.
        market_value: Current market value of the position.
        pnl: Unrealised profit or loss.
    """

    symbol: str
    direction: str
    quantity: int
    entry_price: float
    current_price: float
    market_value: float
    pnl: float = 0.0


@dataclass(frozen=True, slots=True)
class RiskInput:
    """Aggregated input for the Risk Intelligence Engine.

    All intelligence fields are optional — missing components degrade
    gracefully. The trade_qualification field is required as the engine
    operates on qualified trade opportunities.

    Attributes:
        trade_qualification: Trade Qualification Engine output.
        market_regime: Market Regime Intelligence output.
        volatility: Volatility Intelligence output.
        liquidity: Liquidity Intelligence output.
        dealer_positioning: Dealer Positioning Intelligence output.
        gamma_exposure: Gamma Exposure Intelligence output.
        event_analysis: Event Intelligence output.
        news_analysis: News Intelligence output.
        intelligence_fusion: Intelligence Fusion output.
        underlying_price: Current underlying asset price.
        entry_price: Proposed entry price for the trade.
    """

    trade_qualification: TradeQualification
    market_regime: MarketRegimeAnalysis | None = None
    volatility: VolatilityAnalysis | None = None
    liquidity: LiquidityAnalysis | None = None
    dealer_positioning: DealerPositioningAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None
    event_analysis: EventAnalysis | None = None
    news_analysis: NewsAnalysis | None = None
    intelligence_fusion: IntelligenceFusion | None = None
    underlying_price: float | None = None
    entry_price: float | None = None


@dataclass(frozen=True, slots=True)
class RiskAnalysis:
    """Complete Risk Intelligence Engine output.

    This is the top-level result containing all risk planning outputs
    for a qualified trade opportunity.

    Attributes:
        risk_profile: The risk profile used for analysis.
        risk_score: Normalised risk score (0-100) with band.
        position_sizing: Position sizing plan.
        stop_loss: Stop loss plan.
        targets: Target plan.
        capital_allocation: Capital allocation plan.
        exposure: Exposure assessment.
        decision_context: Decision context with sizing guidance.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
        warnings: Non-fatal warnings generated during analysis.
        metadata: Producer context.
        timestamp: When the analysis was computed.
    """

    risk_profile: RiskProfile
    risk_score: RiskScore
    position_sizing: PositionSizing
    stop_loss: StopLossPlan
    targets: TargetPlan
    capital_allocation: CapitalAllocation
    exposure: ExposureAssessment
    decision_context: DecisionContext
    evidence: Evidence | None = None
    explanation: RiskExplanation | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
