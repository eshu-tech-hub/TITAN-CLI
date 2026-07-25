from titan.options.analytics.models import (
    DepthAnalysis,
    ExecutabilityAnalysis,
    ExecutionGrade,
    LiquidityRisk,
    SlippageAnalysis,
    SpreadAnalysis,
)


class ExecutabilityAnalyzer:
    """Generate final execution score, grade, and execution risk."""

    name = "ExecutabilityAnalyzer"

    def analyze(
        self,
        spread: SpreadAnalysis,
        depth: DepthAnalysis,
        slippage: SlippageAnalysis,
    ) -> ExecutabilityAnalysis:
        """Combine component outputs into execution-quality output."""

        if not isinstance(spread, SpreadAnalysis):
            raise TypeError("spread must be a SpreadAnalysis.")
        if not isinstance(depth, DepthAnalysis):
            raise TypeError("depth must be a DepthAnalysis.")
        if not isinstance(slippage, SlippageAnalysis):
            raise TypeError("slippage must be a SlippageAnalysis.")

        execution_score = (
            (spread.score * 0.4)
            + (depth.depth_score * 0.3)
            + (slippage.slippage_score * 0.3)
        )
        confidence = (
            (spread.confidence * 0.4)
            + (depth.confidence * 0.3)
            + (slippage.confidence * 0.3)
        )
        warnings = tuple(
            dict.fromkeys(spread.warnings + depth.warnings + slippage.warnings)
        )

        return ExecutabilityAnalysis(
            execution_score=execution_score,
            execution_grade=self._grade(execution_score),
            execution_risk=self._risk(execution_score),
            confidence=confidence,
            warnings=warnings,
            metadata={
                "weights": {
                    "spread": 0.4,
                    "depth": 0.3,
                    "slippage": 0.3,
                }
            },
        )

    def explanation(self, result: ExecutabilityAnalysis) -> str:
        """Generate a structured execution explanation."""

        return (
            f"Execution score is {result.execution_score:.1f}, grade is "
            f"{result.execution_grade.value}, and execution risk is "
            f"{result.execution_risk.value}."
        )

    def _grade(self, score: float) -> ExecutionGrade:
        if score >= 85.0:
            return ExecutionGrade.A
        if score >= 70.0:
            return ExecutionGrade.B
        if score >= 55.0:
            return ExecutionGrade.C
        if score >= 40.0:
            return ExecutionGrade.D
        return ExecutionGrade.F

    def _risk(self, score: float) -> LiquidityRisk:
        if score >= 75.0:
            return LiquidityRisk.LOW
        if score >= 55.0:
            return LiquidityRisk.MODERATE
        if score >= 35.0:
            return LiquidityRisk.HIGH
        return LiquidityRisk.EXTREME
