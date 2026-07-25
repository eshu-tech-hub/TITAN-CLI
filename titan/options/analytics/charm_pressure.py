"""Charm Pressure Analyzer.

Assesses the intensity of charm-driven dealer delta decay hedging
pressure from supplied option analytics.

Charm pressure captures how dealers must rebalance delta as time
passes and options approach expiry.

No broker imports.
No API calls.
No Charm estimation — consumes supplied analytics only.
"""

from titan.options.analytics.models import (
    CharmExposureInput,
    CharmPressure,
    CharmPressureLevel,
    CharmRegime,
    CharmRegimeType,
    GammaRegime,
)

PRESSURE_LOW_THRESHOLD = 0.25
PRESSURE_MEDIUM_THRESHOLD = 0.45
PRESSURE_HIGH_THRESHOLD = 0.7

NEAR_EXPIRY_DAYS = 7


class CharmPressureAnalyzer:
    """Assess charm-driven dealer delta decay hedging pressure.

    Evaluates how dealers must adjust delta hedges as time passes
    (time-driven hedging) based on the charm regime, gamma exposure,
    vanna context, proximity to expiry, and broader positioning.
    """

    name = "CharmPressureAnalyzer"

    def analyze(
        self,
        input_data: CharmExposureInput,
        regime: CharmRegime,
    ) -> CharmPressure:
        """Assess charm-driven hedging pressure.

        Args:
            input_data: Aggregated charm exposure inputs.
            regime: Charm regime assessment from CharmRegimeAnalyzer.

        Returns:
            Charm pressure assessment.
        """

        time_sensitivity = self._time_sensitivity(input_data, regime)
        near_expiry_risk = self._near_expiry_risk(input_data, regime)
        pressure_level = self._pressure_level(time_sensitivity, near_expiry_risk)
        dealer_response = self._dealer_response(
            regime, time_sensitivity, near_expiry_risk
        )
        confidence = self._confidence(input_data, regime)
        reasons = self._reasons(regime, time_sensitivity, near_expiry_risk, input_data)

        return CharmPressure(
            pressure_level=pressure_level,
            dealer_response=dealer_response,
            time_sensitivity=time_sensitivity,
            near_expiry_risk=near_expiry_risk,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _time_sensitivity(
        self,
        input_data: CharmExposureInput,
        regime: CharmRegime,
    ) -> float:
        """Estimate dealer sensitivity to time decay (0-1).

        Higher when charm regime is strongly positive or negative
        and when gamma regime amplifies the delta-decay effect.
        """
        score = 0.0
        factors = 0

        if regime.regime_type is CharmRegimeType.POSITIVE:
            score += 0.5
            factors += 1
        elif regime.regime_type is CharmRegimeType.NEGATIVE:
            score += 0.5
            factors += 1
        elif regime.regime_type is CharmRegimeType.BALANCED:
            score += 0.1
            factors += 1

        gex = input_data.gamma_exposure
        if gex is not None and gex.gamma_regime is GammaRegime.NEGATIVE:
            score += 0.2
            factors += 1
        elif gex is not None and gex.gamma_regime is GammaRegime.POSITIVE:
            score += 0.1
            factors += 1

        if input_data.vanna_exposure is not None:
            score += 0.1
            factors += 1

        if regime.confidence > 0.5:
            score += 0.1
            factors += 1

        if factors == 0:
            return 0.0

        return min(1.0, score / factors)

    def _near_expiry_risk(
        self,
        input_data: CharmExposureInput,
        regime: CharmRegime,
    ) -> bool:
        """Determine if near-expiry charm risk is elevated.

        Risk is elevated when:
        - Expiry is within NEAR_EXPIRY_DAYS
        - Charm regime is not UNKNOWN or BALANCED
        """
        if regime.regime_type in (CharmRegimeType.UNKNOWN, CharmRegimeType.BALANCED):
            return False

        snapshot = input_data.option_chain_snapshot
        if snapshot is None or snapshot.expiry is None or snapshot.timestamp is None:
            return False

        days_to_expiry = (snapshot.expiry - snapshot.timestamp).days
        if days_to_expiry < 0:
            return False

        return days_to_expiry <= NEAR_EXPIRY_DAYS

    def _pressure_level(
        self,
        time_sensitivity: float,
        near_expiry_risk: bool,
    ) -> CharmPressureLevel:
        if near_expiry_risk:
            boost = 0.2
        else:
            boost = 0.0

        combined = time_sensitivity + boost

        if combined >= PRESSURE_HIGH_THRESHOLD:
            return CharmPressureLevel.EXTREME
        if combined >= PRESSURE_MEDIUM_THRESHOLD:
            return CharmPressureLevel.HIGH
        if combined >= PRESSURE_LOW_THRESHOLD:
            return CharmPressureLevel.MEDIUM
        return CharmPressureLevel.LOW

    def _dealer_response(
        self,
        regime: CharmRegime,
        time_sensitivity: float,
        near_expiry_risk: bool,
    ) -> str:
        parts: list[str] = []

        if regime.regime_type is CharmRegimeType.POSITIVE:
            parts.append(
                "Positive charm: dealer delta increases with time, "
                "requiring dealers to buy delta to maintain hedges."
            )
        elif regime.regime_type is CharmRegimeType.NEGATIVE:
            parts.append(
                "Negative charm: dealer delta decays with time, "
                "requiring dealers to sell delta to maintain hedges."
            )
        elif regime.regime_type is CharmRegimeType.BALANCED:
            parts.append(
                "Charm exposure is balanced. Dealer delta is "
                "relatively stable with respect to time decay."
            )
        else:
            parts.append("Charm exposure cannot be determined from available data.")

        if time_sensitivity >= 0.5:
            parts.append("Time-driven delta decay pressure is elevated.")

        if near_expiry_risk:
            parts.append(
                "Near-expiry charm risk is elevated — delta decay "
                "accelerates as expiry approaches."
            )

        return " ".join(parts)

    def _confidence(
        self,
        input_data: CharmExposureInput,
        regime: CharmRegime,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if regime.confidence > 0:
            confidences.append(regime.confidence)
            weights.append(0.35)

        if input_data.gamma_exposure is not None:
            confidences.append(input_data.gamma_exposure.confidence)
            weights.append(0.25)

        if input_data.vanna_exposure is not None:
            confidences.append(input_data.vanna_exposure.confidence)
            weights.append(0.2)

        if input_data.dealer_positioning is not None:
            confidences.append(input_data.dealer_positioning.confidence)
            weights.append(0.1)

        if input_data.greeks is not None:
            confidences.append(input_data.greeks.confidence)
            weights.append(0.1)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    def _reasons(
        self,
        regime: CharmRegime,
        time_sensitivity: float,
        near_expiry_risk: bool,
        input_data: CharmExposureInput,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Charm regime is {regime.regime_type.value}.")
        reasons.append(f"Time sensitivity: {time_sensitivity:.2f}.")

        if near_expiry_risk:
            reasons.append("Near-expiry charm risk is elevated.")

        if input_data.gamma_exposure is not None:
            reasons.append(
                f"Gamma regime: {input_data.gamma_exposure.gamma_regime.value}."
            )

        if input_data.vanna_exposure is not None:
            reasons.append(
                f"Vanna regime: {input_data.vanna_exposure.regime.regime_type.value}."
            )

        return reasons
