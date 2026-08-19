from __future__ import annotations

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
    CharmExposureAnalysis,
    DealerPositioningAnalysis,
    GammaExposureAnalysis,
    GreeksAnalysis,
    LiquidityAnalysis,
    OptionChainAnalysis,
    VannaExposureAnalysis,
    VolatilityAnalysis,
)
from titan.risk.models import RiskAnalysis
from titan.trading.models import TradeDirection, TradeQualification


class DecisionAction(str, Enum):
    """Final trading decision produced by the Decision Engine."""

    BUY = "buy"
    SELL = "sell"
    NO_TRADE = "no_trade"
    WATCHLIST = "watchlist"
    WAIT = "wait"


class InstrumentType(str, Enum):
    """Instrument type for the trade decision."""

    UNDERLYING = "underlying"
    FUTURES = "futures"
    CALL_OPTION = "call_option"
    PUT_OPTION = "put_option"


class HoldingStyle(str, Enum):
    """Holding period style for the trade decision."""

    SCALP = "scalp"
    DAY_TRADE = "day_trade"
    SWING = "swing"
    POSITION = "position"


class DecisionRank(str, Enum):
    """Opportunity rank assigned during decision ranking."""

    BEST = "best"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class DecisionInput:
    """Aggregated input for the Decision Engine.

    Consumes the complete output of every intelligence module, the
    Trade Qualification Engine, and the Risk Intelligence Engine to
    produce a single institutional trade decision.

    All fields except trade_qualification and risk_analysis are
    optional — missing components degrade gracefully.

    Attributes:
        trade_qualification: Trade Qualification Engine output.
        risk_analysis: Risk Intelligence Engine output.
        market_regime: Market Regime Intelligence output.
        option_chain: Option Chain Intelligence output.
        greeks: Greeks Intelligence output.
        liquidity: Liquidity Intelligence output.
        volatility: Volatility Intelligence output.
        dealer_positioning: Dealer Positioning Intelligence output.
        gamma_exposure: Gamma Exposure Intelligence output.
        vanna_exposure: Vanna Exposure Intelligence output.
        charm_exposure: Charm Exposure Intelligence output.
        event_analysis: Event Intelligence output.
        news_analysis: News Intelligence output.
        intelligence_fusion: Intelligence Fusion output.
        underlying_price: Current underlying asset price.
        symbol: Instrument symbol for the trade.
    """

    trade_qualification: TradeQualification
    risk_analysis: RiskAnalysis
    market_regime: MarketRegimeAnalysis | None = None
    option_chain: OptionChainAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    liquidity: LiquidityAnalysis | None = None
    volatility: VolatilityAnalysis | None = None
    dealer_positioning: DealerPositioningAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None
    vanna_exposure: VannaExposureAnalysis | None = None
    charm_exposure: CharmExposureAnalysis | None = None
    event_analysis: EventAnalysis | None = None
    news_analysis: NewsAnalysis | None = None
    intelligence_fusion: IntelligenceFusion | None = None
    underlying_price: float | None = None
    symbol: str = ""


@dataclass(frozen=True, slots=True)
class TradeDecision:
    """Complete institutional trade decision produced by the Decision Engine.

    This is the final output of the TITAN decision pipeline. It contains
    everything needed by the Broker Layer to execute, but performs no
    execution itself.

    Attributes:
        decision: Final trading action.
        trade_direction: Direction of the trade (long/short/option).
        instrument_type: Type of instrument to trade.
        symbol: Instrument symbol.
        expiry: Option expiry date (for options).
        strike: Option strike price (for options).
        entry_strategy: Description of the entry approach.
        stop_loss_reference: Recommended stop loss price.
        target_reference: Recommended take-profit target.
        holding_style: Intended holding period style.
        rank: Opportunity ranking.
        confidence: Overall confidence in the decision (0.0-1.0).
        probability: Estimated probability of success (0.0-1.0).
        trade_score: Normalised trade quality score (0-100).
        institutional_grade: Whether the decision meets institutional grade.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
        warnings: Non-fatal warnings generated during decision.
        metadata: Producer context.
        timestamp: When the decision was computed.
    """

    decision: DecisionAction
    trade_direction: TradeDirection
    instrument_type: InstrumentType
    symbol: str
    expiry: str | None = None
    strike: float | None = None
    entry_strategy: str = ""
    stop_loss_reference: float = 0.0
    target_reference: float = 0.0
    holding_style: HoldingStyle = HoldingStyle.SWING
    rank: DecisionRank = DecisionRank.ACCEPTABLE
    confidence: float = 0.0
    probability: float = 0.0
    trade_score: float = 0.0
    institutional_grade: bool = False
    evidence: Evidence | None = None
    explanation: DecisionExplanation | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    """Structured explanation for the trade decision.

    Attributes:
        decision_summary: Summary of the final decision.
        supporting_intelligence: Key intelligence supporting the decision.
        risk_summary: Key risk factors influencing the decision.
        why_this_trade: Rationale for selecting this trade.
        why_alternatives_rejected: Rationale for rejecting alternatives.
        execution_guidance: Guidance for executing the trade.
    """

    decision_summary: str = ""
    supporting_intelligence: str = ""
    risk_summary: str = ""
    why_this_trade: str = ""
    why_alternatives_rejected: str = ""
    execution_guidance: str = ""
