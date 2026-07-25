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
HIGH_CONCENTRATION_THRESHOLD = 0.5


class GammaAnalyzer(OptionAnalyzer):
    """Analyze supplied gamma values and concentration."""

    name = "GammaAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Calculate net gamma, average gamma, and concentration."""

        self._validate_snapshot(snapshot)
        values_by_strike = self._values_by_strike(snapshot)
        values = [
            value
            for strike_values in values_by_strike.values()
            for value in strike_values
        ]
        warnings = self._warnings(snapshot, values)

        if not values:
            return AnalysisResult(
                score=NEUTRAL_SCORE,
                confidence=0.1,
                bullish=False,
                bearish=False,
                neutral=True,
                reasons=("Gamma unavailable from supplied option-chain data.",),
                warnings=warnings,
                metadata=self._metadata(None, None, None, MarketBias.UNKNOWN, 0),
            )

        net_gamma = sum(values)
        average_gamma = net_gamma / len(values)
        concentration = self._concentration(values_by_strike)
        reasons = self._reasons(net_gamma, average_gamma, concentration)
        if concentration is not None and concentration >= HIGH_CONCENTRATION_THRESHOLD:
            warnings = tuple(dict.fromkeys((*warnings, "High Gamma Concentration")))

        return AnalysisResult(
            score=NEUTRAL_SCORE,
            confidence=self._confidence(snapshot, len(values), warnings),
            bullish=False,
            bearish=False,
            neutral=True,
            reasons=reasons,
            warnings=warnings,
            metadata=self._metadata(
                net_gamma,
                average_gamma,
                concentration,
                MarketBias.NEUTRAL,
                len(values),
            ),
        )

    def to_evidence(self, result: AnalysisResult) -> Evidence:
        """Convert gamma analysis into universal Greeks evidence."""

        return Evidence(
            source="Greeks",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=(
                EvidenceSignal.NEUTRAL
                if result.metadata.get("market_bias") is MarketBias.NEUTRAL
                else EvidenceSignal.UNKNOWN
            ),
            score=Score(result.score),
            confidence=Confidence(result.confidence),
            weight=1.0,
            reasons=result.reasons,
            warnings=result.warnings,
            metadata=result.metadata,
        )

    def explanation(self, result: AnalysisResult) -> str:
        """Generate gamma explanation from structured result values."""

        net_gamma = result.metadata.get("net_gamma")
        average_gamma = result.metadata.get("average_gamma")
        concentration = result.metadata.get("gamma_concentration")
        if net_gamma is None:
            return "Gamma data was not supplied, so convexity risk is unknown."
        return (
            f"Net gamma is {net_gamma:.4f}, average gamma is {average_gamma:.4f}, "
            f"and concentration is {self._format_optional(concentration)}."
        )

    def _values_by_strike(
        self, snapshot: OptionChainSnapshot
    ) -> dict[float, list[float]]:
        return {
            strike.strike_price: self._valid_values(strike.call_gamma, strike.put_gamma)
            for strike in snapshot.strikes
        }

    def _concentration(
        self, values_by_strike: dict[float, list[float]]
    ) -> float | None:
        strike_totals = [
            sum(abs(value) for value in values) for values in values_by_strike.values()
        ]
        total_gamma = sum(strike_totals)
        if total_gamma == 0:
            return 0.0 if strike_totals else None
        return max(strike_totals) / total_gamma

    def _warnings(
        self,
        snapshot: OptionChainSnapshot,
        values: list[float],
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if not snapshot.strikes:
            warnings.append("Empty Option Chain")
        if not values:
            warnings.append("Missing Gamma")
        return tuple(dict.fromkeys(warnings))

    def _reasons(
        self,
        net_gamma: float,
        average_gamma: float,
        concentration: float | None,
    ) -> tuple[str, ...]:
        reasons = [
            f"Net gamma {net_gamma:.4f}.",
            f"Average gamma {average_gamma:.4f}.",
        ]
        if concentration is not None:
            reasons.append(f"Gamma concentration {concentration:.2f}.")
        return tuple(reasons)

    def _metadata(
        self,
        net_gamma: float | None,
        average_gamma: float | None,
        concentration: float | None,
        bias: MarketBias,
        valid_contracts: int,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "market_bias": bias,
            "net_gamma": net_gamma,
            "average_gamma": average_gamma,
            "gamma_concentration": concentration,
            "gex": None,
            "dealer_gamma": None,
            "valid_contracts": valid_contracts,
        }

    def _confidence(
        self,
        snapshot: OptionChainSnapshot,
        valid_contracts: int,
        warnings: tuple[str, ...],
    ) -> float:
        total_contracts = len(snapshot.strikes) * 2
        if valid_contracts == 0 or total_contracts == 0:
            return 0.1
        confidence = 0.2 + ((valid_contracts / total_contracts) * 0.5)
        if warnings:
            confidence -= 0.1
        return max(0.1, min(0.7, confidence))

    def _valid_values(self, *values: Any) -> list[float]:
        return [float(value) for value in values if self._valid_number(value)]

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)

    def _format_optional(self, value: Any) -> str:
        if value is None:
            return "unavailable"
        return f"{value:.2f}"
