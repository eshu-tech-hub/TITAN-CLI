"""Gamma Walls Analyzer.

Identifies significant gamma concentration levels — call walls and put
walls — from supplied option-chain data.  These levels represent price
zones where dealer hedging activity is expected to create resistance
(call wall) or support (put wall).

No broker imports.
No API calls.
No Black-Scholes implementation.
"""

from numbers import Real
from typing import Any

from titan.options.analytics.models import (
    GammaExposureInput,
    GammaWall,
    OptionChainSnapshot,
    WallType,
)

MIN_STRIKES_FOR_WALL = 2
MAX_WALL_CANDIDATES = 5


class GammaWallsAnalyzer:
    """Identify gamma walls from supplied option-chain data.

    Consumes OptionChainSnapshot to locate strikes with the highest
    gamma-weighted open interest concentration.  Pure analysis — does
    not modify any input model.
    """

    name = "GammaWallsAnalyzer"

    def analyze(
        self,
        input_data: GammaExposureInput,
    ) -> tuple[GammaWall | None, GammaWall | None]:
        """Identify call wall and put wall.

        Args:
            input_data: Aggregated gamma exposure inputs.

        Returns:
            Tuple of (call_wall, put_wall).  Each may be ``None`` when
            insufficient data is available.
        """

        snapshot = input_data.option_chain_snapshot

        if snapshot is None or len(snapshot.strikes) < MIN_STRIKES_FOR_WALL:
            return None, None

        call_candidates = self._rank_strikes(snapshot, side="call")
        put_candidates = self._rank_strikes(snapshot, side="put")

        call_wall = self._select_wall(call_candidates, WallType.CALL_WALL)
        put_wall = self._select_wall(put_candidates, WallType.PUT_WALL)

        return call_wall, put_wall

    def _rank_strikes(
        self,
        snapshot: OptionChainSnapshot,
        side: str,
    ) -> list[tuple[float, float, int]]:
        """Rank strikes by gamma-weighted open interest.

        Returns list of (strike_price, gamma_exposure, open_interest)
        tuples sorted descending by gamma exposure.
        """
        candidates: list[tuple[float, float, int]] = []

        for strike in snapshot.strikes:
            if side == "call":
                gamma = strike.call_gamma
                oi = strike.call_open_interest
            else:
                gamma = strike.put_gamma
                oi = strike.put_open_interest

            exposure = self._compute_exposure(gamma, oi)
            if exposure > 0:
                candidates.append((strike.strike_price, exposure, oi))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:MAX_WALL_CANDIDATES]

    def _compute_exposure(
        self,
        gamma: float | None,
        open_interest: int,
    ) -> float:
        """Compute gamma-weighted exposure for one side of a strike."""
        if gamma is None or not self._valid_number(gamma):
            return float(open_interest)
        return abs(float(gamma)) * open_interest

    def _select_wall(
        self,
        candidates: list[tuple[float, float, int]],
        wall_type: WallType,
    ) -> GammaWall | None:
        """Select the strongest wall from ranked candidates.

        The top candidate is the primary wall.  Returns ``None`` if
        no valid candidate exists.
        """
        if not candidates:
            return None

        strike, exposure, oi = candidates[0]

        if oi == 0 and exposure == 0:
            return None

        total_exposure = sum(e for _, e, _ in candidates) or 1.0
        concentration = exposure / total_exposure

        confidence = self._wall_confidence(concentration, oi, len(candidates))

        return GammaWall(
            strike=strike,
            wall_type=wall_type,
            gamma_concentration=concentration,
            open_interest=oi,
            confidence=confidence,
        )

    def _wall_confidence(
        self,
        concentration: float,
        open_interest: int,
        candidate_count: int,
    ) -> float:
        """Calculate confidence in wall identification.

        Higher concentration, higher OI, and more candidates all
        contribute to confidence.
        """
        score = 0.3

        score += min(0.3, concentration * 0.3)

        if open_interest > 10000:
            score += 0.2
        elif open_interest > 1000:
            score += 0.1

        if candidate_count >= 3:
            score += 0.1

        return min(1.0, score)

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)
