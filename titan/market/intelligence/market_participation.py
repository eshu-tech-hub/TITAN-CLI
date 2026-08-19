"""Market Participation Analyzer.

Analyses the quality of market participation and detects breadth-price
divergence.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import (
    MarketBreadthSnapshot,
    MarketParticipation,
)

MIN_SYMBOLS = 5
HEALTHY_PARTICIPATION = 0.8
WEAK_PARTICIPATION = 0.5
INTERNAL_STRENGTH_AD = 1.5
INTERNAL_WEAKNESS_AD = 0.67


class MarketParticipationAnalyzer:
    """Analyse market participation quality and breadth divergence.

    Consumes MarketBreadthSnapshot to evaluate whether the broad
    market confirms or diverges from index price action.
    """

    name = "MarketParticipationAnalyzer"

    def analyze(
        self,
        snapshot: MarketBreadthSnapshot,
    ) -> MarketParticipation:
        """Evaluate participation quality and detect divergence.

        Args:
            snapshot: Market breadth snapshot.

        Returns:
            Market participation assessment.
        """

        reasons: list[str] = []

        if snapshot.total_symbols < MIN_SYMBOLS:
            return MarketParticipation(
                confidence=0.0,
                reasons=(
                    (f"Insufficient data: need at least {MIN_SYMBOLS} "
                    f"symbols, got {snapshot.total_symbols}."),
                ),
            )

        participating = snapshot.advances + snapshot.declines
        participation_ratio = (
            participating / snapshot.total_symbols
            if snapshot.total_symbols > 0
            else 1.0
        )

        ad_ratio = (
            snapshot.advances / snapshot.declines
            if snapshot.declines > 0
            else float(snapshot.advances or 1)
        )

        internal_strength = (
            participation_ratio >= HEALTHY_PARTICIPATION
            and ad_ratio >= INTERNAL_STRENGTH_AD
        )

        internal_weakness = (
            participation_ratio < WEAK_PARTICIPATION or ad_ratio <= INTERNAL_WEAKNESS_AD
        )

        divergence = self._divergence(participation_ratio, ad_ratio, snapshot)

        confidence = self._confidence(snapshot, participation_ratio)

        reasons.extend(
            self._reasons(
                participation_ratio=participation_ratio,
                internal_strength=internal_strength,
                internal_weakness=internal_weakness,
                divergence=divergence,
            )
        )

        return MarketParticipation(
            participation_ratio=participation_ratio,
            internal_strength=internal_strength,
            internal_weakness=internal_weakness,
            divergence_detected=divergence,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _divergence(
        self,
        participation_ratio: float,
        ad_ratio: float,
        snapshot: MarketBreadthSnapshot,
    ) -> bool:
        if snapshot.total_symbols < MIN_SYMBOLS:
            return False

        narrow_participation = (
            participation_ratio < HEALTHY_PARTICIPATION and ad_ratio > 1.5
        )
        skewed_breadth = participation_ratio >= HEALTHY_PARTICIPATION and (
            ad_ratio <= 0.5 or ad_ratio >= 3.0
        )

        return narrow_participation or skewed_breadth

    def _confidence(
        self,
        snapshot: MarketBreadthSnapshot,
        participation_ratio: float,
    ) -> float:
        sample_factor = min(1.0, snapshot.total_symbols / 50)
        if abs(participation_ratio - 1.0) > 0.15:
            signal = 0.7
        else:
            signal = 0.3
        return min(1.0, sample_factor * (0.3 + 0.7 * signal))

    def _reasons(
        self,
        participation_ratio: float,
        internal_strength: bool,
        internal_weakness: bool,
        divergence: bool,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(
            f"Participation ratio is {participation_ratio:.2f} "
            f"({participation_ratio * 100:.0f}% of symbols active)."
        )

        if internal_strength:
            reasons.append(
                "Internal strength detected — broad participation with advancing bias."
            )
        elif internal_weakness:
            reasons.append(
                "Internal weakness detected — narrow or skewed participation."
            )

        if divergence:
            reasons.append(
                "Breadth divergence detected — market internals "
                "may not confirm price action."
            )

        return reasons
