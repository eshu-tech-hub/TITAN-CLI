from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from titan.core.evidence import Evidence


class StrategyType(str, Enum):
    """Trading strategy classification for regime context.

    Communicates strategy suitability based on market environment.
    Must NOT be interpreted as a trade recommendation.
    """

    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    RANGE_TRADING = "range_trading"
    VOLATILITY_EXPANSION = "volatility_expansion"
    VOLATILITY_CONTRACTION = "volatility_contraction"
    NO_TRADE = "no_trade"


class MarketRegime(str, Enum):
    """Primary market regime classification."""

    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    COMPRESSION = "compression"
    EXPANSION = "expansion"
    TRANSITION = "transition"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class TrendDirection(str, Enum):
    """Directional classification for market trend."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


class StructureState(str, Enum):
    """Overall market structure state classification."""

    TRENDING = "trending"
    RANGING = "ranging"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class BreakType(str, Enum):
    """Market structure break classification.

    BOS (Break of Structure): price breaks a key swing level within the
        current trend context.
    CHOCH (Change of Character): trend structure flips, indicating a
        potential trend reversal.
    """

    NONE = "none"
    BOS = "bos"
    CHOCH = "choch"


@dataclass(frozen=True, slots=True)
class TrendStructure:
    """Primary and secondary trend assessment.

    Attributes:
        primary: Longer-term trend direction.
        secondary: Shorter-term trend direction.
        strength: Trend strength metric (0-1).
        confidence: Confidence in the trend assessment (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    primary: TrendDirection
    secondary: TrendDirection
    strength: float
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SwingPoint:
    """A single swing high or low identified in price data.

    Attributes:
        index: Candle index in the MarketDataSeries.
        price: Price level of the swing point (high for swing high,
            low for swing low).
        high: Candle high at this index.
        low: Candle low at this index.
        is_swing_high: Whether this point is a swing high.
        is_swing_low: Whether this point is a swing low.
    """

    index: int
    price: float
    high: float
    low: float
    is_swing_high: bool
    is_swing_low: bool


@dataclass(frozen=True, slots=True)
class SwingStructure:
    """Swing point analysis and market structure breaks.

    Attributes:
        swing_highs: Detected swing high points.
        swing_lows: Detected swing low points.
        higher_highs: Sequence of higher highs in uptrend.
        higher_lows: Sequence of higher lows in uptrend.
        lower_highs: Sequence of lower highs in downtrend.
        lower_lows: Sequence of lower lows in downtrend.
        break_type: Most recent structure break type.
        confidence: Confidence in the swing analysis (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    swing_highs: tuple[SwingPoint, ...] = field(default_factory=tuple)
    swing_lows: tuple[SwingPoint, ...] = field(default_factory=tuple)
    higher_highs: tuple[float, ...] = field(default_factory=tuple)
    higher_lows: tuple[float, ...] = field(default_factory=tuple)
    lower_highs: tuple[float, ...] = field(default_factory=tuple)
    lower_lows: tuple[float, ...] = field(default_factory=tuple)
    break_type: BreakType = BreakType.NONE
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SupportResistanceStructure:
    """Support and resistance level identification.

    Attributes:
        support_levels: Identified support price levels, sorted descending.
        resistance_levels: Identified resistance price levels,
            sorted descending.
        confidence: Confidence in the level identification (0-1).
        reasons: Human-readable reasons for the assessment.
    """

    support_levels: tuple[float, ...] = field(default_factory=tuple)
    resistance_levels: tuple[float, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MarketStructureExplanation:
    """Structured explanation for Market Structure Intelligence.

    Attributes:
        trend: Trend assessment explanation.
        swings: Swing point analysis explanation.
        support: Support level explanation.
        resistance: Resistance level explanation.
        structure: Overall market structure explanation.
        institutional_interpretation: Market context interpretation.
    """

    trend: str = ""
    swings: str = ""
    support: str = ""
    resistance: str = ""
    structure: str = ""
    institutional_interpretation: str = ""


@dataclass(frozen=True, slots=True)
class MarketStructureAnalysis:
    """Combined Market Structure Intelligence output.

    Communicates institutional-grade market structure analysis from
    supplied price data without prescribing entries, exits, or
    position sizing.

    Attributes:
        primary_trend: Longer-term trend direction.
        secondary_trend: Shorter-term trend direction.
        structure_state: Overall market structure state.
        support_levels: Identified support price levels.
        resistance_levels: Identified resistance price levels.
        trend_strength: Trend strength metric (0-1).
        confidence: Aggregate confidence in the structure view (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    primary_trend: TrendDirection
    secondary_trend: TrendDirection
    structure_state: StructureState
    support_levels: tuple[float, ...] = field(default_factory=tuple)
    resistance_levels: tuple[float, ...] = field(default_factory=tuple)
    trend_strength: float = 0.0
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: MarketStructureExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> MarketStructureAnalysis:
        return cls(
            primary_trend=TrendDirection.UNKNOWN,
            secondary_trend=TrendDirection.UNKNOWN,
            structure_state=StructureState.UNKNOWN,
            confidence=0.0,
            warnings=("Market structure data unavailable.",),
        )


# ---------------------------------------------------------------------------
# VWAP Intelligence
# ---------------------------------------------------------------------------


class VWAPBias(str, Enum):
    """Institutional bias derived from VWAP position and trend."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class VWAPPosition(str, Enum):
    """Price position relative to VWAP."""

    ABOVE = "above"
    BELOW = "below"
    AT = "at"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VWAPTrend:
    """VWAP trend and price interaction analysis.

    Attributes:
        slope: VWAP slope over the lookback period.
        direction: Trend direction of VWAP itself (bullish=rising, bearish=falling).
        crossover: Whether a VWAP crossover occurred (price crossed VWAP).
        reclaim: Whether price reclaimed VWAP (crossed from below to above).
        rejection: Whether price was rejected at VWAP (touched and reversed).
        pullback: Whether price pulled back to VWAP (returned from a distance).
        confidence: Confidence in the trend assessment (0-1).
        reasons: Human-readable reasons.
    """

    slope: float = 0.0
    direction: TrendDirection = TrendDirection.UNKNOWN
    crossover: bool = False
    reclaim: bool = False
    rejection: bool = False
    pullback: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VWAPBands:
    """VWAP deviation bands for support/resistance context.

    Attributes:
        upper: Upper deviation band price.
        lower: Lower deviation band price.
        deviation: Current standard deviation multiple from VWAP.
        bandwidth: Normalized band width ((upper - lower) / vwap).
        confidence: Confidence in the band assessment (0-1).
        reasons: Human-readable reasons.
    """

    upper: float = 0.0
    lower: float = 0.0
    deviation: float = 0.0
    bandwidth: float = 0.0
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VWAPExplanation:
    """Structured explanation for VWAP Intelligence.

    Attributes:
        vwap: VWAP level explanation.
        institutional_bias: Institutional bias explanation.
        price_position: Price position relative to VWAP.
        vwap_trend: VWAP trend explanation.
        support_resistance: Support/resistance from bands.
        institutional_interpretation: Market context interpretation.
    """

    vwap: str = ""
    institutional_bias: str = ""
    price_position: str = ""
    vwap_trend: str = ""
    support_resistance: str = ""
    institutional_interpretation: str = ""


@dataclass(frozen=True, slots=True)
class VWAPAnalysis:
    """Combined VWAP Intelligence output.

    Communicates institutional-grade VWAP analysis from supplied price
    data without prescribing entries, exits, or position sizing.

    Attributes:
        vwap: The computed VWAP price level.
        current_price: The most recent close price.
        distance: Normalized distance from VWAP ((price - vwap) / vwap).
        position: Price position relative to VWAP.
        bias: Institutional bias from VWAP context.
        slope: VWAP slope over the lookback period.
        upper_band: Upper deviation band price.
        lower_band: Lower deviation band price.
        trend: VWAP trend analysis sub-result.
        bands: VWAP bands analysis sub-result.
        confidence: Aggregate confidence (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    vwap: float
    current_price: float
    distance: float = 0.0
    position: VWAPPosition = VWAPPosition.UNKNOWN
    bias: VWAPBias = VWAPBias.UNKNOWN
    slope: float = 0.0
    upper_band: float = 0.0
    lower_band: float = 0.0
    trend: VWAPTrend | None = None
    bands: VWAPBands | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: VWAPExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> VWAPAnalysis:
        return cls(
            vwap=0.0,
            current_price=0.0,
            confidence=0.0,
            warnings=("VWAP data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Volume Intelligence
# ---------------------------------------------------------------------------


class VolumeBias(str, Enum):
    """Institutional bias derived from volume context."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ParticipationLevel(str, Enum):
    """Market participation intensity classification."""

    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class VolumeTrend:
    """Volume trend and expansion/contraction analysis.

    Attributes:
        slope: Volume linear regression slope.
        expanding: Whether volume is currently expanding.
        contracting: Whether volume is currently contracting.
        expansion_ratio: Ratio of current avg to previous avg volume.
        confidence: Confidence in the trend assessment (0-1).
        reasons: Human-readable reasons.
    """

    slope: float = 0.0
    expanding: bool = False
    contracting: bool = False
    expansion_ratio: float = 1.0
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RelativeVolume:
    """Relative volume and participation analysis.

    Attributes:
        rvol: Relative volume ratio (current / average).
        average_volume: The computed average volume over lookback.
        participation: Participation level classification.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    rvol: float = 0.0
    average_volume: float = 0.0
    participation: ParticipationLevel = ParticipationLevel.NORMAL
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AccumulationDistribution:
    """Accumulation/distribution analysis from price-volume divergence.

    Attributes:
        accumulation: Whether accumulation is detected (price up on rising vol).
        distribution: Whether distribution is detected (price down on rising vol).
        ad_ratio: Accumulation/distribution ratio (0-1 scale).
        divergence: Whether price-volume divergence is detected.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    accumulation: bool = False
    distribution: bool = False
    ad_ratio: float = 0.5
    divergence: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VolumeExplanation:
    """Structured explanation for Volume Intelligence.

    Attributes:
        current_volume: Current volume level explanation.
        relative_volume: Relative volume explanation.
        participation: Market participation explanation.
        accumulation_distribution: Accumulation/distribution explanation.
        breakout_quality: Breakout confirmation explanation.
        institutional_interpretation: Market context interpretation.
    """

    current_volume: str = ""
    relative_volume: str = ""
    participation: str = ""
    accumulation_distribution: str = ""
    breakout_quality: str = ""
    institutional_interpretation: str = ""


@dataclass(frozen=True, slots=True)
class VolumeAnalysis:
    """Combined Volume Intelligence output.

    Communicates institutional-grade volume analysis from supplied price
    data without prescribing entries, exits, or position sizing.

    Attributes:
        current_volume: The most recent candle volume.
        average_volume: Average volume over the lookback period.
        relative_volume: RVOL ratio (current / average).
        participation_level: Participation intensity classification.
        volume_bias: Institutional bias from volume context.
        breakout_confirmation: Whether volume confirms breakout/breakdown.
        exhaustion_probability: Estimated exhaustion risk (0-1).
        trend: Volume trend sub-result.
        relative: Relative volume sub-result.
        accumulation_distribution: Accumulation/distribution sub-result.
        confidence: Aggregate confidence (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    current_volume: int = 0
    average_volume: float = 0.0
    relative_volume: float = 0.0
    participation_level: ParticipationLevel = ParticipationLevel.NORMAL
    volume_bias: VolumeBias = VolumeBias.UNKNOWN
    breakout_confirmation: bool = False
    exhaustion_probability: float = 0.0
    trend: VolumeTrend | None = None
    relative: RelativeVolume | None = None
    accumulation_distribution: AccumulationDistribution | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: VolumeExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> VolumeAnalysis:
        return cls(
            confidence=0.0,
            warnings=("Volume data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Breadth Intelligence
# ---------------------------------------------------------------------------


class BreadthBias(str, Enum):
    """Institutional bias derived from market breadth context."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class BreadthStrength(str, Enum):
    """Market breadth strength classification."""

    VERY_WEAK = "very_weak"
    WEAK = "weak"
    NEUTRAL = "neutral"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass(frozen=True, slots=True)
class SectorBreadthSnapshot:
    """Breadth data for a single sector.

    Broker-independent input model.

    Attributes:
        sector_name: Name of the sector.
        advances: Number of advancing symbols.
        declines: Number of declining symbols.
        unchanged: Number of unchanged symbols.
        weight: Sector weight in the composite index (0-1).
        metadata: Additional context.
    """

    sector_name: str = ""
    advances: int = 0
    declines: int = 0
    unchanged: int = 0
    weight: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarketBreadthSnapshot:
    """Point-in-time market breadth data.

    Broker-independent input model consumed by BreadthAnalyzer.

    Attributes:
        timestamp: Observation time.
        index_name: Market index name (e.g. "NIFTY 50").
        advances: Total advancing symbols.
        declines: Total declining symbols.
        unchanged: Total unchanged symbols.
        total_symbols: Total symbols tracked.
        sector_summaries: Per-sector breadth snapshots.
        metadata: Additional context.
    """

    timestamp: datetime | None = None
    index_name: str = ""
    advances: int = 0
    declines: int = 0
    unchanged: int = 0
    total_symbols: int = 0
    sector_summaries: tuple[SectorBreadthSnapshot, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdvanceDecline:
    """Advance/decline ratio and dominance analysis.

    Attributes:
        ad_ratio: Ratio of advances to declines.
        advance_percentage: Percentage of total symbols advancing.
        decline_percentage: Percentage of total symbols declining.
        advance_dominance: Whether advances dominate declines.
        decline_dominance: Whether declines dominate advances.
        breadth_strength: Overall breadth strength classification.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    ad_ratio: float = 1.0
    advance_percentage: float = 50.0
    decline_percentage: float = 50.0
    advance_dominance: bool = False
    decline_dominance: bool = False
    breadth_strength: BreadthStrength = BreadthStrength.NEUTRAL
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SectorBreadth:
    """Sector-level breadth analysis.

    Attributes:
        advancing_sectors: Sectors with positive breadth.
        declining_sectors: Sectors with negative breadth.
        leading_sectors: Top performing sectors by net breadth.
        lagging_sectors: Bottom performing sectors by net breadth.
        rotation_detected: Whether sector rotation is detected.
        concentration_risk: Whether breadth is concentrated in few sectors.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    advancing_sectors: int = 0
    declining_sectors: int = 0
    leading_sectors: tuple[str, ...] = field(default_factory=tuple)
    lagging_sectors: tuple[str, ...] = field(default_factory=tuple)
    rotation_detected: bool = False
    concentration_risk: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MarketParticipation:
    """Market participation quality analysis.

    Attributes:
        participation_ratio: Ratio of participating to total symbols.
        internal_strength: Whether internals confirm price action.
        internal_weakness: Whether internals diverge from price action.
        divergence_detected: Whether breadth-price divergence is detected.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    participation_ratio: float = 1.0
    internal_strength: bool = False
    internal_weakness: bool = False
    divergence_detected: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BreadthExplanation:
    """Structured explanation for Breadth Intelligence.

    Attributes:
        overall_breadth: Overall breadth condition explanation.
        advance_decline: Advance/decline explanation.
        participation: Market participation explanation.
        sector_leadership: Sector leadership explanation.
        market_health: Market health assessment.
        institutional_interpretation: Market context interpretation.
    """

    overall_breadth: str = ""
    advance_decline: str = ""
    participation: str = ""
    sector_leadership: str = ""
    market_health: str = ""
    institutional_interpretation: str = ""


@dataclass(frozen=True, slots=True)
class BreadthAnalysis:
    """Combined Breadth Intelligence output.

    Communicates institutional-grade market breadth analysis from
    supplied MarketBreadthSnapshot without prescribing entries, exits,
    or position sizing.

    Attributes:
        advance_decline_ratio: Ratio of advances to declines.
        advance_percentage: Percentage of symbols advancing.
        participation_ratio: Ratio of participating (adv+dec) to total.
        breadth_strength: Overall breadth strength.
        breadth_bias: Institutional bias from breadth context.
        leading_sectors: Top performing sectors.
        lagging_sectors: Bottom performing sectors.
        divergence_detected: Whether breadth-price divergence is detected.
        market_health: Qualitative market health description.
        advance_decline: Advance/decline sub-result.
        sector_breadth: Sector breadth sub-result.
        market_participation: Market participation sub-result.
        confidence: Aggregate confidence (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    advance_decline_ratio: float = 1.0
    advance_percentage: float = 50.0
    participation_ratio: float = 1.0
    breadth_strength: BreadthStrength = BreadthStrength.NEUTRAL
    breadth_bias: BreadthBias = BreadthBias.UNKNOWN
    leading_sectors: tuple[str, ...] = field(default_factory=tuple)
    lagging_sectors: tuple[str, ...] = field(default_factory=tuple)
    divergence_detected: bool = False
    market_health: str = ""
    advance_decline: AdvanceDecline | None = None
    sector_breadth: SectorBreadth | None = None
    market_participation: MarketParticipation | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: BreadthExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> BreadthAnalysis:
        return cls(
            confidence=0.0,
            warnings=("Breadth data unavailable.",),
        )


# ---------------------------------------------------------------------------
# Market Regime Intelligence
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrendRegime:
    """Trend regime assessment synthesised from market structure + VWAP.

    Attributes:
        direction: Primary trend direction.
        strength: Aggregate trend strength (0-1).
        momentum_environment: Whether conditions favour momentum.
        mean_reversion_environment: Whether conditions favour mean reversion.
        aligned: Whether price trend and VWAP trend are aligned.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    direction: TrendDirection = TrendDirection.UNKNOWN
    strength: float = 0.0
    momentum_environment: bool = False
    mean_reversion_environment: bool = False
    aligned: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ParticipationRegime:
    """Participation regime synthesised from volume + breadth.

    Attributes:
        quality: Qualitative participation quality.
        institutional_confirmation: Whether institutions confirm the move.
        compressed: Whether participation suggests compression.
        expanding: Whether participation suggests expansion.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    quality: str = ""
    institutional_confirmation: bool = False
    compressed: bool = False
    expanding: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class StrategySuitability:
    """Strategy suitability for current market regime.

    Attributes:
        preferred: The most suitable strategy type.
        avoid_breakouts: Whether breakout strategies should be avoided.
        avoid_mean_reversion: Whether mean reversion should be avoided.
        confidence: Confidence in the assessment (0-1).
        reasons: Human-readable reasons.
    """

    preferred: StrategyType = StrategyType.NO_TRADE
    avoid_breakouts: bool = False
    avoid_mean_reversion: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Contextual intelligence for decision-making.

    Communicates regime suitability WITHOUT recommending trades.
    All fields describe the market environment, not an entry signal.

    Attributes:
        favorable_for_long: Whether environment supports long positioning.
        favorable_for_short: Whether environment supports short positioning.
        favorable_for_option_buying: Whether environment favours long vol.
        favorable_for_option_selling: Whether environment favours short vol.
        preferred_strategy: Most suitable approach.
        avoid_breakouts: Whether breakout trades carry elevated risk.
        avoid_mean_reversion: Whether reversion trades carry elevated risk.
        overall_score: Environmental score (0-100).
        confidence: Confidence in the context (0-1).
    """

    favorable_for_long: bool = False
    favorable_for_short: bool = False
    favorable_for_option_buying: bool = False
    favorable_for_option_selling: bool = False
    preferred_strategy: StrategyType = StrategyType.NO_TRADE
    avoid_breakouts: bool = False
    avoid_mean_reversion: bool = False
    overall_score: float = 50.0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class MarketRegimeExplanation:
    """Structured explanation for Market Regime Intelligence.

    Attributes:
        overall_regime: Overall regime explanation.
        trend_assessment: Trend assessment explanation.
        participation_assessment: Participation assessment explanation.
        institutional_confirmation: Confirmation level explanation.
        preferred_strategy: Strategy suitability explanation.
        risk_assessment: Risk environment explanation.
    """

    overall_regime: str = ""
    trend_assessment: str = ""
    participation_assessment: str = ""
    institutional_confirmation: str = ""
    preferred_strategy: str = ""
    risk_assessment: str = ""


@dataclass(frozen=True, slots=True)
class MarketRegimeAnalysis:
    """Combined Market Regime Intelligence output.

    Synthesises MarketStructure, VWAP, Volume, and Breadth intelligence
    into a unified institutional assessment of the current market
    environment. Does NOT recommend trades.

    Attributes:
        market_regime: Primary market regime classification.
        trend_strength: Aggregate trend strength (0-1).
        participation_quality: Qualitative participation description.
        institutional_confirmation: Whether institutions confirm price.
        market_health: Qualitative market health.
        preferred_strategy: Most suitable strategy type.
        decision_context: Contextual environment assessment.
        trend: Trend regime sub-result.
        participation: Participation regime sub-result.
        strategy: Strategy suitability sub-result.
        confidence: Aggregate confidence (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    market_regime: MarketRegime = MarketRegime.UNKNOWN
    trend_strength: float = 0.0
    participation_quality: str = ""
    institutional_confirmation: bool = False
    market_health: str = ""
    preferred_strategy: StrategyType = StrategyType.NO_TRADE
    decision_context: DecisionContext | None = None
    trend: TrendRegime | None = None
    participation: ParticipationRegime | None = None
    strategy: StrategySuitability | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: MarketRegimeExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> MarketRegimeAnalysis:
        return cls(
            confidence=0.0,
            warnings=("Market regime data unavailable.",),
        )
