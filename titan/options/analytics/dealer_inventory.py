"""Dealer inventory bias analyzer for the Dealer Positioning Engine.

Estimates whether dealers are net long gamma, net short gamma, or neutral
using supplied option analytics. No broker imports, no API calls, no
order flow estimation.
"""

from titan.options.analytics.models import (
    DealerInventory,
    DealerPositioningInput,
    DealerSide,
    GreeksAnalysis,
    OptionChainAnalysis,
    SurfaceIntelligenceAnalysis,
    SurfaceHealthLevel,
)

INVENTORY_CONFIDENCE_LOW = 0.15
INVENTORY_CONFIDENCE_MODERATE = 0.40
INVENTORY_CONFIDENCE_HIGH = 0.65


class DealerInventoryAnalyzer:
    """Estimate dealer inventory (gamma) positioning from option analytics.

    Uses Greeks (net gamma), volatility surface health (smile convexity,
    skew steepness, IV level), and option-chain OI concentration to
    infer whether dealers are long gamma, short gamma, or neutral.
    """

    name = "DealerInventoryAnalyzer"

    def analyze(
        self,
        input: DealerPositioningInput,
    ) -> DealerInventory:
        if self._insufficient_data(input):
            return DealerInventory(
                dealer_side=DealerSide.UNKNOWN,
                inventory_score=0.0,
                confidence=0.0,
                reasons=("Insufficient data for inventory estimation.",),
                warnings=("Missing required analytics inputs.",),
            )

        gamma_signal = self._gamma_signal(input.greeks)
        surface_signal = self._surface_inventory_signal(input.surface)
        oi_signal = self._oi_inventory_signal(input.option_chain)

        combined_score = self._combine_signals(gamma_signal, surface_signal, oi_signal)
        dealer_side = self._classify_side(combined_score)
        confidence = self._calculate_confidence(input, gamma_signal, oi_signal)
        reasons = self._build_reasons(
            combined_score, gamma_signal, surface_signal, oi_signal
        )
        warnings = self._collect_warnings(input)

        return DealerInventory(
            dealer_side=dealer_side,
            inventory_score=combined_score,
            confidence=confidence,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
        )

    def _insufficient_data(self, input: DealerPositioningInput) -> bool:
        return all(x is None for x in (input.greeks, input.surface, input.option_chain))

    def _gamma_signal(self, greeks: GreeksAnalysis | None) -> float:
        """Extract gamma positioning signal from Greeks analysis.

        Returns a value from -100 (strong short gamma) to +100 (strong
        long gamma). Zero if data is unavailable.
        """
        if greeks is None or greeks.net_gamma is None:
            return 0.0

        net_gamma = greeks.net_gamma
        threshold = 0.001

        if net_gamma > threshold:
            return 50.0 * min(1.0, net_gamma / (threshold * 10))
        if net_gamma < -threshold:
            return -50.0 * min(1.0, abs(net_gamma) / (threshold * 10))

        return 0.0

    def _surface_inventory_signal(
        self,
        surface: SurfaceIntelligenceAnalysis | None,
    ) -> float:
        """Extract inventory signal from surface intelligence.

        Rich surface conditions (strong smile, steep skew, high IV)
        suggest dealers are short premium → short gamma.
        """
        if surface is None:
            return 0.0

        health = surface.health
        if health in (SurfaceHealthLevel.UNHEALTHY, SurfaceHealthLevel.UNKNOWN):
            return 0.0

        signal = 0.0
        components_used = 0

        for cs in surface.component_scores:
            if not cs.available:
                continue
            if cs.name == "Smile" and cs.signal is not None:
                sig = cs.signal
                if sig.value in ("very_bullish", "bullish"):
                    signal -= 30.0
                elif sig.value in ("very_bearish", "bearish"):
                    signal += 30.0
                components_used += 1
            elif cs.name == "Skew" and cs.signal is not None:
                sig = cs.signal
                if sig.value in ("very_bullish", "bullish"):
                    signal -= 20.0
                elif sig.value in ("very_bearish", "bearish"):
                    signal += 20.0
                components_used += 1
            elif cs.name == "Volatility" and cs.signal is not None:
                sig = cs.signal
                if sig.value in ("very_bullish", "bullish"):
                    signal -= 15.0
                elif sig.value in ("very_bearish", "bearish"):
                    signal += 15.0
                components_used += 1

        if components_used == 0:
            return 0.0

        return signal / components_used

    def _oi_inventory_signal(
        self,
        option_chain: OptionChainAnalysis | None,
    ) -> float:
        """Extract inventory signal from option-chain OI data.

        Heavy OI concentration at out-of-the-money strikes suggests
        dealer short premium positioning.
        """
        if option_chain is None:
            return 0.0

        if option_chain.bullish_score > 60.0 and option_chain.bearish_score < 40.0:
            return -25.0
        if option_chain.bearish_score > 60.0 and option_chain.bullish_score < 40.0:
            return 25.0

        return 0.0

    def _combine_signals(
        self,
        gamma_signal: float,
        surface_signal: float,
        oi_signal: float,
    ) -> float:
        return max(-100.0, min(100.0, gamma_signal + surface_signal + oi_signal))

    def _classify_side(self, combined_score: float) -> DealerSide:
        if combined_score >= 20.0:
            return DealerSide.LONG_GAMMA
        if combined_score <= -20.0:
            return DealerSide.SHORT_GAMMA
        return DealerSide.NEUTRAL

    def _calculate_confidence(
        self,
        input: DealerPositioningInput,
        gamma_signal: float,
        oi_signal: float,
    ) -> float:
        sources = 0

        if input.greeks is not None and input.greeks.net_gamma is not None:
            sources += 1
        if input.surface is not None:
            sources += 1
        if input.option_chain is not None:
            sources += 1

        if sources == 0:
            return 0.0

        base_confidence = {
            3: INVENTORY_CONFIDENCE_HIGH,
            2: INVENTORY_CONFIDENCE_MODERATE,
            1: INVENTORY_CONFIDENCE_LOW,
        }.get(sources, 0.0)

        if gamma_signal == 0.0 and oi_signal == 0.0:
            base_confidence *= 0.5

        return base_confidence

    def _build_reasons(
        self,
        combined_score: float,
        gamma_signal: float,
        surface_signal: float,
        oi_signal: float,
    ) -> list[str]:
        reasons: list[str] = []

        if combined_score >= 30.0:
            reasons.append("Dealer gamma positioning is long.")
        elif combined_score <= -30.0:
            reasons.append("Dealer gamma positioning is short.")
        else:
            reasons.append("Dealer gamma positioning is neutral.")

        if gamma_signal != 0.0:
            direction = "positive" if gamma_signal > 0 else "negative"
            reasons.append(f"Net gamma signal is {direction} ({gamma_signal:+.1f}).")

        if surface_signal != 0.0:
            direction = "positive" if surface_signal > 0 else "negative"
            reasons.append(
                f"Surface-based inventory signal is {direction} ({surface_signal:+.1f})."
            )

        if oi_signal != 0.0:
            direction = "positive" if oi_signal > 0 else "negative"
            reasons.append(
                f"OI-based inventory signal is {direction} ({oi_signal:+.1f})."
            )

        return reasons

    def _collect_warnings(
        self,
        input: DealerPositioningInput,
    ) -> list[str]:
        warnings: list[str] = []

        if input.greeks is None:
            warnings.append("Greeks analysis not available for inventory estimate.")
        if input.surface is None:
            warnings.append(
                "Surface intelligence not available for inventory estimate."
            )
        if input.option_chain is None:
            warnings.append(
                "Option chain analysis not available for inventory estimate."
            )

        return warnings

    def extract_inventory_evidence(
        self,
        inventory: DealerInventory,
    ) -> dict | None:
        """Extract structured evidence from inventory for explanation."""
        if inventory.dealer_side is DealerSide.UNKNOWN:
            return None
        return {
            "side": inventory.dealer_side.value,
            "score": inventory.inventory_score,
            "confidence": inventory.confidence,
        }
