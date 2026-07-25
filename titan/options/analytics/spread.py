from titan.options.analytics.models import (
    LiquidityQuality,
    OptionLiquiditySnapshot,
    SpreadAnalysis,
)


class SpreadAnalyzer:
    """Analyze top-of-book bid/ask spread for one option contract."""

    name = "SpreadAnalyzer"

    def analyze(self, snapshot: OptionLiquiditySnapshot) -> SpreadAnalysis:
        """Calculate spread, spread percent, score, and quality."""

        if not isinstance(snapshot, OptionLiquiditySnapshot):
            raise TypeError("snapshot must be an OptionLiquiditySnapshot.")

        bid_price = snapshot.bid_price
        ask_price = snapshot.ask_price
        warnings = self._input_warnings(bid_price, ask_price)
        if warnings:
            return SpreadAnalysis(
                spread=None,
                spread_percent=None,
                score=0.0,
                confidence=0.1,
                quality=LiquidityQuality.UNKNOWN,
                warnings=warnings,
                metadata={"available": False},
            )

        assert bid_price is not None
        assert ask_price is not None
        spread = ask_price - bid_price
        midpoint = (ask_price + bid_price) / 2.0
        spread_percent = (spread / midpoint) * 100.0
        score = self._score(spread_percent)

        return SpreadAnalysis(
            spread=spread,
            spread_percent=spread_percent,
            score=score,
            confidence=0.9,
            quality=self._quality(spread_percent),
            warnings=(),
            metadata={
                "available": True,
                "bid_price": bid_price,
                "ask_price": ask_price,
                "midpoint": midpoint,
            },
        )

    def explanation(self, result: SpreadAnalysis) -> str:
        """Generate a structured spread explanation."""

        if result.spread is None or result.spread_percent is None:
            return (
                "Spread could not be calculated because bid/ask prices are incomplete."
            )
        return (
            f"Spread is {result.spread:.2f} "
            f"({result.spread_percent:.2f}%) with {result.quality.value} quality."
        )

    def _input_warnings(
        self,
        bid_price: float | None,
        ask_price: float | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if bid_price is None:
            warnings.append("Bid price is missing.")
        elif bid_price <= 0:
            warnings.append("Bid price must be positive.")

        if ask_price is None:
            warnings.append("Ask price is missing.")
        elif ask_price <= 0:
            warnings.append("Ask price must be positive.")

        if bid_price is not None and ask_price is not None and ask_price < bid_price:
            warnings.append("Ask price is below bid price.")

        return tuple(warnings)

    def _score(self, spread_percent: float) -> float:
        return max(0.0, min(100.0, 100.0 - (spread_percent * 12.5)))

    def _quality(self, spread_percent: float) -> LiquidityQuality:
        if spread_percent <= 1.0:
            return LiquidityQuality.HIGH
        if spread_percent <= 3.0:
            return LiquidityQuality.MODERATE
        return LiquidityQuality.LOW
