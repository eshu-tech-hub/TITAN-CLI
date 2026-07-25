from collections import defaultdict

from dataclasses import dataclass

from titan.portfolio.models import (
    CorrelationAnalysis,
    CorrelationLevel,
    ExistingPortfolio,
)


@dataclass(slots=True)
class CorrelationAnalyzer:
    """Analyses cross-position correlation risk.

    Measures:
        - Highly correlated position pairs (same sector or symbol).
        - Duplicate exposure to the same symbol.
        - Index concentration (major index symbols).
        - Sector correlation from overlapping positions.
    """

    name: str = "CorrelationAnalyzer"

    INDEX_SYMBOLS: tuple[str, ...] = ("NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY")

    def analyze(self, portfolio: ExistingPortfolio) -> CorrelationAnalysis:
        """Analyse correlation risk in the portfolio.

        Args:
            portfolio: Existing portfolio with open positions.

        Returns:
            Correlation risk assessment.
        """
        positions = portfolio.positions
        if not positions:
            return CorrelationAnalysis()

        symbol_counts: dict[str, int] = defaultdict(int)
        sector_positions: dict[str, list[str]] = defaultdict(list)
        index_symbols_present: list[str] = []

        for pos in positions:
            symbol_counts[pos.symbol] += 1
            sector_positions[pos.sector or "Unknown"].append(pos.symbol)
            if pos.symbol.upper() in self.INDEX_SYMBOLS:
                index_symbols_present.append(pos.symbol)

        duplicate_exposure = any(c > 1 for c in symbol_counts.values())

        highly_correlated_pairs = 0
        for sector, syms in sector_positions.items():
            if len(syms) > 1:
                highly_correlated_pairs += len(syms) * (len(syms) - 1) // 2

        index_concentration = len(index_symbols_present) > 0

        sector_count = len(sector_positions)
        if sector_count <= 1 and len(positions) > 1:
            sector_correlation = CorrelationLevel.EXTREME
        elif sector_count == 1:
            sector_correlation = (
                CorrelationLevel.HIGH if len(positions) > 1 else CorrelationLevel.LOW
            )
        elif sector_count <= 3:
            sector_correlation = CorrelationLevel.MODERATE
        else:
            sector_correlation = CorrelationLevel.LOW

        overall = self._determine_overall(
            highly_correlated_pairs,
            duplicate_exposure,
            index_concentration,
            sector_correlation,
        )

        return CorrelationAnalysis(
            highly_correlated_pairs=highly_correlated_pairs,
            duplicate_exposure=duplicate_exposure,
            index_concentration=index_concentration,
            sector_correlation=sector_correlation,
            overall_correlation_level=overall,
        )

    def _determine_overall(
        self,
        highly_correlated_pairs: int,
        duplicate_exposure: bool,
        index_concentration: bool,
        sector_correlation: CorrelationLevel,
    ) -> CorrelationLevel:
        if (
            highly_correlated_pairs >= 5
            or sector_correlation == CorrelationLevel.EXTREME
        ):
            return CorrelationLevel.EXTREME
        if (
            highly_correlated_pairs >= 3
            or sector_correlation == CorrelationLevel.HIGH
            or (duplicate_exposure and index_concentration)
        ):
            return CorrelationLevel.HIGH
        if highly_correlated_pairs >= 1 or duplicate_exposure or index_concentration:
            return CorrelationLevel.MODERATE
        if sector_correlation in (CorrelationLevel.LOW, CorrelationLevel.VERY_LOW):
            return sector_correlation
        return CorrelationLevel.LOW
