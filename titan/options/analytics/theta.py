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
THETA_SCORE_MULTIPLIER = 10.0
TIME_DECAY_THRESHOLD = -0.5
NEAR_EXPIRY_DAYS = 2


class ThetaAnalyzer(OptionAnalyzer):
    """Analyze supplied theta values and time-decay risk."""

    name = "ThetaAnalyzer"

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Calculate net theta, average theta, and expiry warnings."""

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
                reasons=("Theta unavailable from supplied option-chain data.",),
                warnings=warnings,
                metadata=self._metadata(None, None, False, MarketBias.UNKNOWN, 0),
            )

        net_theta = sum(values)
        average_theta = net_theta / len(values)
        time_decay_risk = net_theta <= TIME_DECAY_THRESHOLD
        if time_decay_risk:
            warnings = tuple(dict.fromkeys((*warnings, "High Time Decay Risk")))
        bias = MarketBias.BEARISH if time_decay_risk else MarketBias.NEUTRAL

        return AnalysisResult(
            score=self._score(net_theta),
            confidence=self._confidence(snapshot, len(values), warnings),
            bullish=False,
            bearish=bias is MarketBias.BEARISH,
            neutral=bias is MarketBias.NEUTRAL,
            reasons=self._reasons(net_theta, average_theta, time_decay_risk),
            warnings=warnings,
            metadata=self._metadata(
                net_theta,
                average_theta,
                time_decay_risk,
                bias,
                len(values),
            ),
        )

    def to_evidence(self, result: AnalysisResult) -> Evidence:
        """Convert theta analysis into universal Greeks evidence."""

        signal = (
            EvidenceSignal.BEARISH
            if result.metadata.get("market_bias") is MarketBias.BEARISH
            else EvidenceSignal.NEUTRAL
        )
        return Evidence(
            source="Greeks",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=signal,
            score=Score(result.score),
            confidence=Confidence(result.confidence),
            weight=1.0,
            reasons=result.reasons,
            warnings=result.warnings,
            metadata=result.metadata,
        )

    def explanation(self, result: AnalysisResult) -> str:
        """Generate theta explanation from structured result values."""

        net_theta = result.metadata.get("net_theta")
        average_theta = result.metadata.get("average_theta")
        if net_theta is None:
            return "Theta data was not supplied, so time-decay risk is unknown."
        return f"Net theta is {net_theta:.2f}; average theta is {average_theta:.2f}."

    def _values(self, snapshot: OptionChainSnapshot) -> list[float]:
        values: list[float] = []
        for strike in snapshot.strikes:
            values.extend(self._valid_values(strike.call_theta, strike.put_theta))
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
            warnings.append("Missing Theta")
        if (
            snapshot.expiry.date() - snapshot.timestamp.date()
        ).days <= NEAR_EXPIRY_DAYS:
            warnings.append("Near Expiry")
        return tuple(dict.fromkeys(warnings))

    def _reasons(
        self,
        net_theta: float,
        average_theta: float,
        time_decay_risk: bool,
    ) -> tuple[str, ...]:
        reasons = [
            f"Net theta {net_theta:.2f}.",
            f"Average theta {average_theta:.2f}.",
        ]
        if time_decay_risk:
            reasons.append("Time decay risk is elevated.")
        else:
            reasons.append("Time decay risk is controlled.")
        return tuple(reasons)

    def _metadata(
        self,
        net_theta: float | None,
        average_theta: float | None,
        time_decay_risk: bool,
        bias: MarketBias,
        valid_contracts: int,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "market_bias": bias,
            "net_theta": net_theta,
            "average_theta": average_theta,
            "time_decay_risk": time_decay_risk,
            "valid_contracts": valid_contracts,
        }

    def _score(self, net_theta: float) -> float:
        return min(
            MAX_SCORE,
            max(MIN_SCORE, NEUTRAL_SCORE + (net_theta * THETA_SCORE_MULTIPLIER)),
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
        confidence = 0.2 + ((valid_contracts / total_contracts) * 0.5)
        if warnings:
            confidence -= 0.1
        return max(0.1, min(0.7, confidence))

    def _valid_values(self, *values: Any) -> list[float]:
        return [float(value) for value in values if self._valid_number(value)]

    def _valid_number(self, value: Any) -> bool:
        return isinstance(value, Real) and not isinstance(value, bool)
