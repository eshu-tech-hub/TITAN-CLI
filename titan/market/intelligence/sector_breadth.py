"""Sector Breadth Analyzer.

Analyses sector-level breadth, leadership, and rotation.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import (
    MarketBreadthSnapshot,
    SectorBreadth,
    SectorBreadthSnapshot,
)

MIN_SECTORS = 2
CONCENTRATION_THRESHOLD = 0.5


class SectorBreadthAnalyzer:
    """Analyse sector-level breadth and rotation.

    Consumes MarketBreadthSnapshot with sector summaries to
    identify leading/ lagging sectors and detect rotation.
    """

    name = "SectorBreadthAnalyzer"

    def analyze(
        self,
        snapshot: MarketBreadthSnapshot,
    ) -> SectorBreadth:
        """Evaluate sector breadth and detect rotation.

        Args:
            snapshot: Market breadth snapshot with sector data.

        Returns:
            Sector breadth assessment.
        """

        reasons: list[str] = []
        sectors = snapshot.sector_summaries

        if not sectors or len(sectors) < MIN_SECTORS:
            return SectorBreadth(
                confidence=0.0,
                reasons=(
                    (f"Insufficient sector data: need at least "
                    f"{MIN_SECTORS} sectors, got {len(sectors)}."),
                ),
            )

        advancing_sectors = 0
        declining_sectors = 0
        sector_net: list[tuple[str, int]] = []

        for sec in sectors:
            net = sec.advances - sec.declines
            sector_net.append((sec.sector_name, net))
            if net > 0:
                advancing_sectors += 1
            elif net < 0:
                declining_sectors += 1

        sector_net.sort(key=lambda x: x[1], reverse=True)

        leading = tuple(name for name, _ in sector_net[:3] if name)
        lagging = tuple(name for name, _ in sector_net[-3:] if name)

        rotation = advancing_sectors > 0 and declining_sectors > 0

        concentration = self._concentration_risk(sectors)

        confidence = self._confidence(sectors)

        reasons.extend(
            self._reasons(
                advancing=advancing_sectors,
                declining=declining_sectors,
                leading=leading,
                lagging=lagging,
                rotation=rotation,
                concentration=concentration,
            )
        )

        return SectorBreadth(
            advancing_sectors=advancing_sectors,
            declining_sectors=declining_sectors,
            leading_sectors=leading,
            lagging_sectors=lagging,
            rotation_detected=rotation,
            concentration_risk=concentration,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _concentration_risk(
        self,
        sectors: tuple[SectorBreadthSnapshot, ...],
    ) -> bool:
        if not sectors:
            return False
        weights = [s.weight for s in sectors if s.weight > 0]
        if not weights:
            return False
        max_weight = max(weights)
        return max_weight >= CONCENTRATION_THRESHOLD

    def _confidence(
        self,
        sectors: tuple[SectorBreadthSnapshot, ...],
    ) -> float:
        if not sectors:
            return 0.0
        sample_factor = min(1.0, len(sectors) / 10)
        return min(1.0, sample_factor * 0.85)

    def _reasons(
        self,
        advancing: int,
        declining: int,
        leading: tuple[str, ...],
        lagging: tuple[str, ...],
        rotation: bool,
        concentration: bool,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(
            f"{advancing} sector(s) advancing, {declining} sector(s) declining."
        )

        if leading:
            reasons.append(f"Leading sectors: {', '.join(leading)}.")
        if lagging:
            reasons.append(f"Lagging sectors: {', '.join(lagging)}.")

        if rotation:
            reasons.append("Sector rotation detected — mixed breadth across sectors.")

        if concentration:
            reasons.append("Concentration risk: one sector dominates the index.")

        return reasons
