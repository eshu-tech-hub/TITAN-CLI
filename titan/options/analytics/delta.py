from numbers import Real
from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    MarketBias,
    OptionChainSnapshot,
)

NEUTRAL_SCORE = 50.0
MAX_SCORE = 100.0
MIN_SCORE = 0.0
DIRECTIONAL_DELTA_THRESHOLD = 0.15
SCORE_DELTA_MULTIPLIER = 25.0


class DeltaAnalyzer(OptionAnalyzer):
    """Analyze supplied option delta values without estimating Greeks."""

    name = "DeltaAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Calculate net, average, ATM, and directional delta exposure."""

        self._validate_snapshot(snapshot)
        values = self._values(snapshot)
        warnings = self._warnings(snapshot, values)

        if not values:
            return AnalysisResult(
                score=NEUTRAL_SCORE,
                confidence=0.1,
                bullish=False,
                bearish=False,
                neutral=True,
                reasons=("Delta unavailable from supplied option-chain data.",),
                warnings=warnings,
                metadata=self._metadata(None, None, None, MarketBias.UNKNOWN, 0),
            )

        net_delta = sum(values)
        average_delta = net_delta / len(values)
        atm_delta = self._atm_delta(snapshot)
        bias = self._bias(net_delta)
        score = self._score(net_delta)
        reasons = self._reasons(net_delta, average_delta, atm_delta, bias)

        return AnalysisResult(
            score=score,
            confidence=self._confidence(snapshot, len(values), warnings),
            bullish=bias is MarketBias.BULLISH,
            bearish=bias is MarketBias.BEARISH,
            neutral=bias is MarketBias.NEUTRAL,
            reasons=reasons,
            warnings=warnings,
            metadata=self._metadata(
                net_delta, average_delta, atm_delta, bias, len(values)
            ),
        )

    def to_evidence(self, result: AnalysisResult) -> Evidence:
        """Convert delta analysis into universal Greeks evidence."""

        return Evidence(
            source="Greeks",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._signal(result),
            score=Score(result.score),
            confidence=Confidence(result.confidence),
            weight=1.0,
            reasons=result.reasons,
            warnings=result.warnings,
            metadata=result.metadata,
        )

    def explanation(self, result: AnalysisResult) -> str:
        """Generate delta explanation from structured result values."""

        net_delta = result.metadata.get("net_delta")
        average_delta = result.metadata.get("average_delta")
        atm_delta = result.metadata.get("atm_delta")
        if net_delta is None:
            return "Delta data was not supplied, so directional exposure is unknown."
        return (
            f"Net delta is {net_delta:.2f}, average delta is {average_delta:.2f}, "
            f"and ATM delta is {self._format_optional(atm_delta)}."
        )

    def _values(self, snapshot: OptionChainSnapshot) -> list[float]:
        values: list[float] = []
        for strike in snapshot.strikes:
            values.extend(self._valid_values(strike.call_delta, strike.put_delta))
        return values

    def _atm_delta(self, snapshot: OptionChainSnapshot) -> float | None:
        if snapshot.underlying_price is None or not snapshot.strikes:
            return None

        underlying: float = float(snapshot.underlying_price)
        nearest = min(
            snapshot.strikes,
            key=lambda strike: abs(strike.strike_price - underlying),
        )
        values = self._valid_values(nearest.call_delta, nearest.put_delta)
        if not values:
            return None
        return sum(values) / len(values)

    def _warnings(
        self,
        snapshot: OptionChainSnapshot,
        values: list[float],
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if not snapshot.strikes:
            warnings.append("Empty Option Chain")
        if not values:
            warnings.append("Missing Delta")
        if snapshot.underlying_price is None:
            warnings.append("ATM Delta Unavailable")
        return tuple(dict.fromkeys(warnings))

    def _reasons(
        self,
        net_delta: float,
        average_delta: float,
        atm_delta: float | None,
        bias: MarketBias,
    ) -> tuple[str, ...]:
        reasons = [
            f"Net delta {net_delta:.2f}.",
            f"Average delta {average_delta:.2f}.",
            f"Directional exposure is {bias.value}.",
        ]
        if atm_delta is not None:
            reasons.append(f"ATM delta {atm_delta:.2f}.")
        return tuple(reasons)

    def _metadata(
        self,
        net_delta: float | None,
        average_delta: float | None,
        atm_delta: float | None,
        bias: MarketBias,
        valid_contracts: int,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "market_bias": bias,
            "net_delta": net_delta,
            "average_delta": average_delta,
            "atm_delta": atm_delta,
            "directional_exposure": bias.value,
            "valid_contracts": valid_contracts,
        }

    def _bias(self, net_delta: float) -> MarketBias:
        if net_delta > DIRECTIONAL_DELTA_THRESHOLD:
            return MarketBias.BULLISH
        if net_delta < -DIRECTIONAL_DELTA_THRESHOLD:
            return MarketBias.BEARISH
        return MarketBias.NEUTRAL

    def _score(self, net_delta: float) -> float:
        return min(
            MAX_SCORE,
            max(MIN_SCORE, NEUTRAL_SCORE + (net_delta * SCORE_DELTA_MULTIPLIER)),
        )

    def _confidence(
        self,
        snapshot: OptionChainSnapshot,
        valid_contracts: int,
        warnings: tuple[str, ...],
    ) -> float:
        total_contracts = len(snapshot.strikes) * 2
        if valid_contracts == 0 or total_contracts == 0:
            return 0.1
        completeness = valid_contracts / total_contracts
        confidence = 0.2 + (completeness * 0.5)
        if warnings:
            confidence -= 0.1
        return max(0.1, min(0.7, confidence))

    def _signal(self, result: AnalysisResult) -> EvidenceSignal:
        market_bias = result.metadata.get("market_bias")
        if market_bias is MarketBias.BULLISH:
            return EvidenceSignal.BULLISH
        if market_bias is MarketBias.BEARISH:
            return EvidenceSignal.BEARISH
        if market_bias is MarketBias.NEUTRAL:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.UNKNOWN

    def _valid_values(self, *values: Any) -> list[float]:
        return [float(value) for value in values if self._valid_number(value)]

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)

    def _format_optional(self, value: Any) -> str:
        if value is None:
            return "unavailable"
        return f"{value:.2f}"
