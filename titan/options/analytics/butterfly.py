from typing import Any

from titan.options.analytics.models import (
    ButterflyResult,
    OptionChainSnapshot,
)

MAX_VALID_IV = 10.0
CONFIDENCE_RELIABLE_STRIKES = 5
CONFIDENCE_PARTIAL_STRIKES = 3


class ButterflyAnalyzer:
    """Analyze butterfly-like curvature of the implied volatility smile.

    Consumes supplied implied volatility values only.
    Never estimates implied volatility or fits any pricing model.

    Analytics:
        1. ATM Richness — how expensive ATM options are relative to near wings
        2. Wing Richness — how expensive far wings are relative to near wings
        3. Relative Curvature — overall steepness of the volatility curve
    """

    name = "ButterflyAnalyzer"

    def analyze(self, chain: OptionChainSnapshot) -> ButterflyResult:
        if not isinstance(chain, OptionChainSnapshot):
            raise TypeError("chain must be an OptionChainSnapshot.")

        if not chain.strikes:
            return ButterflyResult(
                warnings=("Chain has no strikes.",),
            )

        atm_strike = self._find_atm_strike(chain)
        if atm_strike is None:
            return ButterflyResult(
                warnings=("Could not determine ATM strike.",),
            )

        atm_iv = self._resolve_atm_iv(chain, atm_strike)
        near_wing_strikes, far_wing_strikes = self._split_wings(chain, atm_strike)

        near_wing_iv = self._average_wing_iv(near_wing_strikes, atm_strike)
        far_wing_iv = self._average_wing_iv(far_wing_strikes, atm_strike)

        atm_richness: float | None = None
        if atm_iv is not None and near_wing_iv is not None and near_wing_iv > 0:
            atm_richness = (atm_iv - near_wing_iv) / near_wing_iv

        wing_richness: float | None = None
        if far_wing_iv is not None and near_wing_iv is not None and near_wing_iv > 0:
            wing_richness = (far_wing_iv - near_wing_iv) / near_wing_iv

        relative_curvature: float | None = None
        if atm_richness is not None and wing_richness is not None:
            relative_curvature = abs(atm_richness) + abs(wing_richness)
        elif atm_richness is not None:
            relative_curvature = abs(atm_richness)
        elif wing_richness is not None:
            relative_curvature = abs(wing_richness)

        confidence = self._calculate_confidence(
            chain, atm_iv, near_wing_iv, far_wing_iv
        )
        warnings = self._generate_warnings(chain, atm_iv, near_wing_iv, far_wing_iv)

        return ButterflyResult(
            atm_richness=atm_richness,
            wing_richness=wing_richness,
            relative_curvature=relative_curvature,
            atm_iv=atm_iv,
            near_wing_iv=near_wing_iv,
            far_wing_iv=far_wing_iv,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(chain),
        )

    def _find_atm_strike(self, chain: OptionChainSnapshot) -> float | None:
        if not chain.strikes:
            return None
        underlying = chain.underlying_price
        if underlying is not None and underlying > 0:
            atm = min(chain.strikes, key=lambda s: abs(s.strike_price - underlying))
        else:
            sorted_strikes = sorted(chain.strikes, key=lambda s: s.strike_price)
            atm = sorted_strikes[len(sorted_strikes) // 2]
        return atm.strike_price

    def _resolve_atm_iv(
        self, chain: OptionChainSnapshot, atm_strike: float
    ) -> float | None:
        atm_snapshot = next(
            (s for s in chain.strikes if s.strike_price == atm_strike), None
        )
        if atm_snapshot is None:
            return None

        call_iv = self._safe_iv(atm_snapshot.call_implied_volatility)
        put_iv = self._safe_iv(atm_snapshot.put_implied_volatility)

        if call_iv is not None and put_iv is not None:
            return (call_iv + put_iv) / 2.0
        if call_iv is not None:
            return call_iv
        if put_iv is not None:
            return put_iv
        return None

    def _split_wings(
        self,
        chain: OptionChainSnapshot,
        atm_strike: float,
    ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        distant_strikes: list[tuple[float, float]] = []
        for s in chain.strikes:
            if s.strike_price == atm_strike:
                continue
            iv = self._resolve_wing_iv(s, atm_strike)
            if iv is not None:
                dist = abs(s.strike_price - atm_strike)
                distant_strikes.append((dist, iv))

        distant_strikes.sort(key=lambda x: x[0])

        mid = len(distant_strikes) // 2
        near = distant_strikes[:mid] if mid > 0 else []
        far = distant_strikes[mid:] if mid > 0 else distant_strikes
        return near, far

    def _resolve_wing_iv(self, strike: Any, atm_strike: float) -> float | None:
        if strike.strike_price < atm_strike:
            return self._safe_iv(strike.put_implied_volatility)
        return self._safe_iv(strike.call_implied_volatility)

    def _safe_iv(self, iv: float | None) -> float | None:
        if iv is None:
            return None
        if iv <= 0 or iv >= MAX_VALID_IV:
            return None
        return iv

    def _average_wing_iv(
        self,
        wing_strikes: list[tuple[float, float]],
        atm_strike: float,
    ) -> float | None:
        if not wing_strikes:
            return None
        ivals = [iv for _, iv in wing_strikes]
        return sum(ivals) / len(ivals)

    def _calculate_confidence(
        self,
        chain: OptionChainSnapshot,
        atm_iv: float | None,
        near_wing_iv: float | None,
        far_wing_iv: float | None,
    ) -> float:
        if atm_iv is None:
            return 0.0

        strike_count = len(chain.strikes)
        components = sum(
            1 for v in (atm_iv, near_wing_iv, far_wing_iv) if v is not None
        )

        if strike_count >= CONFIDENCE_RELIABLE_STRIKES and components >= 3:
            return 0.85
        if strike_count >= CONFIDENCE_PARTIAL_STRIKES and components >= 2:
            return 0.55
        if components >= 1:
            return 0.25
        return 0.0

    def _generate_warnings(
        self,
        chain: OptionChainSnapshot,
        atm_iv: float | None,
        near_wing_iv: float | None,
        far_wing_iv: float | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if atm_iv is None:
            warnings.append("ATM implied volatility is unavailable.")
        if near_wing_iv is None:
            warnings.append("Near-wing IV data insufficient for butterfly analysis.")
        if far_wing_iv is None:
            warnings.append("Far-wing IV data insufficient for butterfly analysis.")
        if len(chain.strikes) < CONFIDENCE_PARTIAL_STRIKES:
            warnings.append(
                f"Insufficient strikes for butterfly analysis "
                f"({len(chain.strikes)} available, {CONFIDENCE_PARTIAL_STRIKES}+ recommended)."
            )
        return tuple(warnings)

    def _metadata(self, chain: OptionChainSnapshot) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "underlying": chain.underlying,
            "expiry": chain.expiry.isoformat() if chain.expiry else None,
        }
