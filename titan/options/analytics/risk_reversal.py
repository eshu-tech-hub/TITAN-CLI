from collections.abc import Callable
from typing import Any

from titan.options.analytics.models import (
    MarketBias,
    OptionChainSnapshot,
    OptionStrikeSnapshot,
    RiskReversalResult,
)

MAX_VALID_IV = 10.0
DELTA_TARGET = 0.25
RR_BIAS_THRESHOLD = 0.02
GENERAL_RR_LOW = 0.01
GENERAL_RR_MEDIUM = 0.03
GENERAL_RR_HIGH = 0.06


class RiskReversalAnalyzer:
    """Analyze risk reversal spreads from implied volatility data.

    Consumes supplied implied volatility and delta values only.
    Never estimates delta or implied volatility.
    """

    name = "RiskReversalAnalyzer"

    def analyze(self, chain: OptionChainSnapshot) -> RiskReversalResult:
        if not isinstance(chain, OptionChainSnapshot):
            raise TypeError("chain must be an OptionChainSnapshot.")

        if not chain.strikes:
            return RiskReversalResult(
                warnings=("Chain has no strikes.",),
            )

        atm_strike = self._find_atm_strike(chain)

        otm_puts = [
            s
            for s in chain.strikes
            if atm_strike is not None and s.strike_price < atm_strike
        ]
        otm_calls = [
            s
            for s in chain.strikes
            if atm_strike is not None and s.strike_price > atm_strike
        ]

        put_25d = self._find_strike_by_delta(
            otm_puts, lambda s: s.put_delta, DELTA_TARGET
        )
        call_25d = self._find_strike_by_delta(
            otm_calls, lambda s: s.call_delta, DELTA_TARGET
        )

        twenty_five_delta_rr: float | None = None
        twenty_five_delta_put_iv: float | None = None
        twenty_five_delta_call_iv: float | None = None
        twenty_five_delta_put_strike: float | None = None
        twenty_five_delta_call_strike: float | None = None

        if put_25d is not None and call_25d is not None:
            put_iv = self._safe_iv(put_25d.put_implied_volatility)
            call_iv = self._safe_iv(call_25d.call_implied_volatility)
            if put_iv is not None and call_iv is not None:
                twenty_five_delta_rr = put_iv - call_iv
                twenty_five_delta_put_iv = put_iv
                twenty_five_delta_call_iv = call_iv
                twenty_five_delta_put_strike = put_25d.strike_price
                twenty_five_delta_call_strike = call_25d.strike_price

        avg_otm_put_iv = self._average_otm_iv(
            otm_puts, lambda s: s.put_implied_volatility
        )
        avg_otm_call_iv = self._average_otm_iv(
            otm_calls, lambda s: s.call_implied_volatility
        )

        general_rr: float | None = None
        if avg_otm_put_iv is not None and avg_otm_call_iv is not None:
            general_rr = avg_otm_put_iv - avg_otm_call_iv

        bias, confidence = self._determine_bias(
            twenty_five_delta_rr, general_rr, avg_otm_put_iv, avg_otm_call_iv
        )

        warnings = self._generate_warnings(chain, twenty_five_delta_rr, general_rr)

        return RiskReversalResult(
            twenty_five_delta_rr=twenty_five_delta_rr,
            twenty_five_delta_put_iv=twenty_five_delta_put_iv,
            twenty_five_delta_call_iv=twenty_five_delta_call_iv,
            twenty_five_delta_put_strike=twenty_five_delta_put_strike,
            twenty_five_delta_call_strike=twenty_five_delta_call_strike,
            general_rr=general_rr,
            avg_otm_put_iv=avg_otm_put_iv,
            avg_otm_call_iv=avg_otm_call_iv,
            bias=bias,
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

    def _find_strike_by_delta(
        self,
        strikes: list[OptionStrikeSnapshot],
        get_delta: Callable[[OptionStrikeSnapshot], float | None],
        target: float,
    ) -> OptionStrikeSnapshot | None:
        best: OptionStrikeSnapshot | None = None
        best_diff = float("inf")
        for s in strikes:
            delta = get_delta(s)
            if delta is not None and delta != 0.0:
                diff = abs(abs(delta) - target)
                if diff < best_diff:
                    best_diff = diff
                    best = s
        return best

    def _safe_iv(self, iv: float | None) -> float | None:
        if iv is None:
            return None
        if iv <= 0 or iv >= MAX_VALID_IV:
            return None
        return iv

    def _average_otm_iv(
        self,
        strikes: list[OptionStrikeSnapshot],
        get_iv: Callable[[OptionStrikeSnapshot], float | None],
    ) -> float | None:
        valid: list[float] = []
        for s in strikes:
            iv = self._safe_iv(get_iv(s))
            if iv is not None:
                valid.append(iv)
        if not valid:
            return None
        return sum(valid) / len(valid)

    def _determine_bias(
        self,
        twenty_five_delta_rr: float | None,
        general_rr: float | None,
        avg_otm_put_iv: float | None,
        avg_otm_call_iv: float | None,
    ) -> tuple[MarketBias, float]:
        rr_values = [v for v in (twenty_five_delta_rr, general_rr) if v is not None]
        if not rr_values:
            return MarketBias.UNKNOWN, 0.0

        avg_rr = sum(rr_values) / len(rr_values)
        abs_rr = abs(avg_rr)

        if abs_rr <= RR_BIAS_THRESHOLD:
            return MarketBias.NEUTRAL, self._confidence_from_rr(abs_rr)

        has_25d = twenty_five_delta_rr is not None
        has_general = general_rr is not None
        both = has_25d and has_general

        confidence_base = 0.6 if both else 0.4
        confidence_adjustment = min(abs_rr / GENERAL_RR_HIGH, 1.0) * 0.3
        confidence = min(confidence_base + confidence_adjustment, 1.0)

        if avg_rr > 0:
            return MarketBias.BEARISH, confidence
        return MarketBias.BULLISH, confidence

    def _confidence_from_rr(self, abs_rr: float) -> float:
        if abs_rr < GENERAL_RR_LOW:
            return 0.1
        if abs_rr < GENERAL_RR_MEDIUM:
            return 0.3
        if abs_rr < GENERAL_RR_HIGH:
            return 0.5
        return 0.7

    def _generate_warnings(
        self,
        chain: OptionChainSnapshot,
        twenty_five_delta_rr: float | None,
        general_rr: float | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if twenty_five_delta_rr is None:
            warnings.append(
                "25-delta risk reversal unavailable: missing delta or IV data."
            )
        if general_rr is None:
            warnings.append(
                "General risk reversal unavailable: insufficient OTM IV data."
            )
        if len(chain.strikes) < 3:
            warnings.append("Insufficient strikes for reliable risk reversal analysis.")
        return tuple(warnings)

    def _metadata(self, chain: OptionChainSnapshot) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "underlying": chain.underlying,
            "expiry": chain.expiry.isoformat() if chain.expiry else None,
        }
