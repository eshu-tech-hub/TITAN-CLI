"""Dealer directional bias analyzer for the Dealer Positioning Engine.

Estimates the directional bias implied by dealer positioning using
supplied option analytics. No broker imports, no API calls, no order
flow estimation.
"""

from titan.options.analytics.models import (
    DealerBias,
    DealerBiasLevel,
    DealerPositioningInput,
    GreeksAnalysis,
    MarketBias,
    OptionChainAnalysis,
    SurfaceIntelligenceAnalysis,
    SurfaceHealthLevel,
)

BIAS_CONFIDENCE_LOW = 0.15
BIAS_CONFIDENCE_MODERATE = 0.40
BIAS_CONFIDENCE_HIGH = 0.65


class DealerBiasAnalyzer:
    """Estimate dealer directional bias from option analytics.

    Surface intelligence (skew direction, smile regime), option-chain
    bias (bullish/bearish scores), and Greeks (net delta) are combined
    to determine the directional pressure dealer hedging is likely to
    create.
    """

    name = "DealerBiasAnalyzer"

    def analyze(
        self,
        input: DealerPositioningInput,
    ) -> DealerBias:
        if self._insufficient_data(input):
            return DealerBias(
                bias_level=DealerBiasLevel.UNKNOWN,
                bias_score=0.0,
                confidence=0.0,
                reasons=("Insufficient data for bias estimation.",),
                warnings=("Missing required analytics inputs.",),
            )

        surface_signal = self._surface_bias_signal(input.surface)
        chain_signal = self._chain_bias_signal(input.option_chain)
        greeks_signal = self._greeks_bias_signal(input.greeks)

        combined_score = self._combine_signals(
            surface_signal, chain_signal, greeks_signal
        )
        bias_level = self._classify_bias(combined_score)
        confidence = self._calculate_confidence(input)
        reasons = self._build_reasons(
            combined_score, surface_signal, chain_signal, greeks_signal
        )
        warnings = self._collect_warnings(input)

        return DealerBias(
            bias_level=bias_level,
            bias_score=combined_score,
            confidence=confidence,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
        )

    def _insufficient_data(self, input: DealerPositioningInput) -> bool:
        return all(x is None for x in (input.surface, input.option_chain, input.greeks))

    def _surface_bias_signal(
        self,
        surface: SurfaceIntelligenceAnalysis | None,
    ) -> float:
        """Extract directional bias signal from surface intelligence.

        Skew direction is the primary surface-based bias indicator.
        Smile regime provides supporting evidence.
        """
        if surface is None:
            return 0.0

        health = surface.health
        if health in (SurfaceHealthLevel.UNHEALTHY, SurfaceHealthLevel.UNKNOWN):
            return 0.0

        signal = 0.0
        components_used = 0

        for cs in surface.component_scores:
            if not cs.available or cs.signal is None:
                continue

            signal_multiplier = 0.0
            if cs.name == "Skew":
                signal_multiplier = 40.0
            elif cs.name == "Smile":
                signal_multiplier = 25.0
            elif cs.name == "Term Structure":
                signal_multiplier = 15.0
            else:
                continue

            sig = cs.signal
            if sig.value in ("very_bullish", "bullish"):
                signal += signal_multiplier
            elif sig.value in ("very_bearish", "bearish"):
                signal -= signal_multiplier

            components_used += 1

        if components_used == 0:
            return 0.0

        return signal / components_used

    def _chain_bias_signal(
        self,
        option_chain: OptionChainAnalysis | None,
    ) -> float:
        """Extract directional bias signal from option-chain analysis.

        Uses the built-in bullish/bearish scores from the chain
        intelligence engine.
        """
        if option_chain is None:
            return 0.0

        bullish = option_chain.bullish_score
        bearish = option_chain.bearish_score

        net_score = bullish - bearish

        if abs(net_score) < 5.0:
            return 0.0

        return max(-50.0, min(50.0, net_score * 0.5))

    def _greeks_bias_signal(
        self,
        greeks: GreeksAnalysis | None,
    ) -> float:
        """Extract directional bias signal from Greeks analysis.

        Net delta provides a directional signal. Market bias from the
        greeks analysis contributes supporting evidence.
        """
        if greeks is None:
            return 0.0

        signal = 0.0
        components_used = 0

        if greeks.net_delta is not None:
            signal += max(-30.0, min(30.0, greeks.net_delta * 100.0))
            components_used += 1

        if greeks.average_delta is not None:
            signal += max(-20.0, min(20.0, greeks.average_delta * 100.0))
            components_used += 1

        if greeks.overall_bias is MarketBias.BULLISH:
            signal += 15.0
            components_used += 1
        elif greeks.overall_bias is MarketBias.BEARISH:
            signal -= 15.0
            components_used += 1

        if components_used == 0:
            return 0.0

        return signal / components_used

    def _combine_signals(
        self,
        surface_signal: float,
        chain_signal: float,
        greeks_signal: float,
    ) -> float:
        return max(-100.0, min(100.0, surface_signal + chain_signal + greeks_signal))

    def _classify_bias(self, combined_score: float) -> DealerBiasLevel:
        if combined_score >= 20.0:
            return DealerBiasLevel.BULLISH
        if combined_score <= -20.0:
            return DealerBiasLevel.BEARISH
        return DealerBiasLevel.NEUTRAL

    def _calculate_confidence(
        self,
        input: DealerPositioningInput,
    ) -> float:
        sources = 0

        if input.surface is not None:
            sources += 1
        if input.option_chain is not None:
            sources += 1
        if input.greeks is not None:
            sources += 1

        if sources == 0:
            return 0.0

        return {
            3: BIAS_CONFIDENCE_HIGH,
            2: BIAS_CONFIDENCE_MODERATE,
            1: BIAS_CONFIDENCE_LOW,
        }.get(sources, 0.0)

    def _build_reasons(
        self,
        combined_score: float,
        surface_signal: float,
        chain_signal: float,
        greeks_signal: float,
    ) -> list[str]:
        reasons: list[str] = []

        if combined_score >= 30.0:
            reasons.append("Dealer directional bias is bullish.")
        elif combined_score <= -30.0:
            reasons.append("Dealer directional bias is bearish.")
        else:
            reasons.append("Dealer directional bias is neutral.")

        if surface_signal != 0.0:
            direction = "bullish" if surface_signal > 0 else "bearish"
            reasons.append(
                f"Surface-based bias signal is {direction} ({surface_signal:+.1f})."
            )

        if chain_signal != 0.0:
            direction = "bullish" if chain_signal > 0 else "bearish"
            reasons.append(
                f"Option-chain bias signal is {direction} ({chain_signal:+.1f})."
            )

        if greeks_signal != 0.0:
            direction = "bullish" if greeks_signal > 0 else "bearish"
            reasons.append(
                f"Greeks-based bias signal is {direction} ({greeks_signal:+.1f})."
            )

        return reasons

    def _collect_warnings(
        self,
        input: DealerPositioningInput,
    ) -> list[str]:
        warnings: list[str] = []

        if input.surface is None:
            warnings.append("Surface intelligence not available for bias estimate.")
        if input.option_chain is None:
            warnings.append("Option chain analysis not available for bias estimate.")
        if input.greeks is None:
            warnings.append("Greeks analysis not available for bias estimate.")

        return warnings

    def extract_bias_evidence(
        self,
        bias: DealerBias,
    ) -> dict | None:
        """Extract structured evidence from bias for explanation."""
        if bias.bias_level is DealerBiasLevel.UNKNOWN:
            return None
        return {
            "bias": bias.bias_level.value,
            "score": bias.bias_score,
            "confidence": bias.confidence,
        }
