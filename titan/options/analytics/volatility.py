from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.options.analytics.hv import HVAnalyzer
from titan.options.analytics.iv import IVAnalyzer
from titan.options.analytics.iv_percentile import IVPercentileAnalyzer
from titan.options.analytics.iv_rank import IVRankAnalyzer
from titan.options.analytics.models import (
    IVHVRelation,
    MarketBias,
    VolatilityAnalysis,
    VolatilityExplanation,
    VolatilitySnapshot,
)
from titan.options.analytics.volatility_regime import (
    VolatilityRegimeAnalyzer,
)

NEUTRAL_CONFIDENCE = 0.0
IV_HV_PREMIUM_RATIO = 1.10
IV_HV_DISCOUNT_RATIO = 0.90
IV_HV_MISPRICING_RATIO = 0.50


class VolatilityAnalyzer:
    """Orchestrator for volatility intelligence.

    Runs all sub-analyzers (IV, HV, IV Rank, IV Percentile, Regime)
    against a single VolatilitySnapshot and produces a unified
    VolatilityAnalysis result with evidence and explanation.

    This is the primary entry point for the Volatility Intelligence Engine.
    """

    name = "VolatilityAnalyzer"

    def __init__(self) -> None:
        self._iv = IVAnalyzer()
        self._hv = HVAnalyzer()
        self._iv_rank = IVRankAnalyzer()
        self._iv_percentile = IVPercentileAnalyzer()
        self._regime = VolatilityRegimeAnalyzer()

    def analyze(self, snapshot: VolatilitySnapshot) -> VolatilityAnalysis:
        """Run all volatility sub-analyzers and fuse results.

        Args:
            snapshot: Volatility data snapshot. All values may be None.

        Returns:
            Combined VolatilityAnalysis with evidence and explanation.
        """

        if not isinstance(snapshot, VolatilitySnapshot):
            raise TypeError("snapshot must be a VolatilitySnapshot.")

        iv_level, iv_trend, iv_conf = self._iv.analyze(snapshot)
        current_hv, hv_trend, hv_stability, hv_conf = self._hv.analyze(snapshot)
        rank_level, rank_value, rank_conf = self._iv_rank.analyze(snapshot)
        pctl_level, pctl_value, pctl_conf = self._iv_percentile.analyze(snapshot)
        regime, buying_bias, selling_bias, regime_conf = self._regime.analyze(
            snapshot, iv_trend
        )

        iv_vs_hv = self._determine_iv_vs_hv_relation(
            snapshot.implied_volatility, snapshot.historical_volatility
        )
        overall_bias = self._determine_overall_bias(
            iv_level, iv_vs_hv, regime, buying_bias, selling_bias
        )
        confidence = self._calculate_confidence(iv_conf, hv_conf, regime_conf)
        warnings = self._generate_warnings(snapshot)

        analysis = VolatilityAnalysis(
            current_iv=snapshot.implied_volatility,
            current_hv=current_hv,
            iv_rank=rank_value,
            iv_percentile=pctl_value,
            iv_vs_hv=iv_vs_hv,
            volatility_regime=regime,
            iv_level=iv_level,
            iv_rank_level=rank_level,
            iv_trend=iv_trend,
            hv_trend=hv_trend,
            hv_stability=hv_stability,
            buying_bias=buying_bias,
            selling_bias=selling_bias,
            overall_bias=overall_bias,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(snapshot),
        )

        evidence = self.to_evidence(analysis)
        explanation = self.explanation(analysis)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    def to_evidence(self, analysis: VolatilityAnalysis) -> Evidence:
        """Convert volatility analysis into universal evidence.

        Args:
            analysis: Completed volatility analysis.

        Returns:
            Evidence suitable for fusion.
        """

        return Evidence(
            source="Volatility",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._evidence_signal(analysis),
            score=Score(self._evidence_score(analysis)),
            confidence=Confidence(analysis.confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "iv_level": analysis.iv_level.value,
                "iv_rank_level": analysis.iv_rank_level.value,
                "iv_vs_hv": analysis.iv_vs_hv.value,
                "volatility_regime": analysis.volatility_regime.value,
                "overall_bias": analysis.overall_bias.value,
            },
        )

    def explanation(self, analysis: VolatilityAnalysis) -> VolatilityExplanation:
        """Generate structured explanation from analysis.

        Args:
            analysis: Completed volatility analysis.

        Returns:
            Structured explanation with all required sections.
        """

        return VolatilityExplanation(
            current_volatility=self._current_volatility_section(analysis),
            historical_comparison=self._historical_comparison_section(analysis),
            iv_vs_hv=self._iv_vs_hv_section(analysis),
            regime=self._regime_section(analysis),
            risk=self._risk_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
            warnings=analysis.warnings,
        )

    def _determine_iv_vs_hv_relation(
        self,
        iv: float | None,
        hv: float | None,
    ) -> IVHVRelation:
        if iv is None or hv is None:
            return IVHVRelation.UNKNOWN

        ratio = iv / hv if hv > 0.0 else float("inf")

        if ratio >= IV_HV_PREMIUM_RATIO:
            return IVHVRelation.IV_PREMIUM
        if ratio <= IV_HV_DISCOUNT_RATIO:
            return IVHVRelation.IV_DISCOUNT
        if ratio <= IV_HV_MISPRICING_RATIO:
            return IVHVRelation.MISPRICING
        return IVHVRelation.NORMAL

    def _determine_overall_bias(
        self,
        iv_level: Any,
        iv_vs_hv: IVHVRelation,
        regime: Any,
        buying_bias: bool,
        selling_bias: bool,
    ) -> MarketBias:
        if buying_bias and not selling_bias:
            return MarketBias.BULLISH
        if selling_bias and not buying_bias:
            return MarketBias.BEARISH

        if iv_vs_hv is IVHVRelation.IV_PREMIUM:
            return MarketBias.BEARISH
        if iv_vs_hv is IVHVRelation.IV_DISCOUNT:
            return MarketBias.BULLISH

        return MarketBias.NEUTRAL

    def _calculate_confidence(
        self,
        iv_conf: float,
        hv_conf: float,
        regime_conf: float,
    ) -> float:
        confidences = [c for c in (iv_conf, hv_conf, regime_conf) if c > 0.0]

        if not confidences:
            return NEUTRAL_CONFIDENCE

        return sum(confidences) / len(confidences)

    def _generate_warnings(self, snapshot: VolatilitySnapshot) -> tuple[str, ...]:
        warnings: list[str] = []

        if snapshot.implied_volatility is None:
            warnings.append("Implied volatility not supplied.")
        if snapshot.historical_volatility is None:
            warnings.append("Historical volatility not supplied.")
        if snapshot.iv_rank is None:
            warnings.append("IV rank not supplied.")
        if snapshot.iv_percentile is None:
            warnings.append("IV percentile not supplied.")

        return tuple(warnings)

    def _metadata(self, snapshot: VolatilitySnapshot) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "has_iv": snapshot.implied_volatility is not None,
            "has_hv": snapshot.historical_volatility is not None,
            "has_iv_rank": snapshot.iv_rank is not None,
            "has_iv_percentile": snapshot.iv_percentile is not None,
        }

    def _evidence_signal(self, analysis: VolatilityAnalysis) -> EvidenceSignal:
        bias = analysis.overall_bias

        if bias is MarketBias.BULLISH:
            return EvidenceSignal.BULLISH
        if bias is MarketBias.BEARISH:
            return EvidenceSignal.BEARISH
        return EvidenceSignal.NEUTRAL

    def _evidence_score(self, analysis: VolatilityAnalysis) -> float:
        bias = analysis.overall_bias

        if bias is MarketBias.BULLISH or bias is MarketBias.BEARISH:
            return 50.0 + (analysis.confidence * 30.0)
        return 50.0

    def _evidence_reasons(self, analysis: VolatilityAnalysis) -> tuple[str, ...]:
        reasons: list[str] = []

        if analysis.iv_level is not None:
            reasons.append(f"IV is {analysis.iv_level.value}.")
        if analysis.iv_vs_hv is not None:
            reasons.append(f"IV vs HV: {analysis.iv_vs_hv.value}.")
        if analysis.iv_rank_level is not None:
            reasons.append(f"IV rank is {analysis.iv_rank_level.value}.")
        if analysis.volatility_regime is not None:
            reasons.append(f"Regime: {analysis.volatility_regime.value}.")

        return tuple(reasons)

    def _current_volatility_section(self, analysis: VolatilityAnalysis) -> str:
        iv = analysis.current_iv
        if iv is None:
            return "Current volatility data is unavailable."

        return (
            f"Current implied volatility is {iv:.2%}. "
            f"Classification: {analysis.iv_level.value}. "
            f"Trend: {analysis.iv_trend.value}."
        )

    def _historical_comparison_section(self, analysis: VolatilityAnalysis) -> str:
        hv = analysis.current_hv
        if hv is None:
            return "Historical volatility data is unavailable."

        return (
            f"Historical volatility is {hv:.2%}. "
            f"Trend: {analysis.hv_trend.value}. "
            f"Stability: {analysis.hv_stability.value}."
        )

    def _iv_vs_hv_section(self, analysis: VolatilityAnalysis) -> str:
        relation = analysis.iv_vs_hv

        if relation is IVHVRelation.UNKNOWN:
            return "IV vs HV comparison is unavailable."

        descriptions = {
            IVHVRelation.IV_PREMIUM: (
                "Implied volatility trades at a premium to historical "
                "volatility, suggesting elevated option prices."
            ),
            IVHVRelation.IV_DISCOUNT: (
                "Implied volatility trades at a discount to historical "
                "volatility, suggesting depressed option prices."
            ),
            IVHVRelation.MISPRICING: (
                "Extreme divergence between implied and historical "
                "volatility suggests potential mispricing."
            ),
            IVHVRelation.NORMAL: ("Implied and historical volatility are aligned."),
        }

        return descriptions.get(relation, "IV vs HV comparison is unavailable.")

    def _regime_section(self, analysis: VolatilityAnalysis) -> str:
        regime = analysis.volatility_regime

        descriptions = {
            "expansion": (
                "Volatility is in an expansion regime with rising implied "
                "volatility above historical levels."
            ),
            "compression": (
                "Volatility is in a compression regime with declining implied "
                "volatility below historical levels."
            ),
            "stable": (
                "Volatility regime is stable with implied and historical "
                "volatility in alignment."
            ),
            "transition": (
                "Volatility regime is in transition. Current levels are "
                "normal but trending."
            ),
        }

        return descriptions.get(
            regime.value,
            "Volatility regime cannot be determined.",
        )

    def _risk_section(self, analysis: VolatilityAnalysis) -> str:
        warnings = analysis.warnings
        if not warnings:
            return (
                "No volatility-related risk warnings. " "Data completeness is adequate."
            )

        return "Volatility risk warnings:\n" + "\n".join(f"  - {w}" for w in warnings)

    def _institutional_section(self, analysis: VolatilityAnalysis) -> str:
        regime = analysis.volatility_regime
        iv_vs_hv = analysis.iv_vs_hv

        parts: list[str] = ["Institutional Interpretation:"]

        if regime.value == "expansion":
            parts.append(
                "Options are relatively expensive. Consider premium "
                "collection strategies or avoiding long premium positions."
            )
        elif regime.value == "compression":
            parts.append(
                "Options are relatively cheap. Consider long premium "
                "strategies or volatility mean-reversion plays."
            )

        if iv_vs_hv is IVHVRelation.IV_PREMIUM:
            parts.append(
                " IV premium suggests market is pricing in higher "
                "future volatility. Consider tail-risk hedging."
            )
        elif iv_vs_hv is IVHVRelation.IV_DISCOUNT:
            parts.append(
                " IV discount suggests complacency. Monitor for "
                "potential volatility shocks."
            )

        if analysis.buying_bias:
            parts.append(
                " Conditions favor volatility buying. "
                "Consider long straddles or strangles."
            )
        if analysis.selling_bias:
            parts.append(
                " Conditions favor volatility selling. "
                "Consider short premium or credit strategies."
            )

        return " ".join(parts)
