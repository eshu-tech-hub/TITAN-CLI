from math import isinf
from numbers import Real
from typing import Any

from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    MarketBias,
    OptionChainSnapshot,
)


class PCRAnalyzer(OptionAnalyzer):
    """Analyze option-chain put-call ratio using open interest."""

    name = "PCRAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Calculate and interpret put-call ratio from valid strike rows."""

        self._validate_snapshot(snapshot)
        total_call_oi = 0
        total_put_oi = 0
        invalid_contracts = 0

        for strike in snapshot.strikes:
            if not self._valid_number(strike.strike_price) or strike.strike_price <= 0:
                invalid_contracts += 1
                continue
            if not self._valid_oi(strike.call_open_interest) or not self._valid_oi(
                strike.put_open_interest
            ):
                invalid_contracts += 1
                continue
            total_call_oi += int(strike.call_open_interest)
            total_put_oi += int(strike.put_open_interest)

        pcr = self._calculate_pcr(total_put_oi, total_call_oi)
        warnings = self._warnings(
            snapshot, invalid_contracts, total_call_oi, total_put_oi
        )
        bias, score, reasons = self._interpret(pcr, total_put_oi, total_call_oi)

        return AnalysisResult(
            score=score,
            confidence=self._confidence(
                snapshot, invalid_contracts, total_call_oi, total_put_oi
            ),
            bullish=bias is MarketBias.BULLISH,
            bearish=bias is MarketBias.BEARISH,
            neutral=bias in (MarketBias.NEUTRAL, MarketBias.UNKNOWN),
            reasons=reasons,
            warnings=warnings,
            metadata={
                "analyzer": self.name,
                "market_bias": bias,
                "pcr": pcr,
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "valid_contracts": len(snapshot.strikes) - invalid_contracts,
                "invalid_contracts": invalid_contracts,
            },
        )

    def _calculate_pcr(self, total_put_oi: int, total_call_oi: int) -> float | None:
        if total_call_oi == 0:
            if total_put_oi == 0:
                return None
            return float("inf")
        return total_put_oi / total_call_oi

    def _interpret(
        self,
        pcr: float | None,
        total_put_oi: int,
        total_call_oi: int,
    ) -> tuple[MarketBias, float, tuple[str, ...]]:
        if pcr is None:
            return MarketBias.UNKNOWN, 50.0, ("PCR unavailable without open interest.",)
        if isinf(pcr):
            return MarketBias.BULLISH, 80.0, ("Put OI present while Call OI is zero.",)
        if pcr >= 1.2:
            score = min(85.0, 50.0 + ((pcr - 1.0) * 40.0))
            return MarketBias.BULLISH, score, ("PCR shows Put OI dominance.",)
        if pcr <= 0.8:
            score = max(15.0, 50.0 - ((1.0 - pcr) * 40.0))
            return MarketBias.BEARISH, score, ("PCR shows Call OI dominance.",)
        if total_put_oi == 0 and total_call_oi == 0:
            return MarketBias.UNKNOWN, 50.0, ("PCR unavailable without open interest.",)
        return MarketBias.NEUTRAL, 50.0, ("PCR is balanced.",)

    def _warnings(
        self,
        snapshot: OptionChainSnapshot,
        invalid_contracts: int,
        total_call_oi: int,
        total_put_oi: int,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if not snapshot.strikes:
            warnings.append("Empty Option Chain")
        if invalid_contracts:
            warnings.append("Invalid Contracts Ignored")
        if total_call_oi == 0:
            warnings.append("Zero Call OI")
        if total_put_oi == 0:
            warnings.append("Zero Put OI")
        if total_call_oi + total_put_oi == 0:
            warnings.append("Missing OI")
        return tuple(dict.fromkeys(warnings))

    def _confidence(
        self,
        snapshot: OptionChainSnapshot,
        invalid_contracts: int,
        total_call_oi: int,
        total_put_oi: int,
    ) -> float:
        if not snapshot.strikes or total_call_oi + total_put_oi == 0:
            return 0.1
        valid_count = len(snapshot.strikes) - invalid_contracts
        if valid_count <= 1:
            return 0.25
        if invalid_contracts or total_call_oi == 0 or total_put_oi == 0:
            return 0.35
        return 0.6

    def _valid_oi(self, value: Any) -> bool:
        return self._valid_number(value) and value >= 0

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)
