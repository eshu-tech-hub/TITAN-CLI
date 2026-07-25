from typing import Any

from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    MarketBias,
    OptionChainSnapshot,
)


class SupportResistanceAnalyzer(OptionAnalyzer):
    """Identify support and resistance from highest Put and Call OI."""

    name = "SupportResistanceAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Return highest Put OI as support and highest Call OI as resistance."""

        self._validate_snapshot(snapshot)
        valid_strikes = [
            strike
            for strike in snapshot.strikes
            if self._valid_strike(strike.strike_price)
            and self._valid_oi(strike.put_open_interest)
            and self._valid_oi(strike.call_open_interest)
        ]
        invalid_contracts = len(snapshot.strikes) - len(valid_strikes)
        highest_put = (
            max(valid_strikes, key=lambda strike: strike.put_open_interest)
            if valid_strikes
            else None
        )
        highest_call = (
            max(valid_strikes, key=lambda strike: strike.call_open_interest)
            if valid_strikes
            else None
        )
        support = highest_put.strike_price if highest_put is not None else None
        resistance = highest_call.strike_price if highest_call is not None else None

        reasons: list[str] = []
        warnings: list[str] = []
        if support is not None:
            reasons.append("Highest Put OI support identified.")
        if resistance is not None:
            reasons.append("Highest Call OI resistance identified.")
        if not valid_strikes:
            reasons.append("Support and resistance unavailable without valid OI.")
            warnings.append("Missing OI")
        if invalid_contracts:
            warnings.append("Invalid Contracts Ignored")
        if support is not None and resistance is not None and support > resistance:
            warnings.append("Inverted Support Resistance")

        return AnalysisResult(
            score=50.0,
            confidence=self._confidence(valid_strikes, invalid_contracts),
            bullish=False,
            bearish=False,
            neutral=True,
            reasons=tuple(reasons),
            warnings=tuple(dict.fromkeys(warnings)),
            metadata={
                "analyzer": self.name,
                "market_bias": MarketBias.NEUTRAL,
                "support": support,
                "resistance": resistance,
                "highest_put_strike": support,
                "highest_call_strike": resistance,
                "valid_contracts": len(valid_strikes),
                "invalid_contracts": invalid_contracts,
            },
        )

    def _confidence(self, valid_strikes: list[Any], invalid_contracts: int) -> float:
        if not valid_strikes:
            return 0.1
        if len(valid_strikes) == 1:
            return 0.25
        if invalid_contracts:
            return 0.4
        return 0.55

    def _valid_strike(self, value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
        )

    def _valid_oi(self, value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
        )
