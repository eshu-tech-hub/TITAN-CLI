"""Advance / Decline Analyzer.

Analyses the ratio and dominance of advancing versus declining
symbols in a market or index.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import (
    AdvanceDecline,
    BreadthStrength,
    MarketBreadthSnapshot,
)

MIN_SYMBOLS = 5

VERY_STRONG_AD = 3.0
STRONG_AD = 1.5
WEAK_AD = 0.67
VERY_WEAK_AD = 0.33
DOMINANCE_THRESHOLD = 2.0


class AdvanceDeclineAnalyzer:
    """Analyse advance/decline ratio and breadth strength.

    Consumes MarketBreadthSnapshot to evaluate whether advances or
    declines dominate and classify the overall breadth strength.
    """

    name = "AdvanceDeclineAnalyzer"

    def analyze(
        self,
        snapshot: MarketBreadthSnapshot,
    ) -> AdvanceDecline:
        """Compute advance/decline ratio and breadth strength.

        Args:
            snapshot: Market breadth snapshot.

        Returns:
            Advance/decline assessment.
        """

        reasons: list[str] = []

        if snapshot.total_symbols < MIN_SYMBOLS:
            return AdvanceDecline(
                confidence=0.0,
                reasons=(
                    f"Insufficient data: need at least {MIN_SYMBOLS} "
                    f"symbols, got {snapshot.total_symbols}.",
                ),
            )

        ad_ratio = self._ad_ratio(snapshot)
        advance_pct = self._advance_percentage(snapshot)
        decline_pct = self._decline_percentage(snapshot)

        advance_dom = (
            advance_pct >= DOMINANCE_THRESHOLD * decline_pct
            if decline_pct > 0
            else True
        )
        decline_dom = (
            decline_pct >= DOMINANCE_THRESHOLD * advance_pct
            if advance_pct > 0
            else True
        )

        breadth_strength = self._breadth_strength(ad_ratio)
        confidence = self._confidence(snapshot, ad_ratio)

        reasons.extend(
            self._reasons(
                ad_ratio=ad_ratio,
                advance_pct=advance_pct,
                decline_pct=decline_pct,
                breadth_strength=breadth_strength,
            )
        )

        return AdvanceDecline(
            ad_ratio=ad_ratio,
            advance_percentage=advance_pct,
            decline_percentage=decline_pct,
            advance_dominance=advance_dom,
            decline_dominance=decline_dom,
            breadth_strength=breadth_strength,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _ad_ratio(self, snapshot: MarketBreadthSnapshot) -> float:
        if snapshot.declines == 0:
            if snapshot.advances == 0:
                return 1.0
            return float(snapshot.advances)
        return snapshot.advances / snapshot.declines

    def _advance_percentage(self, snapshot: MarketBreadthSnapshot) -> float:
        if snapshot.total_symbols == 0:
            return 50.0
        return (snapshot.advances / snapshot.total_symbols) * 100.0

    def _decline_percentage(self, snapshot: MarketBreadthSnapshot) -> float:
        if snapshot.total_symbols == 0:
            return 50.0
        return (snapshot.declines / snapshot.total_symbols) * 100.0

    def _breadth_strength(self, ad_ratio: float) -> BreadthStrength:
        if ad_ratio >= VERY_STRONG_AD:
            return BreadthStrength.VERY_STRONG
        elif ad_ratio >= STRONG_AD:
            return BreadthStrength.STRONG
        elif ad_ratio <= VERY_WEAK_AD:
            return BreadthStrength.VERY_WEAK
        elif ad_ratio <= WEAK_AD:
            return BreadthStrength.WEAK
        else:
            return BreadthStrength.NEUTRAL

    def _confidence(
        self,
        snapshot: MarketBreadthSnapshot,
        ad_ratio: float,
    ) -> float:
        sample_factor = min(1.0, snapshot.total_symbols / 50)
        if abs(ad_ratio - 1.0) > 0.3:
            signal = 0.75
        else:
            signal = 0.3
        return min(1.0, sample_factor * (0.3 + 0.7 * signal))

    def _reasons(
        self,
        ad_ratio: float,
        advance_pct: float,
        decline_pct: float,
        breadth_strength: BreadthStrength,
    ) -> list[str]:
        reasons: list[str] = []
        reasons.append(
            f"A/D ratio is {ad_ratio:.2f} ({advance_pct:.1f}% advancing, "
            f"{decline_pct:.1f}% declining)."
        )
        reasons.append(f"Breadth is {breadth_strength.value}.")
        return reasons
