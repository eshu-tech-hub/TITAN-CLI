"""VWAP Intelligence Engine — Orchestrator and Core Computation.

Provides institutional-grade VWAP analysis from supplied price data.
Computes session VWAP, evaluates price relative to VWAP, determines
institutional bias, and generates evidence and explanation.

Pure orchestrator — no broker imports, no API calls.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
  - Market Structure Intelligence
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.market.intelligence.models import (
    TrendDirection,
    VWAPAnalysis,
    VWAPBands,
    VWAPBias,
    VWAPExplanation,
    VWAPPosition,
    VWAPTrend,
)
from titan.market.intelligence.vwap_bands import VWAPBandsAnalyzer
from titan.market.intelligence.vwap_trend import VWAPTrendAnalyzer
from titan.market.series import MarketDataSeries

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

DISTANCE_BULLISH = 0.005
DISTANCE_BEARISH = -0.005
DISTANCE_AT = 0.001


class VWAPEngine:
    """Core VWAP computation engine.

    Computes session VWAP and per-candle VWAP values from MarketDataSeries.
    Uses typical price ((H+L+C)/3) weighted by volume.
    """

    name = "VWAPEngine"

    def compute_vwap(self, series: MarketDataSeries) -> list[float]:
        """Compute per-candle cumulative VWAP values.

        Args:
            series: Market data series with OHLCV candles.

        Returns:
            List of cumulative VWAP values for each candle.
        """
        vwap_values: list[float] = []
        cum_pv = 0.0
        cum_v = 0

        for candle in series:
            typical = (candle.high + candle.low + candle.close) / 3.0
            cum_pv += typical * candle.volume
            cum_v += candle.volume
            if cum_v > 0:
                vwap_values.append(cum_pv / cum_v)
            else:
                vwap_values.append(0.0)

        return vwap_values

    def current_vwap(self, vwap_values: list[float]) -> float:
        """Return the most recent VWAP value.

        Args:
            vwap_values: Pre-computed per-candle VWAP values.

        Returns:
            The latest VWAP level, or 0.0 if no data.
        """
        if not vwap_values:
            return 0.0
        return vwap_values[-1]


class VWAPAnalyzer:
    """Orchestrate VWAP Intelligence.

    Consumes MarketDataSeries and delegates to VWAPEngine,
    VWAPTrendAnalyzer, and VWAPBandsAnalyzer to produce a unified
    institutional assessment of VWAP context. Pure orchestrator —
    does not recalculate any VWAP metric.
    """

    name = "VWAPAnalyzer"

    def __init__(
        self,
        engine: VWAPEngine | None = None,
        trend_analyzer: VWAPTrendAnalyzer | None = None,
        bands_analyzer: VWAPBandsAnalyzer | None = None,
    ) -> None:
        self._engine = engine or VWAPEngine()
        self._trend = trend_analyzer or VWAPTrendAnalyzer()
        self._bands = bands_analyzer or VWAPBandsAnalyzer()

    def analyze(
        self,
        series: MarketDataSeries,
    ) -> VWAPAnalysis:
        """Execute VWAP intelligence analysis.

        Args:
            series: Market data series with OHLCV candles.

        Returns:
            Combined VWAPAnalysis.
        """

        if len(series) < 2:
            return self._empty_analysis(
                f"Insufficient data: need at least 2 candles, got {len(series)}."
            )

        vwap_values = self._engine.compute_vwap(series)
        vwap_level = vwap_values[-1]
        current_price = series.closes[-1]
        distance = self._distance(current_price, vwap_level)
        position = self._position(distance)
        slope = self._compute_slope(vwap_values)
        bias = self._bias(position, slope)

        trend = self._trend.analyze(series, vwap_values, vwap_level)
        bands = self._bands.analyze(series, vwap_values, vwap_level)

        confidence = self._calculate_confidence(vwap_values, trend, bands, bias)

        analysis = VWAPAnalysis(
            vwap=vwap_level,
            current_price=current_price,
            distance=distance,
            position=position,
            bias=bias,
            slope=slope,
            upper_band=bands.upper,
            lower_band=bands.lower,
            trend=trend,
            bands=bands,
            confidence=confidence,
            warnings=self._combine_warnings(series, vwap_values, trend, bands),
            metadata=self._metadata(series, vwap_values, trend, bands),
        )

        evidence = self._to_evidence(analysis, trend)
        explanation = self._explanation(analysis, trend, bands)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Core calculations
    # ------------------------------------------------------------------

    def _distance(self, price: float, vwap: float) -> float:
        if vwap == 0:
            return 0.0
        return (price - vwap) / vwap

    def _position(self, distance: float) -> VWAPPosition:
        if distance > DISTANCE_AT:
            return VWAPPosition.ABOVE
        if distance < -DISTANCE_AT:
            return VWAPPosition.BELOW
        return VWAPPosition.AT

    def _compute_slope(self, vwap_values: list[float]) -> float:
        if len(vwap_values) < 2:
            return 0.0
        recent = vwap_values[-min(10, len(vwap_values)) :]
        n = len(recent)
        x_avg = (n - 1) / 2.0
        y_avg = sum(recent) / n
        num = sum((i - x_avg) * (v - y_avg) for i, v in enumerate(recent))
        den = sum((i - x_avg) ** 2 for i in range(n))
        if den == 0:
            return 0.0
        return num / den

    def _bias(
        self,
        position: VWAPPosition,
        slope: float,
    ) -> VWAPBias:
        if position is VWAPPosition.ABOVE:
            if slope > 0:
                return VWAPBias.BULLISH
            return VWAPBias.NEUTRAL
        if position is VWAPPosition.BELOW:
            if slope < 0:
                return VWAPBias.BEARISH
            return VWAPBias.NEUTRAL
        if position is VWAPPosition.AT:
            if slope > 0:
                return VWAPBias.BULLISH
            if slope < 0:
                return VWAPBias.BEARISH
            return VWAPBias.NEUTRAL
        return VWAPBias.UNKNOWN

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        vwap_values: list[float],
        trend: VWAPTrend,
        bands: VWAPBands,
        bias: VWAPBias,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if bias is not VWAPBias.UNKNOWN:
            confidences.append(0.6)
            weights.append(0.3)

        if trend.confidence > 0:
            confidences.append(trend.confidence)
            weights.append(0.4)

        if bands.confidence > 0:
            confidences.append(bands.confidence)
            weights.append(0.3)

        sample_factor = min(1.0, len(vwap_values) / 20)
        confidences.append(sample_factor)
        weights.append(0.2)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------

    def _combine_warnings(
        self,
        series: MarketDataSeries,
        vwap_values: list[float],
        trend: VWAPTrend,
        bands: VWAPBands,
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if len(series) < 10:
            combined.append(
                f"Limited data: {len(series)} candle(s). "
                "VWAP analysis may be unreliable."
            )

        if trend.confidence < CONFIDENCE_LOW:
            combined.append("Low VWAP trend confidence.")

        if bands.confidence < CONFIDENCE_LOW:
            combined.append("Low VWAP band confidence.")

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        series: MarketDataSeries,
        vwap_values: list[float],
        trend: VWAPTrend,
        bands: VWAPBands,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "candle_count": len(series),
            "vwap_slope": trend.slope,
            "crossover": trend.crossover,
            "reclaim": trend.reclaim,
            "rejection": trend.rejection,
            "pullback": trend.pullback,
            "upper_band": bands.upper,
            "lower_band": bands.lower,
            "bandwidth": bands.bandwidth,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, bias: VWAPBias) -> EvidenceSignal:
        mapping = {
            VWAPBias.BULLISH: EvidenceSignal.BULLISH,
            VWAPBias.BEARISH: EvidenceSignal.BEARISH,
            VWAPBias.NEUTRAL: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(bias, EvidenceSignal.UNKNOWN)

    def _evidence_score(
        self,
        analysis: VWAPAnalysis,
        trend: VWAPTrend,
    ) -> float:
        base = NEUTRAL_SCORE
        if analysis.bias is VWAPBias.BULLISH:
            base = POSITIVE_SCORE
        elif analysis.bias is VWAPBias.BEARISH:
            base = NEGATIVE_SCORE

        adj = 0.0
        if trend.crossover or trend.reclaim:
            adj += 5.0
        if trend.rejection:
            adj -= 5.0 if base < NEUTRAL_SCORE else 0.0
        if analysis.confidence >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.confidence >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: VWAPAnalysis,
        trend: VWAPTrend,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"Price is {analysis.position.value} VWAP.")
        reasons.append(f"Institutional bias is {analysis.bias.value}.")
        reasons.append(f"Distance from VWAP: {analysis.distance:.4f}.")

        if trend.crossover:
            reasons.append("VWAP crossover detected — price crossed VWAP.")
        if trend.reclaim:
            reasons.append("VWAP reclaim detected.")
        if trend.rejection:
            reasons.append("VWAP rejection detected.")
        if trend.pullback:
            reasons.append("VWAP pullback detected.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: VWAPAnalysis,
        trend: VWAPTrend,
    ) -> Evidence:
        signal = self._evidence_signal(analysis.bias)
        score = self._evidence_score(analysis, trend)
        confidence = analysis.confidence

        return Evidence(
            source="VWAP",
            category=EvidenceCategory.MARKET_STRUCTURE,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis, trend),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "vwap": analysis.vwap,
                "distance": analysis.distance,
                "position": analysis.position.value,
                "bias": analysis.bias.value,
                "slope": analysis.slope,
                "upper_band": analysis.upper_band,
                "lower_band": analysis.lower_band,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: VWAPAnalysis,
        trend: VWAPTrend,
        bands: VWAPBands,
    ) -> VWAPExplanation:
        return VWAPExplanation(
            vwap=self._vwap_section(analysis),
            institutional_bias=self._bias_section(analysis),
            price_position=self._position_section(analysis),
            vwap_trend=self._trend_section(analysis, trend),
            support_resistance=self._sr_section(analysis, bands),
            institutional_interpretation=self._institutional_section(analysis),
        )

    def _vwap_section(self, analysis: VWAPAnalysis) -> str:
        return (
            f"VWAP Level: {analysis.vwap:.2f}. "
            f"Price is {analysis.distance * 100:.2f}% "
            f"{'above' if analysis.position is VWAPPosition.ABOVE else 'below' if analysis.position is VWAPPosition.BELOW else 'at'} VWAP."
        )

    def _bias_section(self, analysis: VWAPAnalysis) -> str:
        mapping = {
            VWAPBias.BULLISH: "Institutional bias is bullish. Price above VWAP supports long positions.",
            VWAPBias.BEARISH: "Institutional bias is bearish. Price below VWAP supports short positions.",
            VWAPBias.NEUTRAL: "Institutional bias is neutral. VWAP position is inconclusive.",
        }
        return mapping.get(analysis.bias, "Institutional bias cannot be determined.")

    def _position_section(self, analysis: VWAPAnalysis) -> str:
        pos_map = {
            VWAPPosition.ABOVE: (
                "Price is trading above VWAP. Institutional flow is "
                "potentially supportive of longs."
            ),
            VWAPPosition.BELOW: (
                "Price is trading below VWAP. Institutional flow is "
                "potentially supportive of shorts."
            ),
            VWAPPosition.AT: "Price is at VWAP. Decision point for institutional flow.",
        }
        return pos_map.get(
            analysis.position,
            "Price position relative to VWAP cannot be determined.",
        )

    def _trend_section(self, analysis: VWAPAnalysis, trend: VWAPTrend) -> str:
        parts: list[str] = ["VWAP Trend Assessment:"]

        dir_map = {
            TrendDirection.BULLISH: "VWAP is rising.",
            TrendDirection.BEARISH: "VWAP is falling.",
            TrendDirection.SIDEWAYS: "VWAP is flat.",
        }
        parts.append(dir_map.get(trend.direction, "VWAP direction unknown."))
        parts.append(f"VWAP slope: {trend.slope:.6f}.")

        if trend.crossover:
            parts.append("Price crossed VWAP.")
        if trend.reclaim:
            parts.append("Price reclaimed VWAP from below.")
        if trend.rejection:
            parts.append("Price was rejected at VWAP.")
        if trend.pullback:
            parts.append("Price pulled back to VWAP.")

        return " ".join(parts)

    def _sr_section(self, analysis: VWAPAnalysis, bands: VWAPBands) -> str:
        parts: list[str] = ["VWAP Support / Resistance:"]

        if bands.upper > 0:
            parts.append(f"Upper deviation band at {bands.upper:.2f}.")
        if bands.lower > 0:
            parts.append(f"Lower deviation band at {bands.lower:.2f}.")
        parts.append(f"Current deviation: {bands.deviation:.2f} standard deviations.")

        return " ".join(parts)

    def _institutional_section(self, analysis: VWAPAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        bias = analysis.bias
        distance = analysis.distance
        abs_dist = abs(distance)

        if bias is VWAPBias.BULLISH:
            if abs_dist >= DISTANCE_BULLISH:
                parts.append(
                    "Price extended above VWAP. Monitor for mean reversion "
                    "or trend continuation on pullback to VWAP."
                )
            else:
                parts.append(
                    "Price near VWAP with bullish bias. Watch for "
                    "confirmation of institutional accumulation."
                )
        elif bias is VWAPBias.BEARISH:
            if abs_dist >= -DISTANCE_BEARISH:
                parts.append(
                    "Price extended below VWAP. Monitor for mean reversion "
                    "or trend continuation on pullback to VWAP."
                )
            else:
                parts.append(
                    "Price near VWAP with bearish bias. Watch for "
                    "confirmation of institutional distribution."
                )
        elif bias is VWAPBias.NEUTRAL:
            parts.append(
                "No clear institutional bias from VWAP. "
                "Cross-reference with market structure and order flow."
            )
        else:
            parts.append(
                "VWAP data is unavailable or insufficient "
                "for institutional interpretation."
            )

        if analysis.confidence < CONFIDENCE_LOW:
            parts.append(
                "Low confidence suggests limited data availability. "
                "Interpret with caution."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> VWAPAnalysis:
        analysis = VWAPAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = VWAPExplanation(
            vwap="VWAP assessment unavailable: insufficient data.",
            institutional_bias="Institutional bias unavailable: insufficient data.",
            price_position="Price position unavailable: insufficient data.",
            vwap_trend="VWAP trend assessment unavailable: insufficient data.",
            support_resistance="VWAP support/resistance unavailable: insufficient data.",
            institutional_interpretation="Institutional Interpretation: VWAP data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
