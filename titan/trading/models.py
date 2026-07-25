from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

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


class TradeStatus(str, Enum):
    """Final qualification status for a trade opportunity."""

    QUALIFIED = "qualified"
    REJECTED = "rejected"
    WATCHLIST = "watchlist"
    WAIT = "wait"


class ScoreBand(str, Enum):
    """Quality band for the trade score."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    WEAK = "weak"
    REJECT = "reject"


class TradeDirection(str, Enum):
    """Trade direction classification for qualification."""

    LONG = "long"
    SHORT = "short"
    OPTION_BUYING = "option_buying"
    OPTION_SELLING = "option_selling"


class FilterCategory(str, Enum):
    """Classification of hard filters applied during qualification."""

    HIGH_EVENT_RISK = "high_event_risk"
    EXTREME_LIQUIDITY_RISK = "extreme_liquidity_risk"
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_INTELLIGENCE = "conflicting_intelligence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNKNOWN_MARKET_REGIME = "unknown_market_regime"


class ConfirmationSource(str, Enum):
    """Sources of confirmation evaluated during qualification."""

    MARKET = "market"
    OPTIONS = "options"
    DEALER = "dealer"
    VOLATILITY = "volatility"
    NEWS = "news"
    EVENTS = "events"
    EVIDENCE = "evidence"
    FUSION = "fusion"


@dataclass(frozen=True, slots=True)
class TradeScore:
    """Normalised trade opportunity score with quality band.

    Attributes:
        value: Score from 0 to 100.
        band: Quality band classification.
    """

    value: float
    band: ScoreBand

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise ValueError("TradeScore value must be between 0 and 100.")


@dataclass(frozen=True, slots=True)
class FilterResult:
    """Result of evaluating a single hard filter.

    Attributes:
        filter_category: The filter that was evaluated.
        passed: Whether the filter was passed.
        reason: Human-readable explanation for the result.
    """

    filter_category: FilterCategory
    passed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    """Result of confirmation check from a single intelligence source.

    Attributes:
        source: The intelligence source.
        confirmed: Whether the source confirms the trade direction.
        score: Normalised confirmation score (0-100).
        confidence: Confidence in the confirmation (0.0-1.0).
        reason: Human-readable explanation.
    """

    source: ConfirmationSource
    confirmed: bool
    score: float
    confidence: float
    reason: str


@dataclass(frozen=True, slots=True)
class DirectionQualification:
    """Qualification assessment for a specific trade direction.

    Attributes:
        direction: Trade direction assessed.
        qualified: Whether the direction is qualified.
        confirmations: Number of confirmations received.
        total_possible: Maximum possible confirmations.
        score: Direction-specific score (0-100).
        reasons: Human-readable reasons for the assessment.
    """

    direction: TradeDirection
    qualified: bool
    confirmations: int
    total_possible: int
    score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TradeQualificationExplanation:
    """Structured explanation for the trade qualification decision."""

    overall_qualification: str = ""
    confirmations: str = ""
    rejections: str = ""
    risk_factors: str = ""
    institutional_alignment: str = ""
    final_assessment: str = ""


@dataclass(frozen=True, slots=True)
class TradeQualification:
    """Complete trade qualification output.

    Attributes:
        status: Final qualification status.
        trade_score: Normalised trade score with quality band.
        confidence: Overall confidence in the qualification (0.0-1.0).
        decision_context: Summary of the decision context.
        passed_filters: Filters that were passed.
        failed_filters: Filters that were failed.
        confirmations: Per-source confirmation results.
        long_qualification: Whether long trades are qualified.
        short_qualification: Whether short trades are qualified.
        option_buying_qualification: Whether option buying is qualified.
        option_selling_qualification: Whether option selling is qualified.
        institutional_alignment: Whether institutional signals align.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
        warnings: Non-fatal warnings generated during qualification.
        metadata: Producer context.
        timestamp: When the qualification was computed.
    """

    status: TradeStatus
    trade_score: TradeScore
    confidence: float
    decision_context: str
    passed_filters: tuple[str, ...] = field(default_factory=tuple)
    failed_filters: tuple[str, ...] = field(default_factory=tuple)
    confirmations: tuple[ConfirmationResult, ...] = field(default_factory=tuple)
    long_qualification: bool = False
    short_qualification: bool = False
    option_buying_qualification: bool = False
    option_selling_qualification: bool = False
    institutional_alignment: bool = False
    evidence: Evidence | None = None
    explanation: TradeQualificationExplanation | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True, slots=True)
class TradeQualificationInput:
    """Aggregated input for the Trade Qualification Engine.

    All fields are optional — missing components degrade gracefully.

    Attributes:
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
        evidence_aggregator: Evidence Aggregator output.
        intelligence_fusion: Intelligence Fusion output.
    """

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
