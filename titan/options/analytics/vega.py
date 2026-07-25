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
HIGH_VEGA_THRESHOLD = 1.0
LOW_VEGA_THRESHOLD = 0.05


class VegaAnalyzer(OptionAnalyzer):
    """Analyze supplied vega values and volatility sensitivity."""

    name = "VegaAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Calculate net vega, average vega, and vega risk state."""

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
                reasons=("Vega unavailable from supplied option-chain data.",),
                warnings=warnings,
                metadata=self._metadata(None, None, "unknown", MarketBias.UNKNOWN, 0),
            )

        net_vega = sum(values)
        average_vega = net_vega / len(values)
        sensitivity = self._sensitivity(net_vega, average_vega)
        if sensitivity == "high_vega_risk":
            warnings = tuple(dict.fromkeys((*warnings, "High Vega Risk")))

        return AnalysisResult(
            score=NEUTRAL_SCORE,
            confidence=self._confidence(snapshot, len(values), warnings),
            bullish=False,
            bearish=False,
            neutral=True,
            reasons=self._reasons(net_vega, average_vega, sensitivity),
            warnings=warnings,
            metadata=self._metadata(
                net_vega,
                average_vega,
                sensitivity,
                MarketBias.NEUTRAL,
                len(values),
            ),
        )

    def to_evidence(self, result: AnalysisResult) -> Evidence:
        """Convert vega analysis into universal Greeks evidence."""

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
        """Generate vega explanation from structured result values."""

        net_vega = result.metadata.get("net_vega")
        average_vega = result.metadata.get("average_vega")
        sensitivity = result.metadata.get("volatility_sensitivity")
        if net_vega is None:
            return "Vega data was not supplied, so volatility sensitivity is unknown."
        return (
            f"Net vega is {net_vega:.2f}, average vega is {average_vega:.2f}, "
            f"and volatility sensitivity is {sensitivity}."
        )

    def _values(self, snapshot: OptionChainSnapshot) -> list[float]:
        values: list[float] = []
        for strike in snapshot.strikes:
            values.extend(self._valid_values(strike.call_vega, strike.put_vega))
        return values

    def _warnings(
        self,
        snapshot: OptionChainSnapshot,
        values: list[float],
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if not snapshot.strikes:
            warnings.append("Empty Option Chain")
        if not values:
            warnings.append("Missing Vega")
        return tuple(dict.fromkeys(warnings))

    def _sensitivity(self, net_vega: float, average_vega: float) -> str:
        if abs(net_vega) >= HIGH_VEGA_THRESHOLD:
            return "high_vega_risk"
        if abs(average_vega) <= LOW_VEGA_THRESHOLD:
            return "low_vega_opportunity"
        return "normal_vega"

    def _reasons(
        self,
        net_vega: float,
        average_vega: float,
        sensitivity: str,
    ) -> tuple[str, ...]:
        return (
            f"Net vega {net_vega:.2f}.",
            f"Average vega {average_vega:.2f}.",
            f"Volatility sensitivity is {sensitivity}.",
        )

    def _metadata(
        self,
        net_vega: float | None,
        average_vega: float | None,
        sensitivity: str,
        bias: MarketBias,
        valid_contracts: int,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "market_bias": bias,
            "net_vega": net_vega,
            "average_vega": average_vega,
            "volatility_sensitivity": sensitivity,
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
