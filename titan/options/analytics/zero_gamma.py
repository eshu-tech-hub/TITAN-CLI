"""Zero Gamma (Gamma Flip) Analyzer.

Identifies the price level where aggregate gamma exposure crosses from
positive to negative (or vice versa). This "zero gamma" or "gamma flip"
level is a critical institutional reference — it represents the price
at which dealer hedging behaviour changes.

No broker imports.
No API calls.
No Black-Scholes implementation.
"""

from numbers import Real
from typing import Any

from titan.options.analytics.models import (
    GammaExposureInput,
    GammaRegime,
    GreeksAnalysis,
    OptionChainSnapshot,
    ZeroGammaLevel,
)

NEUTRAL_GAMMA_THRESHOLD = 1e-10


class ZeroGammaAnalyzer:
    """Identify the price level where net gamma exposure crosses zero.

    Consumes supplied GreeksAnalysis and/or OptionChainSnapshot to
    estimate the gamma flip level.  Pure analysis — does not modify
    any input model.
    """

    name = "ZeroGammaAnalyzer"

    def analyze(
        self,
        input_data: GammaExposureInput,
    ) -> ZeroGammaLevel | None:
        """Estimate the zero-gamma (gamma flip) level.

        Args:
            input_data: Aggregated gamma exposure inputs.

        Returns:
            Zero gamma level estimate, or ``None`` when insufficient
            data is available.
        """

        snapshot = input_data.option_chain_snapshot
        greeks = input_data.greeks
        underlying = self._underlying_price(snapshot)

        if greeks is not None and greeks.net_gamma is not None:
            regime = self._regime_from_net_gamma(greeks.net_gamma)
        else:
            regime = GammaRegime.UNKNOWN

        if snapshot is None or not snapshot.strikes:
            return self._build_level(
                strike=None,
                underlying=underlying,
                confidence=self._confidence(greeks, snapshot),
            )

        flip_strike = self._find_flip(snapshot)

        if flip_strike is not None:
            distance = self._distance(flip_strike, underlying)
            confidence = self._confidence(greeks, snapshot)
            return self._build_level(
                strike=flip_strike,
                underlying=underlying,
                distance=distance,
                confidence=confidence,
            )

        if regime is GammaRegime.POSITIVE:
            return self._build_level(
                strike=self._max_strike(snapshot),
                underlying=underlying,
                confidence=0.3,
            )
        if regime is GammaRegime.NEGATIVE:
            return self._build_level(
                strike=self._min_strike(snapshot),
                underlying=underlying,
                confidence=0.3,
            )

        return self._build_level(
            strike=None,
            underlying=underlying,
            confidence=self._confidence(greeks, snapshot),
        )

    def _find_flip(
        self,
        snapshot: OptionChainSnapshot,
    ) -> float | None:
        """Find strike level where cumulative gamma crosses zero.

        Looks for a sign change in the running cumulative gamma
        exposure (call - put gamma * OI) across strikes sorted by
        strike price.  Returns the interpolated crossing point.
        """

        strikes = sorted(snapshot.strikes, key=lambda s: s.strike_price)
        cumulative = 0.0
        prev_cumulative = 0.0

        for strike in strikes:
            call_gex = self._gamma_exposure(
                strike.call_gamma, strike.call_open_interest
            )
            put_gex = self._gamma_exposure(strike.put_gamma, strike.put_open_interest)
            net = call_gex - put_gex
            cumulative += net

            if self._sign_change(prev_cumulative, cumulative):
                return self._interpolate(
                    prev_strike=(
                        strikes[strikes.index(strike) - 1].strike_price
                        if strikes.index(strike) > 0
                        else strike.strike_price
                    ),
                    curr_strike=strike.strike_price,
                    prev_val=prev_cumulative,
                    curr_val=cumulative,
                )

            prev_cumulative = cumulative

        return None

    def _gamma_exposure(
        self,
        gamma: float | None,
        open_interest: int,
    ) -> float:
        """Compute gamma exposure contribution for a single side."""
        if gamma is None or not self._valid_number(gamma):
            return 0.0
        return abs(float(gamma)) * open_interest

    def _sign_change(self, a: float, b: float) -> bool:
        """Detect sign change (zero crossing)."""
        if abs(a) < NEUTRAL_GAMMA_THRESHOLD or abs(b) < NEUTRAL_GAMMA_THRESHOLD:
            return False
        return (a > 0) != (b > 0)

    def _interpolate(
        self,
        prev_strike: float,
        curr_strike: float,
        prev_val: float,
        curr_val: float,
    ) -> float:
        """Linearly interpolate the zero crossing between two strikes."""
        if abs(curr_val - prev_val) < NEUTRAL_GAMMA_THRESHOLD:
            return (prev_strike + curr_strike) / 2.0
        fraction = abs(prev_val) / abs(curr_val - prev_val)
        return prev_strike + fraction * (curr_strike - prev_strike)

    def _regime_from_net_gamma(self, net_gamma: float) -> GammaRegime:
        """Classify gamma regime from aggregate net gamma."""
        if abs(net_gamma) < NEUTRAL_GAMMA_THRESHOLD:
            return GammaRegime.NEUTRAL
        if net_gamma > 0:
            return GammaRegime.POSITIVE
        return GammaRegime.NEGATIVE

    def _underlying_price(
        self,
        snapshot: OptionChainSnapshot | None,
    ) -> float | None:
        if snapshot is None:
            return None
        return snapshot.underlying_price

    def _min_strike(self, snapshot: OptionChainSnapshot) -> float | None:
        if not snapshot.strikes:
            return None
        return min(s.strike_price for s in snapshot.strikes)

    def _max_strike(self, snapshot: OptionChainSnapshot) -> float | None:
        if not snapshot.strikes:
            return None
        return max(s.strike_price for s in snapshot.strikes)

    def _distance(
        self,
        strike: float | None,
        underlying: float | None,
    ) -> float | None:
        if strike is None or underlying is None or underlying == 0:
            return None
        return (strike - underlying) / underlying

    def _confidence(
        self,
        greeks: GreeksAnalysis | None,
        snapshot: OptionChainSnapshot | None,
    ) -> float:
        score = 0.0
        factors = 0

        if greeks is not None and greeks.net_gamma is not None:
            score += min(1.0, greeks.confidence)
            factors += 1

        if snapshot is not None and len(snapshot.strikes) > 0:
            strike_count = len(snapshot.strikes)
            available = sum(
                1
                for s in snapshot.strikes
                if s.call_gamma is not None or s.put_gamma is not None
            )
            completeness = available / max(strike_count, 1)
            score += 0.3 + completeness * 0.4
            factors += 1

        if factors == 0:
            return 0.0

        return min(1.0, score / factors)

    def _build_level(
        self,
        strike: float | None,
        underlying: float | None,
        distance: float | None = None,
        confidence: float = 0.0,
    ) -> ZeroGammaLevel:
        return ZeroGammaLevel(
            strike=strike,
            underlying_price=underlying,
            distance_percent=distance,
            confidence=confidence,
        )

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)
