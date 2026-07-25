from titan.options.analytics.models import (
    DepthAnalysis,
    LiquidityQuality,
    OptionLiquiditySnapshot,
)

TARGET_DISPLAYED_QUANTITY = 2000


class DepthAnalyzer:
    """Analyze displayed bid/ask depth for one option contract."""

    name = "DepthAnalyzer"

    def analyze(self, snapshot: OptionLiquiditySnapshot) -> DepthAnalysis:
        """Evaluate bid size, ask size, balance, and depth quality."""

        if not isinstance(snapshot, OptionLiquiditySnapshot):
            raise TypeError("snapshot must be an OptionLiquiditySnapshot.")

        bid_size = snapshot.bid_quantity
        ask_size = snapshot.ask_quantity
        warnings = self._input_warnings(bid_size, ask_size)
        if bid_size is None or ask_size is None:
            return DepthAnalysis(
                bid_size=bid_size,
                ask_size=ask_size,
                order_book_balance=None,
                depth_score=0.0,
                confidence=0.1,
                quality=LiquidityQuality.UNKNOWN,
                warnings=warnings,
                metadata={"available": False},
            )

        balance = self._balance(bid_size, ask_size)
        score = self._score(bid_size, ask_size, balance)
        confidence = 0.8 if not warnings else 0.6

        return DepthAnalysis(
            bid_size=bid_size,
            ask_size=ask_size,
            order_book_balance=balance,
            depth_score=score,
            confidence=confidence,
            quality=self._quality(score),
            warnings=warnings,
            metadata={
                "available": True,
                "total_displayed_quantity": bid_size + ask_size,
                "future_depth_levels": (),
            },
        )

    def explanation(self, result: DepthAnalysis) -> str:
        """Generate a structured depth explanation."""

        if result.order_book_balance is None:
            return "Depth could not be evaluated because bid/ask quantities are incomplete."
        return (
            f"Displayed depth score is {result.depth_score:.1f}; "
            f"bid size is {result.bid_size}, ask size is {result.ask_size}, "
            f"and balance is {result.order_book_balance:.2f}."
        )

    def _input_warnings(
        self,
        bid_size: int | None,
        ask_size: int | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if bid_size is None:
            warnings.append("Bid quantity is missing.")
        elif bid_size < 0:
            warnings.append("Bid quantity cannot be negative.")

        if ask_size is None:
            warnings.append("Ask quantity is missing.")
        elif ask_size < 0:
            warnings.append("Ask quantity cannot be negative.")

        if bid_size == 0:
            warnings.append("Bid quantity is zero.")
        if ask_size == 0:
            warnings.append("Ask quantity is zero.")

        return tuple(warnings)

    def _balance(self, bid_size: int, ask_size: int) -> float:
        larger = max(bid_size, ask_size)
        if larger == 0:
            return 0.0
        return min(bid_size, ask_size) / larger

    def _score(self, bid_size: int, ask_size: int, balance: float) -> float:
        total_size = max(0, bid_size) + max(0, ask_size)
        size_score = min(70.0, (total_size / TARGET_DISPLAYED_QUANTITY) * 70.0)
        balance_score = balance * 30.0
        return max(0.0, min(100.0, size_score + balance_score))

    def _quality(self, score: float) -> LiquidityQuality:
        if score >= 70.0:
            return LiquidityQuality.HIGH
        if score >= 40.0:
            return LiquidityQuality.MODERATE
        return LiquidityQuality.LOW
