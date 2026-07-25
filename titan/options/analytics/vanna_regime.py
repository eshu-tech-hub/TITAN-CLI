"""Vanna Regime Analyzer.

Determines the net vanna exposure regime from supplied option analytics.
Vanna measures the sensitivity of delta to changes in implied volatility
(or equivalently, vega to changes in underlying price).

No broker imports.
No API calls.
No Vanna estimation — consumes supplied vanna values only.
"""

from numbers import Real
from typing import Any

from titan.options.analytics.models import (
    VannaExposureInput,
    VannaRegime,
    VannaRegimeType,
)

BALANCED_VANNA_THRESHOLD = 1e-8


class VannaRegimeAnalyzer:
    """Analyse net vanna exposure and classify the regime.

    Consumes per-strike vanna values from OptionChainSnapshot and/or
    aggregate Greeks/GEX for fallback regime inference.  Pure analysis
    — does not modify any input model.
    """

    name = "VannaRegimeAnalyzer"

    def analyze(
        self,
        input_data: VannaExposureInput,
    ) -> VannaRegime:
        """Determine the net vanna regime.

        Args:
            input_data: Aggregated vanna exposure inputs.

        Returns:
            Vanna regime assessment.
        """

        net_vanna = self._compute_net_vanna(input_data)
        reasons: list[str] = []
        confidence = 0.0

        if net_vanna is not None:
            regime_type = self._classify(net_vanna)
            confidence = self._confidence_from_vanna(input_data, net_vanna)
            reasons = self._reasons(net_vanna, regime_type, input_data)
        else:
            regime_type = VannaRegimeType.UNKNOWN
            confidence = self._fallback_confidence(input_data)
            reasons = self._fallback_reasons(input_data)
            net_vanna = self._infer_net_vanna(input_data)

        return VannaRegime(
            regime_type=regime_type,
            net_vanna=net_vanna,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _compute_net_vanna(
        self,
        input_data: VannaExposureInput,
    ) -> float | None:
        """Compute net vanna from per-strike data when available."""
        snapshot = input_data.option_chain_snapshot
        if snapshot is None or not snapshot.strikes:
            return None

        total = 0.0
        has_vanna = False

        for strike in snapshot.strikes:
            cv = self._vanna_value(strike.call_vanna)
            pv = self._vanna_value(strike.put_vanna)
            if cv is not None:
                total += cv * strike.call_open_interest
                has_vanna = True
            if pv is not None:
                total += pv * strike.put_open_interest
                has_vanna = True

        return total if has_vanna else None

    def _vanna_value(self, vanna: float | None) -> float | None:
        if vanna is None or not self._valid_number(vanna):
            return None
        return float(vanna)

    def _classify(self, net_vanna: float) -> VannaRegimeType:
        if abs(net_vanna) < BALANCED_VANNA_THRESHOLD:
            return VannaRegimeType.BALANCED
        if net_vanna > 0:
            return VannaRegimeType.POSITIVE
        return VannaRegimeType.NEGATIVE

    def _confidence_from_vanna(
        self,
        input_data: VannaExposureInput,
        net_vanna: float,
    ) -> float:
        score = 0.5

        snapshot = input_data.option_chain_snapshot
        if snapshot is not None:
            total = len(snapshot.strikes)
            available = sum(
                1
                for s in snapshot.strikes
                if s.call_vanna is not None or s.put_vanna is not None
            )
            completeness = available / max(total, 1)
            score += completeness * 0.3

        if abs(net_vanna) > BALANCED_VANNA_THRESHOLD:
            score += 0.1

        return min(1.0, score)

    def _fallback_confidence(
        self,
        input_data: VannaExposureInput,
    ) -> float:
        score = 0.0
        factors = 0

        if input_data.greeks is not None and input_data.greeks.net_gamma is not None:
            score += input_data.greeks.confidence * 0.3
            factors += 1

        if input_data.gamma_exposure is not None:
            score += input_data.gamma_exposure.confidence * 0.3
            factors += 1

        if factors == 0:
            return 0.0

        return min(0.5, score / factors)

    def _infer_net_vanna(
        self,
        input_data: VannaExposureInput,
    ) -> float | None:
        return None

    def _reasons(
        self,
        net_vanna: float,
        regime_type: VannaRegimeType,
        input_data: VannaExposureInput,
    ) -> list[str]:
        reasons: list[str] = []

        if regime_type is VannaRegimeType.POSITIVE:
            reasons.append("Net vanna is positive.")
        elif regime_type is VannaRegimeType.NEGATIVE:
            reasons.append("Net vanna is negative.")
        elif regime_type is VannaRegimeType.BALANCED:
            reasons.append("Net vanna is balanced near zero.")

        if net_vanna is not None:
            reasons.append(f"Net vanna exposure: {net_vanna:.4f}.")

        snapshot = input_data.option_chain_snapshot
        if snapshot is not None and snapshot.strikes:
            reasons.append(f"Vanna computed from {len(snapshot.strikes)} strike(s).")

        return reasons

    def _fallback_reasons(
        self,
        input_data: VannaExposureInput,
    ) -> list[str]:
        reasons: list[str] = []

        if input_data.option_chain_snapshot is None:
            reasons.append("No per-strike vanna data supplied.")
        elif not input_data.option_chain_snapshot.strikes:
            reasons.append("Option chain snapshot has no strikes.")

        if input_data.greeks is not None:
            reasons.append("Falling back to Greeks analysis for context.")

        return reasons

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)
