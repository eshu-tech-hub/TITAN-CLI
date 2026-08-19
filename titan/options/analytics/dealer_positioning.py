"""Dealer Positioning Intelligence Engine orchestrator.

Estimates dealer positioning, inventory bias, directional bias, and
likely hedging pressure from supplied option analytics. Pure orchestrator
— no broker imports, no API calls, no order flow estimation.
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.dealer_bias import DealerBiasAnalyzer
from titan.options.analytics.dealer_inventory import DealerInventoryAnalyzer
from titan.options.analytics.models import (
    DealerBias,
    DealerBiasLevel,
    DealerInventory,
    DealerPositioningAnalysis,
    DealerPositioningExplanation,
    DealerPositioningInput,
    DealerSide,
    GreeksAnalysis,
    LiquidityAnalysis,
    OptionChainAnalysis,
    SurfaceIntelligenceAnalysis,
)

NEUTRAL_SCORE = 50.0
HEDGING_LOW_THRESHOLD = 0.3
HEDGING_MODERATE_THRESHOLD = 0.5
HEDGING_HIGH_THRESHOLD = 0.7


class DealerPositioningAnalyzer:
    """Orchestrate dealer positioning intelligence.

    Consumes OptionChainAnalysis, GreeksAnalysis, LiquidityAnalysis,
    and SurfaceIntelligenceAnalysis to produce a unified institutional
    assessment of dealer positioning. Pure orchestrator — does not
    recalculate any option metric or greek.
    """

    name = "DealerPositioningAnalyzer"

    def __init__(
        self,
        inventory_analyzer: DealerInventoryAnalyzer | None = None,
        bias_analyzer: DealerBiasAnalyzer | None = None,
    ) -> None:
        self._inventory = inventory_analyzer or DealerInventoryAnalyzer()
        self._bias = bias_analyzer or DealerBiasAnalyzer()

    def analyze(
        self,
        option_chain: OptionChainAnalysis | None = None,
        greeks: GreeksAnalysis | None = None,
        liquidity: LiquidityAnalysis | None = None,
        surface: SurfaceIntelligenceAnalysis | None = None,
    ) -> DealerPositioningAnalysis:
        input_data = DealerPositioningInput(
            option_chain=option_chain,
            greeks=greeks,
            liquidity=liquidity,
            surface=surface,
        )

        if all(v is None for v in (option_chain, greeks, liquidity, surface)):
            return self._empty_analysis("No dealer positioning inputs provided.")

        inventory = self._inventory.analyze(input_data)
        bias = self._bias.analyze(input_data)
        hedging_pressure = self._calculate_hedging_pressure(inventory, bias, input_data)
        confidence = self._calculate_confidence(inventory, bias)
        warnings = self._combine_warnings(inventory, bias, input_data)
        dealer_side = inventory.dealer_side
        dealer_bias = bias.bias_level

        if dealer_side is DealerSide.UNKNOWN and inventory.confidence > 0:
            dealer_side = DealerSide.NEUTRAL
        if dealer_bias is DealerBiasLevel.UNKNOWN and bias.confidence > 0:
            dealer_bias = DealerBiasLevel.NEUTRAL

        analysis = DealerPositioningAnalysis(
            dealer_side=dealer_side,
            dealer_bias=dealer_bias,
            hedging_pressure=hedging_pressure,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(input_data, inventory, bias),
        )

        evidence = self._to_evidence(analysis, inventory, bias)
        explanation = self._explanation(analysis, inventory, bias)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    def _calculate_hedging_pressure(
        self,
        inventory: DealerInventory,
        bias: DealerBias,
        input_data: DealerPositioningInput,
    ) -> float:
        """Estimate likely hedging intensity from 0 (none) to 1 (extreme).

        Combines gamma positioning extremity, directional conviction,
        and short-gamma amplification risk.
        """
        score = 0.0
        factors = 0

        if inventory.dealer_side in (
            DealerSide.LONG_GAMMA,
            DealerSide.SHORT_GAMMA,
        ):
            extremity = abs(inventory.inventory_score) / 100.0
            score += extremity * inventory.confidence
            factors += 1

        if bias.bias_level in (
            DealerBiasLevel.BULLISH,
            DealerBiasLevel.BEARISH,
        ):
            conviction = abs(bias.bias_score) / 100.0
            score += conviction * bias.confidence
            factors += 1

        if (
            inventory.dealer_side is DealerSide.SHORT_GAMMA
            and inventory.confidence > 0.3
        ):
            score += 0.2

        if factors == 0:
            return 0.0

        return min(1.0, score / factors)

    def _calculate_confidence(
        self,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> float:
        confidences = []
        weights = []

        if inventory.confidence > 0:
            confidences.append(inventory.confidence)
            weights.append(0.5)

        if bias.confidence > 0:
            confidences.append(bias.confidence)
            weights.append(0.5)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    def _combine_warnings(
        self,
        inventory: DealerInventory,
        bias: DealerBias,
        input_data: DealerPositioningInput,
    ) -> tuple[str, ...]:
        combined: list[str] = []
        seen: set[str] = set()

        for src in (inventory, bias):
            for w in src.warnings:
                if w not in seen:
                    combined.append(f"[{src.__class__.__name__}] {w}")
                    seen.add(w)

        if input_data.liquidity is None:
            combined.append("Liquidity analysis not available.")

        return tuple(combined)

    def _metadata(
        self,
        input_data: DealerPositioningInput,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "inventory_side": inventory.dealer_side.value,
            "inventory_score": inventory.inventory_score,
            "inventory_confidence": inventory.confidence,
            "bias_level": bias.bias_level.value,
            "bias_score": bias.bias_score,
            "bias_confidence": bias.confidence,
            "option_chain_available": input_data.option_chain is not None,
            "greeks_available": input_data.greeks is not None,
            "liquidity_available": input_data.liquidity is not None,
            "surface_available": input_data.surface is not None,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(
        self,
        dealer_bias: DealerBiasLevel,
    ) -> EvidenceSignal:
        mapping = {
            DealerBiasLevel.BULLISH: EvidenceSignal.BULLISH,
            DealerBiasLevel.BEARISH: EvidenceSignal.BEARISH,
            DealerBiasLevel.NEUTRAL: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(dealer_bias, EvidenceSignal.UNKNOWN)

    def _evidence_score(
        self,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> float:
        weighted_sum = 0.0
        total_weight = 0.0

        if inventory.confidence > 0:
            inv_score = NEUTRAL_SCORE + inventory.inventory_score * 0.3
            weighted_sum += max(0.0, min(100.0, inv_score)) * inventory.confidence
            total_weight += inventory.confidence

        if bias.confidence > 0:
            bias_score = NEUTRAL_SCORE + bias.bias_score * 0.3
            weighted_sum += max(0.0, min(100.0, bias_score)) * bias.confidence
            total_weight += bias.confidence

        if total_weight <= 0:
            return NEUTRAL_SCORE

        return weighted_sum / total_weight

    def _evidence_reasons(
        self,
        analysis: DealerPositioningAnalysis,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        if analysis.dealer_side is not DealerSide.UNKNOWN:
            reasons.append(f"Dealer gamma side is {analysis.dealer_side.value}.")
        if analysis.dealer_bias is not DealerBiasLevel.UNKNOWN:
            reasons.append(f"Dealer directional bias is {analysis.dealer_bias.value}.")
        if analysis.hedging_pressure > 0:
            label = self._hedging_label(analysis.hedging_pressure)
            reasons.append(
                f"Hedging pressure is {label} ({analysis.hedging_pressure:.0%})."
            )

        if inventory.reasons:
            for r in inventory.reasons[:2]:
                if r not in reasons:
                    reasons.append(f"[Inventory] {r}")
        if bias.reasons:
            for r in bias.reasons[:2]:
                if r not in reasons:
                    reasons.append(f"[Bias] {r}")

        return tuple(reasons)

    def _hedging_label(self, pressure: float) -> str:
        if pressure >= HEDGING_HIGH_THRESHOLD:
            return "high"
        if pressure >= HEDGING_MODERATE_THRESHOLD:
            return "moderate"
        if pressure >= HEDGING_LOW_THRESHOLD:
            return "low"
        return "minimal"

    def _to_evidence(
        self,
        analysis: DealerPositioningAnalysis,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> Evidence:
        signal = self._evidence_signal(analysis.dealer_bias)
        score = self._evidence_score(inventory, bias)
        confidence = analysis.confidence

        return Evidence(
            source="Dealer Positioning",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis, inventory, bias),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "dealer_side": analysis.dealer_side.value,
                "dealer_bias": analysis.dealer_bias.value,
                "hedging_pressure": analysis.hedging_pressure,
                "inventory_confidence": inventory.confidence,
                "bias_confidence": bias.confidence,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: DealerPositioningAnalysis,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> DealerPositioningExplanation:
        return DealerPositioningExplanation(
            dealer_inventory=self._inventory_section(analysis, inventory),
            dealer_bias=self._bias_section(analysis, bias),
            hedging_pressure=self._hedging_section(analysis),
            institutional_interpretation=self._institutional_section(
                analysis, inventory, bias
            ),
            risk_assessment=self._risk_section(analysis),
        )

    def _inventory_section(
        self,
        analysis: DealerPositioningAnalysis,
        inventory: DealerInventory,
    ) -> str:
        parts: list[str] = ["Dealer Inventory Assessment:"]

        if analysis.dealer_side is DealerSide.LONG_GAMMA:
            parts.append(
                "Dealers are positioned long gamma. Their hedging "
                "activity is expected to dampen directional moves, "
                "creating resistance at extremes."
            )
        elif analysis.dealer_side is DealerSide.SHORT_GAMMA:
            parts.append(
                "Dealers are positioned short gamma. Their hedging "
                "activity is expected to amplify directional moves, "
                "increasing the risk of momentum acceleration."
            )
        elif analysis.dealer_side is DealerSide.NEUTRAL:
            parts.append(
                "Dealer gamma positioning appears balanced. No "
                "significant hedging amplification or damping is "
                "expected from inventory effects alone."
            )
        else:
            parts.append(
                "Dealer gamma positioning cannot be estimated from available data."
            )

        if inventory.reasons:
            parts.append("Key factors: " + "; ".join(inventory.reasons[:3]))

        return " ".join(parts)

    def _bias_section(
        self,
        analysis: DealerPositioningAnalysis,
        bias: DealerBias,
    ) -> str:
        parts: list[str] = ["Dealer Bias Assessment:"]

        if analysis.dealer_bias is DealerBiasLevel.BULLISH:
            parts.append(
                "Dealer positioning suggests a bullish directional "
                "bias. Hedging flows are likely to provide support "
                "on pullbacks."
            )
        elif analysis.dealer_bias is DealerBiasLevel.BEARISH:
            parts.append(
                "Dealer positioning suggests a bearish directional "
                "bias. Hedging flows are likely to create resistance "
                "on rallies."
            )
        elif analysis.dealer_bias is DealerBiasLevel.NEUTRAL:
            parts.append(
                "Dealer directional bias is neutral. No persistent "
                "directional hedging pressure is expected from "
                "current positioning."
            )
        else:
            parts.append(
                "Dealer directional bias cannot be determined from available data."
            )

        if bias.reasons:
            parts.append("Key factors: " + "; ".join(bias.reasons[:3]))

        return " ".join(parts)

    def _hedging_section(self, analysis: DealerPositioningAnalysis) -> str:
        parts: list[str] = ["Likely Hedging Pressure:"]

        label = self._hedging_label(analysis.hedging_pressure)
        parts.append(
            f"Hedging intensity is estimated as {label} "
            f"({analysis.hedging_pressure:.0%})."
        )

        if analysis.hedging_pressure >= HEDGING_HIGH_THRESHOLD:
            parts.append(
                "Elevated hedging activity is expected. Position "
                "sizing should account for potential acceleration "
                "or reversal risks."
            )
        elif analysis.hedging_pressure >= HEDGING_MODERATE_THRESHOLD:
            parts.append(
                "Moderate hedging activity is expected. Monitor "
                "for shifts in dealer positioning that could "
                "amplify or dampen price action."
            )
        elif analysis.hedging_pressure >= HEDGING_LOW_THRESHOLD:
            parts.append(
                "Low hedging activity is expected. Dealer "
                "positioning is unlikely to materially impact "
                "near-term price action."
            )
        else:
            parts.append(
                "Minimal hedging activity is expected. Dealer "
                "flows are unlikely to drive price action."
            )

        return " ".join(parts)

    def _institutional_section(
        self,
        analysis: DealerPositioningAnalysis,
        inventory: DealerInventory,
        bias: DealerBias,
    ) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        if (
            analysis.dealer_side is DealerSide.SHORT_GAMMA
            and analysis.dealer_bias is DealerBiasLevel.BULLISH
        ):
            parts.append(
                "Short gamma with bullish bias suggests dealers are "
                "short puts. A downward move could trigger dealer "
                "hedging that accelerates selling. Monitor downside "
                "break of key support levels."
            )
        elif (
            analysis.dealer_side is DealerSide.SHORT_GAMMA
            and analysis.dealer_bias is DealerBiasLevel.BEARISH
        ):
            parts.append(
                "Short gamma with bearish bias suggests dealers are "
                "short calls. An upward move could trigger dealer "
                "hedging that accelerates buying. Monitor upside "
                "break of key resistance levels."
            )
        elif (
            analysis.dealer_side is DealerSide.LONG_GAMMA
            and analysis.dealer_bias is DealerBiasLevel.BULLISH
        ):
            parts.append(
                "Long gamma with bullish bias suggests dealers are "
                "long calls or have downside protection. They are "
                "positioned for upside and their hedging creates a "
                "stabilizing bid on dips."
            )
        elif (
            analysis.dealer_side is DealerSide.LONG_GAMMA
            and analysis.dealer_bias is DealerBiasLevel.BEARISH
        ):
            parts.append(
                "Long gamma with bearish bias suggests dealers have "
                "upside protection or long puts. Their hedging "
                "dampens upside moves, creating resistance."
            )
        elif (
            analysis.dealer_side is DealerSide.NEUTRAL
            and analysis.dealer_bias is DealerBiasLevel.NEUTRAL
        ):
            parts.append(
                "Both gamma positioning and directional bias are "
                "neutral. Dealer flows are unlikely to be a primary "
                "market driver."
            )
        else:
            parts.append(
                "Mixed signals from inventory and bias analysis. "
                "Cross-reference with other market intelligence "
                "before drawing conclusions."
            )

        if analysis.confidence < 0.3:
            parts.append(
                "Low confidence suggests limited data availability. "
                "Interpret with caution."
            )

        return " ".join(parts)

    def _risk_section(self, analysis: DealerPositioningAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        if analysis.dealer_side is DealerSide.SHORT_GAMMA:
            parts.append(
                "Short gamma positioning increases the risk of "
                "sharp, accelerating moves. Consider position "
                "sizing that accounts for gap risk."
            )

        if analysis.dealer_bias is DealerBiasLevel.UNKNOWN:
            parts.append(
                "Directional bias is unknown. Avoid high-conviction "
                "positioning until dealer intent is clearer."
            )

        if analysis.hedging_pressure >= HEDGING_HIGH_THRESHOLD:
            parts.append(
                "Elevated hedging pressure increases the "
                "probability of dealer-driven flow. Monitor "
                "gamma strikes and adjust exposure accordingly."
            )

        if analysis.confidence < 0.3:
            parts.append(
                "Low institutional confidence. Reduce position "
                "size and consider wider stops."
            )

        if not parts:
            parts.append(
                "No material risk factors identified from dealer positioning data."
            )

        return " ".join(parts)

    def _empty_analysis(self, reason: str) -> DealerPositioningAnalysis:
        analysis = DealerPositioningAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = DealerPositioningExplanation(
            dealer_inventory="Dealer inventory assessment unavailable: no inputs provided.",
            dealer_bias="Dealer bias assessment unavailable: no inputs provided.",
            hedging_pressure="Hedging pressure cannot be estimated: no inputs provided.",
            institutional_interpretation="Institutional Interpretation: Dealer positioning data is unavailable.",
            risk_assessment="Risk Assessment: Dealer positioning data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
