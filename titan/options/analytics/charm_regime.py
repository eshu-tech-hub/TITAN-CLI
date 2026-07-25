"""Charm Regime Analyzer.

Determines the net charm exposure regime from supplied option analytics.
Charm measures the rate of change of Delta with respect to time (dDelta/dt).

No broker imports.
No API calls.
No Charm estimation — consumes supplied charm values only.
"""

from numbers import Real
from typing import Any

from titan.options.analytics.models import (
    CharmExposureInput,
    CharmRegime,
    CharmRegimeType,
)

BALANCED_CHARM_THRESHOLD = 1e-8


class CharmRegimeAnalyzer:
    """Analyse net charm exposure and classify the regime.

    Consumes per-strike charm values from OptionChainSnapshot.
    Pure analysis — does not modify any input model.
    """

    name = "CharmRegimeAnalyzer"

    def analyze(
        self,
        input_data: CharmExposureInput,
    ) -> CharmRegime:
        """Determine the net charm regime.

        Args:
            input_data: Aggregated charm exposure inputs.

        Returns:
            Charm regime assessment.
        """

        net_charm = self._compute_net_charm(input_data)
        reasons: list[str] = []
        confidence = 0.0

        if net_charm is not None:
            regime_type = self._classify(net_charm)
            confidence = self._confidence_from_charm(input_data, net_charm)
            reasons = self._reasons(net_charm, regime_type, input_data)
        else:
            regime_type = CharmRegimeType.UNKNOWN
            confidence = self._fallback_confidence(input_data)
            reasons = self._fallback_reasons(input_data)
            net_charm = self._infer_net_charm(input_data)

        return CharmRegime(
            regime_type=regime_type,
            net_charm=net_charm,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _compute_net_charm(
        self,
        input_data: CharmExposureInput,
    ) -> float | None:
        """Compute net charm from per-strike data when available."""
        snapshot = input_data.option_chain_snapshot
        if snapshot is None or not snapshot.strikes:
            return None

        total = 0.0
        has_charm = False

        for strike in snapshot.strikes:
            cc = self._charm_value(strike.call_charm)
            pc = self._charm_value(strike.put_charm)
            if cc is not None:
                total += cc * strike.call_open_interest
                has_charm = True
            if pc is not None:
                total += pc * strike.put_open_interest
                has_charm = True

        return total if has_charm else None

    def _charm_value(self, charm: float | None) -> float | None:
        if charm is None or not self._valid_number(charm):
            return None
        return float(charm)

    def _classify(self, net_charm: float) -> CharmRegimeType:
        if abs(net_charm) < BALANCED_CHARM_THRESHOLD:
            return CharmRegimeType.BALANCED
        if net_charm > 0:
            return CharmRegimeType.POSITIVE
        return CharmRegimeType.NEGATIVE

    def _confidence_from_charm(
        self,
        input_data: CharmExposureInput,
        net_charm: float,
    ) -> float:
        score = 0.5

        snapshot = input_data.option_chain_snapshot
        if snapshot is not None:
            total = len(snapshot.strikes)
            available = sum(
                1
                for s in snapshot.strikes
                if s.call_charm is not None or s.put_charm is not None
            )
            completeness = available / max(total, 1)
            score += completeness * 0.3

        if abs(net_charm) > BALANCED_CHARM_THRESHOLD:
            score += 0.1

        return min(1.0, score)

    def _fallback_confidence(
        self,
        input_data: CharmExposureInput,
    ) -> float:
        score = 0.0
        factors = 0

        if input_data.greeks is not None and input_data.greeks.net_gamma is not None:
            score += input_data.greeks.confidence * 0.3
            factors += 1

        if input_data.gamma_exposure is not None:
            score += input_data.gamma_exposure.confidence * 0.3
            factors += 1

        if input_data.vanna_exposure is not None:
            score += input_data.vanna_exposure.confidence * 0.3
            factors += 1

        if factors == 0:
            return 0.0

        return min(0.5, score / factors)

    def _infer_net_charm(
        self,
        input_data: CharmExposureInput,
    ) -> float | None:
        return None

    def _reasons(
        self,
        net_charm: float,
        regime_type: CharmRegimeType,
        input_data: CharmExposureInput,
    ) -> list[str]:
        reasons: list[str] = []

        if regime_type is CharmRegimeType.POSITIVE:
            reasons.append("Net charm is positive.")
        elif regime_type is CharmRegimeType.NEGATIVE:
            reasons.append("Net charm is negative.")
        elif regime_type is CharmRegimeType.BALANCED:
            reasons.append("Net charm is balanced near zero.")

        if net_charm is not None:
            reasons.append(f"Net charm exposure: {net_charm:.4f}.")

        snapshot = input_data.option_chain_snapshot
        if snapshot is not None and snapshot.strikes:
            reasons.append(f"Charm computed from {len(snapshot.strikes)} strike(s).")

        return reasons

    def _fallback_reasons(
        self,
        input_data: CharmExposureInput,
    ) -> list[str]:
        reasons: list[str] = []

        if input_data.option_chain_snapshot is None:
            reasons.append("No per-strike charm data supplied.")
        elif not input_data.option_chain_snapshot.strikes:
            reasons.append("Option chain snapshot has no strikes.")

        if input_data.greeks is not None:
            reasons.append("Falling back to Greeks analysis for context.")

        return reasons

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)
