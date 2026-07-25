from collections import defaultdict

from dataclasses import dataclass

from titan.portfolio.models import (
    ExistingPortfolio,
    PortfolioExposure,
    SectorExposure,
)


@dataclass(slots=True)
class ExposureAnalyzer:
    """Analyses portfolio Greeks and directional exposure.

    Calculates:
        - Net delta, gamma, vega, theta.
        - Directional bias from net delta.
        - Sector concentration (highest sector weight).
        - Symbol concentration (largest single position).
    """

    name: str = "ExposureAnalyzer"

    def analyze(
        self, portfolio: ExistingPortfolio
    ) -> tuple[PortfolioExposure, tuple[SectorExposure, ...]]:
        """Analyse portfolio exposure across all dimensions.

        Args:
            portfolio: Existing portfolio with open positions.

        Returns:
            Tuple of (aggregate exposure, sector breakdown).
        """
        net_delta = 0.0
        net_gamma = 0.0
        net_vega = 0.0
        net_theta = 0.0
        has_greeks = False

        sector_values: dict[str, float] = defaultdict(float)
        sector_counts: dict[str, int] = defaultdict(int)
        symbol_values: dict[str, float] = defaultdict(float)
        total_capital = max(portfolio.total_capital, 1.0)

        for pos in portfolio.positions:
            abs_val = abs(pos.market_value)
            sector_values[pos.sector or "Unknown"] += abs_val
            sector_counts[pos.sector or "Unknown"] += 1
            symbol_values[pos.symbol] += abs_val

            if pos.delta is not None:
                net_delta += pos.delta * pos.quantity
                has_greeks = True
            if pos.gamma is not None:
                net_gamma += pos.gamma * pos.quantity
                has_greeks = True
            if pos.vega is not None:
                net_vega += pos.vega * pos.quantity
                has_greeks = True
            if pos.theta is not None:
                net_theta += pos.theta * pos.quantity
                has_greeks = True

        directional_bias = net_delta if has_greeks else 0.0

        sector_exposures_list: list[SectorExposure] = []
        for sector_name, total_val in sorted(
            sector_values.items(), key=lambda x: x[1], reverse=True
        ):
            sector_exposures_list.append(
                SectorExposure(
                    sector=sector_name,
                    total_value=round(total_val, 2),
                    weight=round(total_val / total_capital, 4),
                    position_count=sector_counts[sector_name],
                )
            )

        sector_concentration = (
            max(v / total_capital for v in sector_values.values())
            if sector_values
            else 0.0
        )
        symbol_concentration = (
            max(v / total_capital for v in symbol_values.values())
            if symbol_values
            else 0.0
        )

        exposure = PortfolioExposure(
            net_delta=round(net_delta, 2) if has_greeks else None,
            net_gamma=round(net_gamma, 2) if has_greeks else None,
            net_vega=round(net_vega, 2) if has_greeks else None,
            net_theta=round(net_theta, 2) if has_greeks else None,
            directional_bias=round(directional_bias, 2),
            sector_concentration=round(sector_concentration, 4),
            symbol_concentration=round(symbol_concentration, 4),
        )

        return exposure, tuple(sector_exposures_list)
