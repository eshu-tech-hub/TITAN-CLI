from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from titan.core.evidence import Evidence, EvidenceSignal


class AnalysisSignal(str, Enum):
    """Directional signal emitted by option analytics."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class MarketBias(str, Enum):
    """Open-interest market bias interpretation."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class LiquidityQuality(str, Enum):
    """Execution-quality classification for liquidity components."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


class LiquidityRisk(str, Enum):
    """Execution-risk classification for liquidity analysis."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


class ExecutionGrade(str, Enum):
    """Institutional execution-quality grade."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class OptionLiquiditySnapshot:
    """Broker-independent liquidity snapshot for one option contract.

    Missing values are represented as ``None`` and treated as unavailable
    evidence rather than zero liquidity.
    """

    bid_price: float | None = None
    ask_price: float | None = None
    bid_quantity: int | None = None
    ask_quantity: int | None = None
    last_traded_price: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SpreadAnalysis:
    """Bid/ask spread analysis for one option contract."""

    spread: float | None
    spread_percent: float | None
    score: float
    confidence: float
    quality: LiquidityQuality
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DepthAnalysis:
    """Displayed top-of-book depth analysis for one option contract."""

    bid_size: int | None
    ask_size: int | None
    order_book_balance: float | None
    depth_score: float
    confidence: float
    quality: LiquidityQuality
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SlippageAnalysis:
    """Expected slippage and liquidity-risk estimate."""

    expected_slippage: float | None
    slippage_score: float
    confidence: float
    liquidity_risk: LiquidityRisk
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutabilityAnalysis:
    """Combined execution-quality score and grade."""

    execution_score: float
    execution_grade: ExecutionGrade
    execution_risk: LiquidityRisk
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LiquidityExplanation:
    """Structured explanation for Liquidity Intelligence."""

    spread: str
    depth: str
    slippage: str
    execution: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class LiquidityAnalysis:
    """Combined Liquidity Intelligence output."""

    spread: float | None
    spread_percent: float | None
    depth_score: float
    slippage_score: float
    execution_score: float
    execution_grade: ExecutionGrade
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: LiquidityExplanation | None = None


@dataclass(frozen=True, slots=True)
class OptionStrikeSnapshot:
    """Broker-independent option-chain row for one strike.

    Attributes:
        strike_price: Strike price for the row.
        call_open_interest: Call-side open interest.
        put_open_interest: Put-side open interest.
        call_volume: Call-side traded volume.
        put_volume: Put-side traded volume.
        call_open_interest_change: Optional call-side OI change.
        put_open_interest_change: Optional put-side OI change.
        call_last_price: Optional call last traded price.
        put_last_price: Optional put last traded price.
        call_delta: Optional call delta supplied by upstream data.
        put_delta: Optional put delta supplied by upstream data.
        call_gamma: Optional call gamma supplied by upstream data.
        put_gamma: Optional put gamma supplied by upstream data.
        call_theta: Optional call theta supplied by upstream data.
        put_theta: Optional put theta supplied by upstream data.
        call_vega: Optional call vega supplied by upstream data.
        put_vega: Optional put vega supplied by upstream data.
        call_rho: Optional call rho supplied by upstream data.
        put_rho: Optional put rho supplied by upstream data.
        call_implied_volatility: Optional call implied volatility.
        put_implied_volatility: Optional put implied volatility.
    """

    strike_price: float
    call_open_interest: int = 0
    put_open_interest: int = 0
    call_volume: int = 0
    put_volume: int = 0
    call_open_interest_change: int | None = None
    put_open_interest_change: int | None = None
    call_last_price: float | None = None
    put_last_price: float | None = None
    call_delta: float | None = None
    put_delta: float | None = None
    call_gamma: float | None = None
    put_gamma: float | None = None
    call_theta: float | None = None
    put_theta: float | None = None
    call_vega: float | None = None
    put_vega: float | None = None
    call_rho: float | None = None
    put_rho: float | None = None
    call_implied_volatility: float | None = None
    put_implied_volatility: float | None = None
    call_vanna: float | None = None
    put_vanna: float | None = None
    call_charm: float | None = None
    put_charm: float | None = None


@dataclass(frozen=True, slots=True)
class OptionChainSnapshot:
    """Broker-independent option-chain snapshot.

    Attributes:
        underlying: Underlying instrument symbol.
        expiry: Option contract expiry timestamp.
        timestamp: Snapshot observation timestamp.
        strikes: Ordered option strike rows.
    """

    underlying: str
    expiry: datetime
    timestamp: datetime
    strikes: tuple[OptionStrikeSnapshot, ...] = field(default_factory=tuple)
    underlying_price: float | None = None


@dataclass(frozen=True, slots=True)
class GreeksExplanation:
    """Structured explanation for Greeks intelligence."""

    delta: str
    gamma: str
    theta: str
    vega: str
    overall: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GreeksAnalysis:
    """Combined Greeks intelligence output."""

    net_delta: float | None
    net_gamma: float | None
    net_theta: float | None
    net_vega: float | None
    average_delta: float | None
    average_gamma: float | None
    average_theta: float | None
    average_vega: float | None
    overall_bias: MarketBias
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: GreeksExplanation | None = None


@dataclass(frozen=True, slots=True)
class OptionChainExplanation:
    """Structured explanation for combined option-chain intelligence."""

    summary: str
    key_points: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class OptionChainAnalysis:
    """Combined option-chain intelligence output.

    The model is intentionally descriptive. It communicates market structure
    signals without prescribing entries, exits, or position sizing.
    """

    overall_bias: MarketBias
    confidence: float
    support: float | None
    resistance: float | None
    pcr: float | None
    highest_put_strike: float | None
    highest_call_strike: float | None
    bullish_score: float
    bearish_score: float
    neutral_score: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    explanation: OptionChainExplanation = field(
        default_factory=lambda: OptionChainExplanation(
            summary="No explanation generated."
        )
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Standard result returned by every option analyzer.

    Attributes:
        score: Normalized analyzer score.
        confidence: Confidence in the analyzer output.
        bullish: Whether the result indicates bullish conditions.
        bearish: Whether the result indicates bearish conditions.
        neutral: Whether the result is neutral.
        reasons: Human-readable reasons for the result.
        warnings: Non-fatal warnings generated during analysis.
        metadata: Additional immutable analyzer context.
    """

    score: float
    confidence: float
    bullish: bool
    bearish: bool
    neutral: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def neutral_placeholder(cls, analyzer_name: str) -> "AnalysisResult":  # type: ignore[misc]
        """Build a neutral placeholder result for milestone foundations.

        Args:
            analyzer_name: Name of the analyzer returning the placeholder.

        Returns:
            A neutral analysis result.
        """

        return cls(
            score=0.0,
            confidence=0.0,
            bullish=False,
            bearish=False,
            neutral=True,
            reasons=(f"{analyzer_name} placeholder analysis executed.",),
            warnings=("Production formula is not implemented yet.",),
            metadata={"analyzer": analyzer_name, "signal": AnalysisSignal.NEUTRAL},
        )


class VolatilityRegime(str, Enum):
    """Volatility regime classification for the broader market context."""

    EXPANSION = "expansion"
    COMPRESSION = "compression"
    STABLE = "stable"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class IVLevel(str, Enum):
    """Implied volatility level classification."""

    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class IVRankLevel(str, Enum):
    """IV rank percentile classification."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    NEUTRAL = "neutral"
    LOW = "low"
    VERY_LOW = "very_low"
    UNKNOWN = "unknown"


class IVHVRelation(str, Enum):
    """Relationship between implied and historical volatility."""

    IV_PREMIUM = "iv_premium"
    IV_DISCOUNT = "iv_discount"
    MISPRICING = "mispricing"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class HVTrend(str, Enum):
    """Historical volatility directional trend."""

    RISING = "rising"
    FALLING = "falling"
    FLAT = "flat"
    UNKNOWN = "unknown"


class HVStability(str, Enum):
    """Historical volatility stability classification."""

    STABLE = "stable"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


class IVTrend(str, Enum):
    """Implied volatility directional trend."""

    RISING = "rising"
    FALLING = "falling"
    FLAT = "flat"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VolatilitySnapshot:
    """Broker-independent volatility data snapshot.

    All values are optional. Missing data must never crash analysis.
    The historical and implied volatility tuples support trend detection
    when multiple observations are available.

    Attributes:
        implied_volatility: Current at-the-money implied volatility.
        historical_volatility: Current historical/realized volatility.
        realized_volatility: Alternative realized volatility measure.
        implied_volatilities: Recent IV observations for trend detection.
        historical_volatilities: Recent HV observations for trend/stability.
        iv_rank: IV rank (0-100).
        iv_percentile: IV percentile (0-100).
        volatility_index: External volatility index value (e.g. VIX).
        underlying_price: Current underlying price for context.
        metadata: Additional volatility context.
    """

    implied_volatility: float | None = None
    historical_volatility: float | None = None
    realized_volatility: float | None = None
    implied_volatilities: tuple[float, ...] = field(default_factory=tuple)
    historical_volatilities: tuple[float, ...] = field(default_factory=tuple)
    iv_rank: float | None = None
    iv_percentile: float | None = None
    volatility_index: float | None = None
    underlying_price: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VolatilityExplanation:
    """Structured explanation for Volatility Intelligence."""

    current_volatility: str
    historical_comparison: str
    iv_vs_hv: str
    regime: str
    risk: str
    institutional_interpretation: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VolatilityAnalysis:
    """Combined Volatility Intelligence output.

    This model communicates institutional-grade volatility analysis
    without prescribing entries, exits, or position sizing.
    """

    current_iv: float | None
    current_hv: float | None
    iv_rank: float | None
    iv_percentile: float | None
    iv_vs_hv: IVHVRelation
    volatility_regime: VolatilityRegime
    iv_level: IVLevel
    iv_rank_level: IVRankLevel
    iv_trend: IVTrend
    hv_trend: HVTrend
    hv_stability: HVStability
    buying_bias: bool
    selling_bias: bool
    overall_bias: MarketBias
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: VolatilityExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "VolatilityAnalysis":
        """Build a neutral placeholder for missing volatility data."""

        return cls(
            current_iv=None,
            current_hv=None,
            iv_rank=None,
            iv_percentile=None,
            iv_vs_hv=IVHVRelation.UNKNOWN,
            volatility_regime=VolatilityRegime.UNKNOWN,
            iv_level=IVLevel.UNKNOWN,
            iv_rank_level=IVRankLevel.UNKNOWN,
            iv_trend=IVTrend.UNKNOWN,
            hv_trend=HVTrend.UNKNOWN,
            hv_stability=HVStability.UNKNOWN,
            buying_bias=False,
            selling_bias=False,
            overall_bias=MarketBias.UNKNOWN,
            confidence=0.0,
            warnings=("Volatility data unavailable.",),
        )


class SmileShape(str, Enum):
    """Volatility smile curvature classification.

    Describes the degree of convexity in the implied volatility smile.
    """

    FLAT = "flat"
    MILD = "mild"
    NORMAL = "normal"
    STRONG = "strong"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


class SmileSymmetry(str, Enum):
    """Volatility smile symmetry classification.

    Describes whether the smile is balanced or biased toward one side.
    """

    SYMMETRIC = "symmetric"
    LEFT_BIASED = "left_biased"
    RIGHT_BIASED = "right_biased"
    UNKNOWN = "unknown"


class SmileRegime(str, Enum):
    """Volatility smile regime classification.

    Captures the overall market regime implied by the smile shape.
    """

    PUT_SKEW = "put_skew"
    CALL_SKEW = "call_skew"
    NORMAL_CONVEXITY = "normal_convexity"
    FLAT = "flat"
    INVERTED = "inverted"
    UNKNOWN = "unknown"


class SmileQuality(str, Enum):
    """Volatility smile data reliability classification."""

    RELIABLE = "reliable"
    PARTIAL = "partial"
    UNRELIABLE = "unreliable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SmileExplanation:
    """Structured explanation for Volatility Smile Intelligence."""

    overview: str
    curvature_assessment: str
    symmetry_assessment: str
    quality_assessment: str
    institutional_interpretation: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SmileAnalysis:
    """Combined Volatility Smile Intelligence output.

    Communicates institutional-grade smile analysis without prescribing
    entries, exits, or position sizing.
    """

    atm_strike: float | None
    atm_iv: float | None
    smile_shape: SmileShape
    smile_symmetry: SmileSymmetry
    smile_regime: SmileRegime
    smile_quality: SmileQuality
    curvature: float | None
    left_wing_iv: float | None
    right_wing_iv: float | None
    strike_count: int
    iv_completeness: float
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: SmileExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "SmileAnalysis":
        """Build a neutral placeholder for missing smile data."""

        return cls(
            atm_strike=None,
            atm_iv=None,
            smile_shape=SmileShape.UNKNOWN,
            smile_symmetry=SmileSymmetry.UNKNOWN,
            smile_regime=SmileRegime.UNKNOWN,
            smile_quality=SmileQuality.UNKNOWN,
            curvature=None,
            left_wing_iv=None,
            right_wing_iv=None,
            strike_count=0,
            iv_completeness=0.0,
            confidence=0.0,
            warnings=("Smile data unavailable.",),
        )


class SkewDirection(str, Enum):
    """Volatility skew direction classification.

    Describes whether the implied volatility skew is biased toward
    put options (left), call options (right), or is symmetric.
    """

    LEFT = "left"
    RIGHT = "right"
    SYMMETRIC = "symmetric"
    UNKNOWN = "unknown"


class SkewStrength(str, Enum):
    """Volatility skew strength classification.

    Describes the magnitude of the skew regardless of direction.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RiskReversalResult:
    """Risk reversal analysis for implied volatility skew.

    Measures the difference between put and call implied volatilities
    at comparable delta or moneyness levels.
    """

    twenty_five_delta_rr: float | None = None
    twenty_five_delta_put_iv: float | None = None
    twenty_five_delta_call_iv: float | None = None
    twenty_five_delta_put_strike: float | None = None
    twenty_five_delta_call_strike: float | None = None
    general_rr: float | None = None
    avg_otm_put_iv: float | None = None
    avg_otm_call_iv: float | None = None
    bias: MarketBias = MarketBias.UNKNOWN
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ButterflyResult:
    """Butterfly analysis for implied volatility skew.

    Examines the curvature and relative pricing of ATM vs wing strikes.
    """

    atm_richness: float | None = None
    wing_richness: float | None = None
    relative_curvature: float | None = None
    atm_iv: float | None = None
    near_wing_iv: float | None = None
    far_wing_iv: float | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkewExplanation:
    """Structured explanation for Volatility Skew Intelligence."""

    skew_direction: str = ""
    risk_reversal: str = ""
    butterfly: str = ""
    institutional_interpretation: str = ""
    risk_assessment: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SkewAnalysis:
    """Combined Volatility Skew Intelligence output.

    Communicates institutional-grade skew analysis without prescribing
    entries, exits, or position sizing.
    """

    direction: SkewDirection
    strength: SkewStrength
    risk_reversal: RiskReversalResult | None
    butterfly: ButterflyResult | None
    overall_bias: MarketBias
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: SkewExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "SkewAnalysis":
        """Build a neutral placeholder for missing skew data."""

        return cls(
            direction=SkewDirection.UNKNOWN,
            strength=SkewStrength.UNKNOWN,
            risk_reversal=None,
            butterfly=None,
            overall_bias=MarketBias.UNKNOWN,
            confidence=0.0,
            warnings=("Skew data unavailable.",),
        )


class TermStructureShape(str, Enum):
    """Volatility term structure shape classification.

    Describes the overall shape of the implied volatility curve
    across expiries.
    """

    NORMAL = "normal"
    CONTANGO = "contango"
    BACKWARDATION = "backwardation"
    FLAT = "flat"
    INVERTED = "inverted"
    UNKNOWN = "unknown"


class TermStructureStrength(str, Enum):
    """Volatility term structure slope strength classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TermStructureExpiry:
    """Single expiry data point for term structure analysis.

    Attributes:
        expiry: Option contract expiry date.
        atm_iv: At-the-money implied volatility for this expiry.
        average_iv: Average implied volatility across strikes.
        metadata: Optional smile/skew context for this expiry.
    """

    expiry: datetime
    atm_iv: float | None = None
    average_iv: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TermStructureSnapshot:
    """Broker-independent collection of expiry data for term structure.

    Attributes:
        underlying: Underlying instrument symbol.
        timestamp: Snapshot observation timestamp.
        expiries: Chronologically sorted expiry data points.
    """

    underlying: str
    timestamp: datetime
    expiries: tuple[TermStructureExpiry, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CalendarResult:
    """Calendar spread analysis for volatility term structure."""

    front_iv: float | None = None
    back_iv: float | None = None
    calendar_spread: float | None = None
    event_premium: float | None = None
    curve_slope: float | None = None
    average_slope: float | None = None
    max_discontinuity: float | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContangoResult:
    """Contango analysis for volatility term structure."""

    is_contango: bool = False
    strength: TermStructureStrength = TermStructureStrength.UNKNOWN
    interpretation: str = ""
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class BackwardationResult:
    """Backwardation analysis for volatility term structure."""

    is_backwardation: bool = False
    strength: TermStructureStrength = TermStructureStrength.UNKNOWN
    interpretation: str = ""
    confidence: float = 0.0
    stress_indicator: bool = False


@dataclass(frozen=True, slots=True)
class TermStructureExplanation:
    """Structured explanation for Volatility Term Structure Intelligence."""

    curve_shape: str = ""
    calendar_analysis: str = ""
    slope_interpretation: str = ""
    institutional_view: str = ""
    risk_assessment: str = ""
    future_considerations: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TermStructureAnalysis:
    """Combined Volatility Term Structure Intelligence output.

    Communicates institutional-grade term structure analysis without
    prescribing entries, exits, or position sizing.
    """

    shape: TermStructureShape
    strength: TermStructureStrength
    front_iv: float | None
    back_iv: float | None
    curve_slope: float | None
    event_premium: float | None
    calendar_bias: MarketBias
    overall_bias: MarketBias
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: TermStructureExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "TermStructureAnalysis":
        """Build a neutral placeholder for missing term structure data."""

        return cls(
            shape=TermStructureShape.UNKNOWN,
            strength=TermStructureStrength.UNKNOWN,
            front_iv=None,
            back_iv=None,
            curve_slope=None,
            event_premium=None,
            calendar_bias=MarketBias.UNKNOWN,
            overall_bias=MarketBias.UNKNOWN,
            confidence=0.0,
            warnings=("Term structure data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Volatility Surface Intelligence (M2.2.4)
# ---------------------------------------------------------------------------


class SurfaceHealthLevel(str, Enum):
    """Overall volatility surface health classification."""

    HEALTHY = "healthy"
    GOOD = "good"
    CAUTION = "caution"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SurfaceConsistencyLevel(str, Enum):
    """Cross-module signal consistency classification."""

    CONSISTENT = "consistent"
    PARTIALLY_CONSISTENT = "partially_consistent"
    INCONSISTENT = "inconsistent"
    UNKNOWN = "unknown"


class SurfaceAnomalyType(str, Enum):
    """Types of surface anomalies detected by the intelligence engine."""

    EXTREME_SMILE = "extreme_smile"
    EXTREME_SKEW = "extreme_skew"
    BROKEN_TERM_STRUCTURE = "broken_term_structure"
    CONFLICTING_SIGNALS = "conflicting_signals"
    MISSING_INTELLIGENCE = "missing_intelligence"
    LOW_CONFIDENCE = "low_confidence"


@dataclass(frozen=True, slots=True)
class SurfaceAnomaly:
    """A single surface anomaly.

    Attributes:
        type: The type of anomaly detected.
        source: Component name where the anomaly was found.
        description: Human-readable description of the anomaly.
    """

    type: SurfaceAnomalyType
    source: str
    description: str


@dataclass(frozen=True, slots=True)
class SurfaceHealth:
    """Surface health assessment result.

    Attributes:
        level: Health classification level.
        reason: Human-readable reason for the health level.
        component_status: Per-component availability and quality.
    """

    level: SurfaceHealthLevel
    reason: str
    component_status: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SurfaceConsistency:
    """Surface cross-module consistency assessment.

    Attributes:
        level: Consistency classification.
        details: Human-readable explanation of consistency verdict.
        conflicts: Specific conflict descriptions.
    """

    level: SurfaceConsistencyLevel
    details: str
    conflicts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SurfaceAnomalyResult:
    """Surface anomaly detection result.

    Attributes:
        anomalies: List of detected anomalies (empty if none).
        anomaly_count: Number of anomalies detected.
    """

    anomalies: tuple[SurfaceAnomaly, ...] = field(default_factory=tuple)
    anomaly_count: int = 0


@dataclass(frozen=True, slots=True)
class VolatilitySurfaceInput:
    """Aggregated input for the Volatility Surface Intelligence Engine.

    All fields are optional — missing components degrade gracefully.

    Attributes:
        volatility: Volatility analysis output (VolatilityAnalyzer).
        smile: Smile analysis output (SmileAnalyzer).
        skew: Skew analysis output (SkewAnalyzer).
        term_structure: Term structure analysis output (TermStructureAnalyzer).
    """

    volatility: VolatilityAnalysis | None = None
    smile: SmileAnalysis | None = None
    skew: SkewAnalysis | None = None
    term_structure: TermStructureAnalysis | None = None


@dataclass(frozen=True, slots=True)
class SurfaceComponentScore:
    """Component-level score breakdown for the surface analysis.

    Attributes:
        name: Component name (e.g., "Volatility", "Smile").
        score: Component evidence score (0-100).
        confidence: Component evidence confidence (0-1).
        signal: Component evidence signal, if available.
        available: Whether the component was present.
    """

    name: str
    score: float
    confidence: float
    signal: EvidenceSignal | None
    available: bool


@dataclass(frozen=True, slots=True)
class SurfaceExplanation:
    """Structured explanation for Volatility Surface Intelligence.

    Attributes:
        overall_surface: Summary of the surface assessment.
        health: Health assessment explanation.
        consistency: Consistency assessment explanation.
        anomalies: Anomaly descriptions (if any).
        institutional_interpretation: Market context interpretation.
        risk_assessment: Risk management guidance.
    """

    overall_surface: str = ""
    health: str = ""
    consistency: str = ""
    anomalies: str = ""
    institutional_interpretation: str = ""
    risk_assessment: str = ""


@dataclass(frozen=True, slots=True)
class SurfaceIntelligenceAnalysis:
    """Combined Volatility Surface Intelligence output.

    Communicates institutional-grade surface analysis by evaluating
    health, consistency, anomalies, and cross-module agreement across
    all volatility intelligence components.

    Attributes:
        health: Overall surface health assessment.
        consistency: Cross-module consistency assessment.
        overall_bias: Derived overall market bias.
        institutional_confidence: Aggregate confidence in the surface view (0-1).
        component_scores: Per-component score breakdowns.
        anomalies: Detected surface anomalies.
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    health: SurfaceHealthLevel
    consistency: SurfaceConsistencyLevel
    overall_bias: MarketBias
    institutional_confidence: float
    component_scores: tuple[SurfaceComponentScore, ...] = field(default_factory=tuple)
    anomalies: tuple[SurfaceAnomaly, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: SurfaceExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "SurfaceIntelligenceAnalysis":
        """Build a neutral placeholder for missing surface data."""

        return cls(
            health=SurfaceHealthLevel.UNKNOWN,
            consistency=SurfaceConsistencyLevel.UNKNOWN,
            overall_bias=MarketBias.UNKNOWN,
            institutional_confidence=0.0,
            warnings=("Volatility surface data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Dealer Positioning Intelligence (M2.2.5)
# ---------------------------------------------------------------------------


class DealerSide(str, Enum):
    """Dealer gamma positioning classification.

    Indicates whether dealers are net long gamma (benefit from large
    moves, dampen price action) or net short gamma (lose on large moves,
    amplify price action).
    """

    LONG_GAMMA = "long_gamma"
    SHORT_GAMMA = "short_gamma"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class DealerBiasLevel(str, Enum):
    """Dealer directional bias classification.

    Reflects the institutional positioning signal inferred from option
    analytics — what dealer hedging pressure implies for price direction.
    """

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DealerInventory:
    """Dealer inventory bias assessment.

    Attributes:
        dealer_side: Estimated gamma positioning of dealers.
        inventory_score: Numerical score (-100 to 100) where negative
            indicates short gamma and positive indicates long gamma.
        confidence: Confidence in the inventory estimate (0-1).
        reasons: Human-readable reasons for the estimation.
        warnings: Non-fatal warnings from the analysis.
    """

    dealer_side: DealerSide
    inventory_score: float
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DealerBias:
    """Dealer directional bias assessment.

    Attributes:
        bias_level: Directional bias inferred from dealer positioning.
        bias_score: Numerical score (-100 to 100) where negative
            indicates bearish and positive indicates bullish.
        confidence: Confidence in the bias estimate (0-1).
        reasons: Human-readable reasons for the estimation.
        warnings: Non-fatal warnings from the analysis.
    """

    bias_level: DealerBiasLevel
    bias_score: float
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DealerPositioningInput:
    """Aggregated input for the Dealer Positioning Intelligence Engine.

    All fields are optional — missing components degrade gracefully.

    Attributes:
        option_chain: Combined option-chain intelligence output.
        greeks: Combined Greeks intelligence output.
        liquidity: Combined Liquidity Intelligence output.
        surface: Combined Volatility Surface Intelligence output.
    """

    option_chain: OptionChainAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    liquidity: LiquidityAnalysis | None = None
    surface: SurfaceIntelligenceAnalysis | None = None


@dataclass(frozen=True, slots=True)
class DealerPositioningExplanation:
    """Structured explanation for Dealer Positioning Intelligence.

    Attributes:
        dealer_inventory: Gamma positioning explanation.
        dealer_bias: Directional bias explanation.
        hedging_pressure: Likely hedging intensity explanation.
        institutional_interpretation: Market context interpretation.
        risk_assessment: Risk management guidance.
    """

    dealer_inventory: str = ""
    dealer_bias: str = ""
    hedging_pressure: str = ""
    institutional_interpretation: str = ""
    risk_assessment: str = ""


@dataclass(frozen=True, slots=True)
class DealerPositioningAnalysis:
    """Combined Dealer Positioning Intelligence output.

    Communicates institutional-grade dealer positioning analysis without
    prescribing entries, exits, or position sizing.

    Attributes:
        dealer_side: Estimated dealer gamma positioning.
        dealer_bias: Estimated dealer directional bias.
        hedging_pressure: Likely hedging intensity (0-1).
        confidence: Aggregate confidence in the dealer view (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    dealer_side: DealerSide
    dealer_bias: DealerBiasLevel
    hedging_pressure: float
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: DealerPositioningExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "DealerPositioningAnalysis":
        """Build a neutral placeholder for missing dealer data."""

        return cls(
            dealer_side=DealerSide.UNKNOWN,
            dealer_bias=DealerBiasLevel.UNKNOWN,
            hedging_pressure=0.0,
            confidence=0.0,
            warnings=("Dealer positioning data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Gamma Exposure Intelligence (M2.2.6)
# ---------------------------------------------------------------------------


class GammaRegime(str, Enum):
    """Net gamma exposure regime classification.

    Indicates whether the aggregate gamma exposure is positive (dealers
    net long gamma), negative (dealers net short gamma), neutral, or
    unknown.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class WallType(str, Enum):
    """Gamma wall classification.

    Identifies whether a significant gamma concentration acts as a
    call wall (resistance) or put wall (support).
    """

    CALL_WALL = "call_wall"
    PUT_WALL = "put_wall"
    NONE = "none"
    UNKNOWN = "unknown"


class PinningProbability(str, Enum):
    """Probability that price will pin near a gamma level.

    When dealers are long gamma, hedging activity tends to pin price
    near the zero-gamma level or between walls.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ZeroGammaLevel:
    """Estimated price level where net gamma exposure crosses zero.

    Attributes:
        strike: The interpolated price level of the gamma flip.
        underlying_price: Current underlying price for context.
        distance_percent: Distance from underlying to zero gamma as
            a percentage of underlying price.
        confidence: Confidence in the zero-gamma estimate (0-1).
    """

    strike: float | None
    underlying_price: float | None = None
    distance_percent: float | None = None
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class GammaWall:
    """A significant gamma concentration level identified as a wall.

    Attributes:
        strike: The strike price of the gamma wall.
        wall_type: Classification of the wall (call, put, none, unknown).
        gamma_concentration: Gamma exposure magnitude at this strike
            (normalised 0-1 relative to max across strikes).
        open_interest: Total open interest at this strike.
        confidence: Confidence in the wall identification (0-1).
    """

    strike: float | None
    wall_type: WallType
    gamma_concentration: float | None = None
    open_interest: int = 0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class GammaExposureInput:
    """Aggregated input for the Gamma Exposure Intelligence Engine.

    All fields are optional — missing components degrade gracefully.

    Attributes:
        dealer_positioning: Dealer positioning analysis output.
        greeks: Combined Greeks intelligence output.
        option_chain: Combined option-chain intelligence output.
        surface: Combined volatility surface intelligence output.
        option_chain_snapshot: Raw option-chain snapshot with per-strike
            gamma and open interest data.
    """

    dealer_positioning: DealerPositioningAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    option_chain: OptionChainAnalysis | None = None
    surface: SurfaceIntelligenceAnalysis | None = None
    option_chain_snapshot: OptionChainSnapshot | None = None


@dataclass(frozen=True, slots=True)
class GammaExposureExplanation:
    """Structured explanation for Gamma Exposure Intelligence.

    Attributes:
        gamma_regime: Explanation of the current gamma regime.
        zero_gamma: Explanation of the zero-gamma level.
        gamma_walls: Explanation of identified gamma walls.
        pinning_risk: Assessment of pinning probability.
        volatility_implications: Volatility expansion or contraction
            implications.
        institutional_interpretation: Market context interpretation.
    """

    gamma_regime: str = ""
    zero_gamma: str = ""
    gamma_walls: str = ""
    pinning_risk: str = ""
    volatility_implications: str = ""
    institutional_interpretation: str = ""


@dataclass(frozen=True, slots=True)
class GammaExposureAnalysis:
    """Combined Gamma Exposure Intelligence output.

    Communicates institutional-grade gamma exposure analysis without
    prescribing entries, exits, or position sizing.

    Attributes:
        net_gamma_exposure: Estimated net gamma exposure in dollar
            gamma per 1% move (if calculable) or raw net gamma.
        gamma_regime: Classification of the net gamma regime.
        zero_gamma_level: Estimated price level of the gamma flip.
        call_wall: Identified call wall (resistance).
        put_wall: Identified put wall (support).
        pinning_probability: Likelihood of price pinning near gamma
            levels.
        volatility_expansion_probability: Likelihood of volatility
            expansion (0-1).
        confidence: Aggregate confidence in the gamma view (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    net_gamma_exposure: float | None
    gamma_regime: GammaRegime
    zero_gamma_level: ZeroGammaLevel | None
    call_wall: GammaWall | None
    put_wall: GammaWall | None
    pinning_probability: PinningProbability
    volatility_expansion_probability: float
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: GammaExposureExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "GammaExposureAnalysis":
        """Build a neutral placeholder for missing gamma exposure data."""

        return cls(
            net_gamma_exposure=None,
            gamma_regime=GammaRegime.UNKNOWN,
            zero_gamma_level=None,
            call_wall=None,
            put_wall=None,
            pinning_probability=PinningProbability.UNKNOWN,
            volatility_expansion_probability=0.0,
            confidence=0.0,
            warnings=("Gamma exposure data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Vanna Exposure Intelligence (M2.2.7)
# ---------------------------------------------------------------------------


class VannaRegimeType(str, Enum):
    """Net vanna exposure regime classification.

    Indicates whether the aggregate vanna exposure is positive (dealers
    gain when IV rises), negative (dealers gain when IV falls), balanced,
    or unknown.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BALANCED = "balanced"
    UNKNOWN = "unknown"


class VannaPressureLevel(str, Enum):
    """Vanna-driven dealer hedging pressure classification.

    Describes the intensity of expected dealer hedging response to
    changes in implied volatility and/or underlying price.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VannaRegime:
    """Net vanna regime assessment.

    Attributes:
        regime_type: Classification of the net vanna regime.
        net_vanna: Estimated net vanna exposure (aggregate).
        confidence: Confidence in the regime estimate (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    regime_type: VannaRegimeType
    net_vanna: float | None
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VannaPressure:
    """Vanna-driven dealer hedging pressure assessment.

    Attributes:
        pressure_level: Overall pressure classification.
        dealer_response: Description of expected dealer response.
        iv_sensitivity: Dealer sensitivity to IV changes (0-1).
        price_sensitivity: Dealer sensitivity to price changes (0-1).
        confidence: Confidence in the pressure estimate (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    pressure_level: VannaPressureLevel
    dealer_response: str
    iv_sensitivity: float
    price_sensitivity: float
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VannaExplanation:
    """Structured explanation for Vanna Exposure Intelligence.

    Attributes:
        overall_vanna: Summary of vanna exposure.
        dealer_sensitivity: Explanation of dealer sensitivity.
        iv_impact: Impact of IV changes on dealer hedging.
        price_impact: Impact of price changes on dealer hedging.
        institutional_interpretation: Market context interpretation.
        risk_assessment: Risk management guidance.
    """

    overall_vanna: str = ""
    dealer_sensitivity: str = ""
    iv_impact: str = ""
    price_impact: str = ""
    institutional_interpretation: str = ""
    risk_assessment: str = ""


@dataclass(frozen=True, slots=True)
class VannaExposureInput:
    """Aggregated input for the Vanna Exposure Intelligence Engine.

    All fields are optional — missing components degrade gracefully.

    Attributes:
        dealer_positioning: Dealer positioning analysis output.
        gamma_exposure: Gamma exposure analysis output.
        greeks: Combined Greeks intelligence output.
        surface: Combined volatility surface intelligence output.
        option_chain: Combined option-chain intelligence output.
        option_chain_snapshot: Raw option-chain snapshot with per-strike
            vanna, gamma, and open interest data.
    """

    dealer_positioning: DealerPositioningAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    surface: SurfaceIntelligenceAnalysis | None = None
    option_chain: OptionChainAnalysis | None = None
    option_chain_snapshot: OptionChainSnapshot | None = None


@dataclass(frozen=True, slots=True)
class VannaExposureAnalysis:
    """Combined Vanna Exposure Intelligence output.

    Communicates institutional-grade vanna exposure analysis without
    prescribing entries, exits, or position sizing.

    Attributes:
        net_vanna: Estimated net vanna exposure.
        regime: Net vanna regime assessment.
        pressure: Vanna-driven dealer hedging pressure.
        confidence: Aggregate confidence in the vanna view (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    net_vanna: float | None
    regime: VannaRegime
    pressure: VannaPressure
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: VannaExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "VannaExposureAnalysis":
        """Build a neutral placeholder for missing vanna data."""

        return cls(
            net_vanna=None,
            regime=VannaRegime(
                regime_type=VannaRegimeType.UNKNOWN,
                net_vanna=None,
                confidence=0.0,
                reasons=("Vanna data unavailable.",),
            ),
            pressure=VannaPressure(
                pressure_level=VannaPressureLevel.UNKNOWN,
                dealer_response="Vanna pressure cannot be assessed.",
                iv_sensitivity=0.0,
                price_sensitivity=0.0,
                confidence=0.0,
                reasons=("Vanna data unavailable.",),
            ),
            confidence=0.0,
            warnings=("Vanna exposure data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Charm Exposure Intelligence (M2.2.8)
# ---------------------------------------------------------------------------


class CharmRegimeType(str, Enum):
    """Net charm exposure regime classification.

    Indicates whether the aggregate charm exposure is positive (dealer
    delta increases with time), negative (dealer delta decays with time),
    balanced, or unknown.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BALANCED = "balanced"
    UNKNOWN = "unknown"


class CharmPressureLevel(str, Enum):
    """Charm-driven dealer hedging pressure classification.

    Describes the intensity of expected dealer delta rebalancing as
    time passes and options approach expiry.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CharmRegime:
    """Net charm regime assessment.

    Attributes:
        regime_type: Classification of the net charm regime.
        net_charm: Estimated net charm exposure (aggregate).
        confidence: Confidence in the regime estimate (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    regime_type: CharmRegimeType
    net_charm: float | None
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CharmPressure:
    """Charm-driven dealer hedging pressure assessment.

    Attributes:
        pressure_level: Overall pressure classification.
        dealer_response: Description of expected dealer response.
        time_sensitivity: Dealer sensitivity to time decay (0-1).
        near_expiry_risk: Whether near-expiry charm risk is elevated.
        confidence: Confidence in the pressure estimate (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    pressure_level: CharmPressureLevel
    dealer_response: str
    time_sensitivity: float
    near_expiry_risk: bool
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CharmExplanation:
    """Structured explanation for Charm Exposure Intelligence.

    Attributes:
        overall_charm: Summary of charm exposure.
        dealer_delta_decay: Explanation of dealer delta decay.
        time_decay_impact: Impact of time decay on dealer hedging.
        near_expiry_risk: Assessment of near-expiry charm risk.
        institutional_interpretation: Market context interpretation.
        risk_assessment: Risk management guidance.
    """

    overall_charm: str = ""
    dealer_delta_decay: str = ""
    time_decay_impact: str = ""
    near_expiry_risk: str = ""
    institutional_interpretation: str = ""
    risk_assessment: str = ""


@dataclass(frozen=True, slots=True)
class CharmExposureInput:
    """Aggregated input for the Charm Exposure Intelligence Engine.

    All fields are optional — missing components degrade gracefully.

    Attributes:
        dealer_positioning: Dealer positioning analysis output.
        gamma_exposure: Gamma exposure analysis output.
        vanna_exposure: Vanna exposure analysis output.
        greeks: Combined Greeks intelligence output.
        surface: Combined volatility surface intelligence output.
        option_chain: Combined option-chain intelligence output.
        option_chain_snapshot: Raw option-chain snapshot with per-strike
            charm, gamma, and open interest data.
    """

    dealer_positioning: DealerPositioningAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None
    vanna_exposure: VannaExposureAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    surface: SurfaceIntelligenceAnalysis | None = None
    option_chain: OptionChainAnalysis | None = None
    option_chain_snapshot: OptionChainSnapshot | None = None


@dataclass(frozen=True, slots=True)
class CharmExposureAnalysis:
    """Combined Charm Exposure Intelligence output.

    Communicates institutional-grade charm exposure analysis without
    prescribing entries, exits, or position sizing.

    Attributes:
        net_charm: Estimated net charm exposure.
        regime: Net charm regime assessment.
        pressure: Charm-driven dealer hedging pressure.
        dealer_delta_decay: Magnitude of dealer delta decay (0-1).
        near_expiry_risk: Whether near-expiry charm risk is elevated.
        confidence: Aggregate confidence in the charm view (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    net_charm: float | None
    regime: CharmRegime
    pressure: CharmPressure
    dealer_delta_decay: float
    near_expiry_risk: bool
    confidence: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: CharmExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> "CharmExposureAnalysis":
        """Build a neutral placeholder for missing charm data."""

        return cls(
            net_charm=None,
            regime=CharmRegime(
                regime_type=CharmRegimeType.UNKNOWN,
                net_charm=None,
                confidence=0.0,
                reasons=("Charm data unavailable.",),
            ),
            pressure=CharmPressure(
                pressure_level=CharmPressureLevel.UNKNOWN,
                dealer_response="Charm pressure cannot be assessed.",
                time_sensitivity=0.0,
                near_expiry_risk=False,
                confidence=0.0,
                reasons=("Charm data unavailable.",),
            ),
            dealer_delta_decay=0.0,
            near_expiry_risk=False,
            confidence=0.0,
            warnings=("Charm exposure data unavailable.",),
        )
