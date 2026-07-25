from titan.options.analytics.models import (
    DepthAnalysis,
    LiquidityRisk,
    OptionLiquiditySnapshot,
    SlippageAnalysis,
    SpreadAnalysis,
)


class SlippageAnalyzer:
    """Estimate expected slippage from spread, displayed depth, and activity."""

    name = "SlippageAnalyzer"

    def analyze(
        self,
        snapshot: OptionLiquiditySnapshot,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
    ) -> SlippageAnalysis:
        """Estimate slippage and classify liquidity risk."""

        if not isinstance(snapshot, OptionLiquiditySnapshot):
            raise TypeError("snapshot must be an OptionLiquiditySnapshot.")
        if not isinstance(spread, SpreadAnalysis):
            raise TypeError("spread must be a SpreadAnalysis.")
        if not isinstance(depth, DepthAnalysis):
            raise TypeError("depth must be a DepthAnalysis.")

        warnings = self._warnings(snapshot, spread, depth)
        if spread.spread_percent is None:
            return SlippageAnalysis(
                expected_slippage=None,
                slippage_score=0.0,
                confidence=0.1,
                liquidity_risk=LiquidityRisk.UNKNOWN,
                warnings=warnings,
                metadata={"available": False},
            )

        expected_slippage = (
            (spread.spread_percent / 2.0)
            + self._depth_penalty(depth.depth_score)
            + self._activity_penalty(snapshot)
        )
        score = max(0.0, min(100.0, 100.0 - (expected_slippage * 12.0)))
        confidence = max(
            0.1, min(0.8, (spread.confidence * 0.5) + (depth.confidence * 0.3))
        )

        return SlippageAnalysis(
            expected_slippage=expected_slippage,
            slippage_score=score,
            confidence=confidence,
            liquidity_risk=self._risk(score),
            warnings=warnings,
            metadata={
                "available": True,
                "spread_component": spread.spread_percent / 2.0,
                "depth_penalty": self._depth_penalty(depth.depth_score),
                "activity_penalty": self._activity_penalty(snapshot),
            },
        )

    def explanation(self, result: SlippageAnalysis) -> str:
        """Generate a structured slippage explanation."""

        if result.expected_slippage is None:
            return "Slippage could not be estimated because spread data is incomplete."
        return (
            f"Expected slippage is {result.expected_slippage:.2f}% with "
            f"{result.liquidity_risk.value} liquidity risk."
        )

    def _warnings(
        self,
        snapshot: OptionLiquiditySnapshot,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
    ) -> tuple[str, ...]:
        warnings = list(spread.warnings + depth.warnings)
        if snapshot.volume is None:
            warnings.append("Volume is missing.")
        elif snapshot.volume <= 0:
            warnings.append("Volume is zero or negative.")
        if snapshot.open_interest is None:
            warnings.append("Open interest is missing.")
        elif snapshot.open_interest <= 0:
            warnings.append("Open interest is zero or negative.")
        return tuple(dict.fromkeys(warnings))

    def _depth_penalty(self, depth_score: float) -> float:
        return max(0.0, (100.0 - depth_score) / 25.0)

    def _activity_penalty(self, snapshot: OptionLiquiditySnapshot) -> float:
        penalty = 0.0
        if snapshot.volume is None or snapshot.volume <= 0:
            penalty += 1.0
        elif snapshot.volume < 100:
            penalty += 0.5

        if snapshot.open_interest is None or snapshot.open_interest <= 0:
            penalty += 1.0
        elif snapshot.open_interest < 500:
            penalty += 0.5

        return penalty

    def _risk(self, score: float) -> LiquidityRisk:
        if score >= 75.0:
            return LiquidityRisk.LOW
        if score >= 55.0:
            return LiquidityRisk.MODERATE
        if score >= 35.0:
            return LiquidityRisk.HIGH
        return LiquidityRisk.EXTREME
