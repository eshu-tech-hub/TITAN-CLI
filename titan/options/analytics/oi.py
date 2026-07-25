from dataclasses import dataclass
from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    MarketBias,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
)

DEFAULT_CONFIDENCE = 0.35
EMPTY_CONFIDENCE = 0.1
SINGLE_STRIKE_CONFIDENCE = 0.25
MIN_LIQUIDITY_VOLUME = 1
MIN_STRIKES_FOR_BALANCED_VIEW = 2
NEUTRAL_SCORE = 50.0
MAX_SCORE_DISTANCE = 50.0
STRONG_OI_RATIO = 1.25


@dataclass(frozen=True, slots=True)
class OpenInterestMetrics:
    """Calculated open-interest metrics before interpretation."""

    total_call_oi: int
    total_put_oi: int
    call_oi_change: int | None
    put_oi_change: int | None
    highest_call_oi_strike: float | None
    highest_put_oi_strike: float | None
    highest_call_change: int | None
    highest_put_change: int | None
    support_strike: float | None
    resistance_strike: float | None
    total_volume: int
    strike_count: int


@dataclass(frozen=True, slots=True)
class OpenInterestInterpretation:
    """Interpreted open-interest state."""

    market_bias: MarketBias
    score: float
    confidence: float
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


class OpenInterestAnalyzer(OptionAnalyzer):
    """Analyze option-chain open interest and produce evidence."""

    name = "OpenInterestAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Analyze open-interest structure from a snapshot.

        Args:
            snapshot: Broker-independent option-chain snapshot.

        Returns:
            Open-interest analysis result.
        """

        self._validate_snapshot(snapshot)
        metrics = self._calculate(snapshot)
        interpretation = self._interpret(metrics)

        return AnalysisResult(
            score=interpretation.score,
            confidence=interpretation.confidence,
            bullish=interpretation.market_bias is MarketBias.BULLISH,
            bearish=interpretation.market_bias is MarketBias.BEARISH,
            neutral=interpretation.market_bias
            in (MarketBias.NEUTRAL, MarketBias.UNKNOWN),
            reasons=interpretation.reasons,
            warnings=interpretation.warnings,
            metadata=self._metadata(metrics, interpretation),
        )

    def to_evidence(self, result: AnalysisResult) -> Evidence:
        """Convert open-interest analysis into universal evidence.

        Args:
            result: Analysis result returned by this analyzer.

        Returns:
            Evidence suitable for cross-module aggregation.

        Raises:
            TypeError: If result is not an AnalysisResult.
        """

        if not isinstance(result, AnalysisResult):
            raise TypeError("result must be an AnalysisResult.")

        return Evidence(
            source="Open Interest",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._evidence_signal(result),
            score=Score(result.score),
            confidence=Confidence(result.confidence),
            weight=1.0,
            reasons=result.reasons,
            warnings=result.warnings,
            metadata=result.metadata,
        )

    def _calculate(self, snapshot: OptionChainSnapshot) -> OpenInterestMetrics:
        """Calculate raw open-interest metrics.

        Args:
            snapshot: Broker-independent option-chain snapshot.

        Returns:
            Raw open-interest metrics.
        """

        strikes = snapshot.strikes
        total_call_oi = sum(strike.call_open_interest for strike in strikes)
        total_put_oi = sum(strike.put_open_interest for strike in strikes)
        call_changes = self._available_call_changes(strikes)
        put_changes = self._available_put_changes(strikes)
        highest_call_oi = self._max_by_call_oi(strikes)
        highest_put_oi = self._max_by_put_oi(strikes)

        return OpenInterestMetrics(
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            call_oi_change=sum(call_changes) if call_changes else None,
            put_oi_change=sum(put_changes) if put_changes else None,
            highest_call_oi_strike=(
                highest_call_oi.strike_price if highest_call_oi is not None else None
            ),
            highest_put_oi_strike=(
                highest_put_oi.strike_price if highest_put_oi is not None else None
            ),
            highest_call_change=max(call_changes) if call_changes else None,
            highest_put_change=max(put_changes) if put_changes else None,
            support_strike=(
                highest_put_oi.strike_price if highest_put_oi is not None else None
            ),
            resistance_strike=(
                highest_call_oi.strike_price if highest_call_oi is not None else None
            ),
            total_volume=sum(
                strike.call_volume + strike.put_volume for strike in strikes
            ),
            strike_count=len(strikes),
        )

    def _interpret(self, metrics: OpenInterestMetrics) -> OpenInterestInterpretation:
        """Interpret raw metrics into bias, score, confidence, and explanations."""

        reasons: list[str] = []
        warnings: list[str] = []

        if metrics.strike_count == 0:
            warnings.append("Incomplete Snapshot")
            return OpenInterestInterpretation(
                market_bias=MarketBias.UNKNOWN,
                score=NEUTRAL_SCORE,
                confidence=EMPTY_CONFIDENCE,
                reasons=("No strike-level OI data available.",),
                warnings=tuple(warnings),
            )

        if metrics.strike_count < MIN_STRIKES_FOR_BALANCED_VIEW:
            warnings.append("Incomplete Snapshot")
        if metrics.total_volume < MIN_LIQUIDITY_VOLUME:
            warnings.append("Low Liquidity")

        put_strength = self._safe_ratio(metrics.total_put_oi, metrics.total_call_oi)
        call_strength = self._safe_ratio(metrics.total_call_oi, metrics.total_put_oi)
        bias = MarketBias.NEUTRAL
        score = NEUTRAL_SCORE

        if put_strength >= STRONG_OI_RATIO:
            bias = MarketBias.BULLISH
            score = min(100.0, NEUTRAL_SCORE + self._score_distance(put_strength))
            reasons.append("Strong Put OI")
        elif call_strength >= STRONG_OI_RATIO:
            bias = MarketBias.BEARISH
            score = max(0.0, NEUTRAL_SCORE - self._score_distance(call_strength))
            reasons.append("Strong Call OI")
        else:
            reasons.append("Balanced OI")

        if metrics.put_oi_change is not None and metrics.put_oi_change > 0:
            reasons.append("Put OI Increasing")
            if bias is MarketBias.NEUTRAL:
                bias = MarketBias.BULLISH
                score = max(score, 60.0)

        if metrics.call_oi_change is not None and metrics.call_oi_change > 0:
            reasons.append("Call OI Increasing")
            if bias is MarketBias.NEUTRAL:
                bias = MarketBias.BEARISH
                score = min(score, 40.0)
            elif bias is MarketBias.BULLISH:
                warnings.append("Conflicting OI")

        if metrics.support_strike is not None:
            reasons.append("Support Identified")
        if metrics.resistance_strike is not None:
            reasons.append("Resistance Identified")

        confidence = self._confidence(metrics, warnings)

        return OpenInterestInterpretation(
            market_bias=bias,
            score=score,
            confidence=confidence,
            reasons=tuple(reasons),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _metadata(
        self,
        metrics: OpenInterestMetrics,
        interpretation: OpenInterestInterpretation,
    ) -> dict[str, Any]:
        """Build analysis metadata."""

        return {
            "total_call_oi": metrics.total_call_oi,
            "total_put_oi": metrics.total_put_oi,
            "call_oi_change": metrics.call_oi_change,
            "put_oi_change": metrics.put_oi_change,
            "highest_call_oi_strike": metrics.highest_call_oi_strike,
            "highest_put_oi_strike": metrics.highest_put_oi_strike,
            "highest_call_change": metrics.highest_call_change,
            "highest_put_change": metrics.highest_put_change,
            "support_strike": metrics.support_strike,
            "resistance_strike": metrics.resistance_strike,
            "market_bias": interpretation.market_bias,
        }

    def _evidence_signal(self, result: AnalysisResult) -> EvidenceSignal:
        """Derive evidence signal from analysis result."""

        market_bias = result.metadata.get("market_bias")

        if market_bias is MarketBias.BULLISH:
            return EvidenceSignal.BULLISH
        if market_bias is MarketBias.BEARISH:
            return EvidenceSignal.BEARISH
        if market_bias is MarketBias.NEUTRAL:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.UNKNOWN

    def _confidence(
        self,
        metrics: OpenInterestMetrics,
        warnings: list[str],
    ) -> float:
        """Calculate conservative confidence from data completeness."""

        if metrics.strike_count == 0:
            return EMPTY_CONFIDENCE
        if metrics.strike_count == 1:
            return SINGLE_STRIKE_CONFIDENCE
        if warnings:
            return DEFAULT_CONFIDENCE
        return 0.5

    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        """Return a ratio that handles zero denominators."""

        if denominator == 0:
            return float(numerator) if numerator > 0 else 1.0
        return numerator / denominator

    def _score_distance(self, ratio: float) -> float:
        """Translate OI imbalance into a bounded score distance."""

        return min(MAX_SCORE_DISTANCE, (ratio - 1.0) * 40.0)

    def _available_call_changes(
        self,
        strikes: tuple[OptionStrikeSnapshot, ...],
    ) -> list[int]:
        """Return available call OI change values."""

        return [
            strike.call_open_interest_change
            for strike in strikes
            if strike.call_open_interest_change is not None
        ]

    def _available_put_changes(
        self,
        strikes: tuple[OptionStrikeSnapshot, ...],
    ) -> list[int]:
        """Return available put OI change values."""

        return [
            strike.put_open_interest_change
            for strike in strikes
            if strike.put_open_interest_change is not None
        ]

    def _max_by_call_oi(
        self,
        strikes: tuple[OptionStrikeSnapshot, ...],
    ) -> OptionStrikeSnapshot | None:
        """Return strike with highest call OI."""

        if not strikes:
            return None
        return max(strikes, key=lambda strike: strike.call_open_interest)

    def _max_by_put_oi(
        self,
        strikes: tuple[OptionStrikeSnapshot, ...],
    ) -> OptionStrikeSnapshot | None:
        """Return strike with highest put OI."""

        if not strikes:
            return None
        return max(strikes, key=lambda strike: strike.put_open_interest)
