"""Vanna Pressure Analyzer.

Assesses the intensity of vanna-driven dealer hedging pressure from
supplied option analytics.

Vanna pressure captures how dealers are expected to respond to changes
in implied volatility (volatility-driven hedging) and underlying price
(price-driven hedging).

No broker imports.
No API calls.
No Vanna estimation — consumes supplied analytics only.
"""

from titan.options.analytics.models import (
    GammaRegime,
    VannaExposureInput,
    VannaPressure,
    VannaPressureLevel,
    VannaRegime,
    VannaRegimeType,
)

PRESSURE_LOW_THRESHOLD = 0.25
PRESSURE_MEDIUM_THRESHOLD = 0.45
PRESSURE_HIGH_THRESHOLD = 0.7


class VannaPressureAnalyzer:
    """Assess vanna-driven dealer hedging pressure.

    Evaluates dealer sensitivity to IV changes (volatility-driven
    hedging) and to price changes (price-driven hedging) based on
    the vanna regime, gamma exposure, and broader positioning context.
    """

    name = "VannaPressureAnalyzer"

    def analyze(
        self,
        input_data: VannaExposureInput,
        regime: VannaRegime,
    ) -> VannaPressure:
        """Assess vanna-driven hedging pressure.

        Args:
            input_data: Aggregated vanna exposure inputs.
            regime: Vanna regime assessment from VannaRegimeAnalyzer.

        Returns:
            Vanna pressure assessment.
        """

        iv_sensitivity = self._iv_sensitivity(input_data, regime)
        price_sensitivity = self._price_sensitivity(input_data, regime)
        pressure_level = self._pressure_level(iv_sensitivity, price_sensitivity)
        dealer_response = self._dealer_response(
            regime, iv_sensitivity, price_sensitivity
        )
        confidence = self._confidence(input_data, regime)
        reasons = self._reasons(regime, iv_sensitivity, price_sensitivity, input_data)

        return VannaPressure(
            pressure_level=pressure_level,
            dealer_response=dealer_response,
            iv_sensitivity=iv_sensitivity,
            price_sensitivity=price_sensitivity,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _iv_sensitivity(
        self,
        input_data: VannaExposureInput,
        regime: VannaRegime,
    ) -> float:
        """Estimate dealer sensitivity to IV changes (0-1).

        Higher when vanna regime is strongly positive or negative
        and when gamma regime amplifies the effect.
        """
        score = 0.0
        factors = 0

        if (
            regime.regime_type is VannaRegimeType.POSITIVE
            or regime.regime_type is VannaRegimeType.NEGATIVE
        ):
            score += 0.6
            factors += 1
        elif regime.regime_type is VannaRegimeType.BALANCED:
            score += 0.2
            factors += 1

        gex = input_data.gamma_exposure
        if gex is not None and gex.gamma_regime is GammaRegime.NEGATIVE:
            score += 0.2
            factors += 1
        elif gex is not None and gex.gamma_regime is GammaRegime.POSITIVE:
            score += 0.1
            factors += 1

        if regime.confidence > 0.5:
            score += 0.1
            factors += 1

        if factors == 0:
            return 0.0

        return min(1.0, score / factors)

    def _price_sensitivity(
        self,
        input_data: VannaExposureInput,
        regime: VannaRegime,
    ) -> float:
        """Estimate dealer sensitivity to price changes (0-1).

        Higher when gamma exposure indicates amplification (short
        gamma) and vanna regime compounds the effect.
        """
        score = 0.0
        factors = 0

        gex = input_data.gamma_exposure
        if gex is not None and gex.gamma_regime is GammaRegime.NEGATIVE:
            score += 0.6
            factors += 1
        elif gex is not None and gex.gamma_regime is GammaRegime.POSITIVE:
            score += 0.2
            factors += 1

        if regime.regime_type in (
            VannaRegimeType.POSITIVE,
            VannaRegimeType.NEGATIVE,
        ):
            score += 0.3
            factors += 1

        dp = input_data.dealer_positioning
        if dp is not None and dp.hedging_pressure > 0.5:
            score += 0.2
            factors += 1

        if factors == 0:
            return 0.0

        return min(1.0, score / factors)

    def _pressure_level(
        self,
        iv_sensitivity: float,
        price_sensitivity: float,
    ) -> VannaPressureLevel:
        combined = (iv_sensitivity + price_sensitivity) / 2.0

        if combined >= PRESSURE_HIGH_THRESHOLD:
            return VannaPressureLevel.EXTREME
        if combined >= PRESSURE_MEDIUM_THRESHOLD:
            return VannaPressureLevel.HIGH
        if combined >= PRESSURE_LOW_THRESHOLD:
            return VannaPressureLevel.MEDIUM
        return VannaPressureLevel.LOW

    def _dealer_response(
        self,
        regime: VannaRegime,
        iv_sensitivity: float,
        price_sensitivity: float,
    ) -> str:
        parts: list[str] = []

        if regime.regime_type is VannaRegimeType.POSITIVE:
            parts.append(
                "Positive vanna: dealers are positioned such that "
                "rising IV increases their delta, requiring additional "
                "hedge selling. Falling IV reduces delta, requiring "
                "hedge buying."
            )
        elif regime.regime_type is VannaRegimeType.NEGATIVE:
            parts.append(
                "Negative vanna: dealers are positioned such that "
                "rising IV decreases their delta, requiring additional "
                "hedge buying. Falling IV increases delta, requiring "
                "hedge selling."
            )
        elif regime.regime_type is VannaRegimeType.BALANCED:
            parts.append(
                "Vanna exposure is balanced. Dealer delta is "
                "relatively insensitive to IV changes."
            )
        else:
            parts.append("Vanna exposure cannot be determined from available data.")

        if iv_sensitivity >= 0.5:
            parts.append("IV-driven hedging pressure is elevated.")
        if price_sensitivity >= 0.5:
            parts.append("Price-driven hedging pressure is elevated.")

        return " ".join(parts)

    def _confidence(
        self,
        input_data: VannaExposureInput,
        regime: VannaRegime,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if regime.confidence > 0:
            confidences.append(regime.confidence)
            weights.append(0.4)

        if input_data.gamma_exposure is not None:
            confidences.append(input_data.gamma_exposure.confidence)
            weights.append(0.3)

        if input_data.dealer_positioning is not None:
            confidences.append(input_data.dealer_positioning.confidence)
            weights.append(0.2)

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
        regime: VannaRegime,
        iv_sensitivity: float,
        price_sensitivity: float,
        input_data: VannaExposureInput,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Vanna regime is {regime.regime_type.value}.")
        reasons.append(
            f"IV sensitivity: {iv_sensitivity:.2f}, "
            f"price sensitivity: {price_sensitivity:.2f}."
        )

        if input_data.gamma_exposure is not None:
            reasons.append(
                f"Gamma regime: {input_data.gamma_exposure.gamma_regime.value}."
            )

        return reasons
