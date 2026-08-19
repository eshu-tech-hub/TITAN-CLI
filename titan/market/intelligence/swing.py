"""Swing Analyzer.

Identifies swing highs, swing lows, and market structure breaks (BOS, CHOCH)
from supplied MarketDataSeries.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import (
    BreakType,
    SwingPoint,
    SwingStructure,
)
from titan.market.series import MarketDataSeries

SWING_LOOKBACK = 2


class SwingAnalyzer:
    """Analyse swing points and market structure breaks.

    Identifies swing highs (local peaks) and swing lows (local troughs)
    and evaluates whether price structure is trending or breaking.
    """

    name = "SwingAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
        lookback: int = SWING_LOOKBACK,
    ) -> SwingStructure:
        """Identify swing points and structure breaks.

        Args:
            series: Market data series with OHLCV candles.
            lookback: Number of candles to check on each side of a
                potential swing point.

        Returns:
            Swing structure assessment.
        """

        reasons: list[str] = []

        if len(series) < lookback * 2 + 1:
            return SwingStructure(
                confidence=0.0,
                reasons=(
                    (f"Insufficient data: need {lookback * 2 + 1} candles, "
                    f"got {len(series)}."),
                ),
            )

        highs = series.highs
        lows = series.lows
        swing_highs: list[SwingPoint] = []
        swing_lows: list[SwingPoint] = []

        for i in range(lookback, len(series) - lookback):
            high = highs[i]
            low = lows[i]

            is_high = all(
                high > highs[j] for j in range(i - lookback, i + lookback + 1) if j != i
            )
            is_low = all(
                low < lows[j] for j in range(i - lookback, i + lookback + 1) if j != i
            )

            if is_high:
                swing_highs.append(
                    SwingPoint(
                        index=i,
                        price=high,
                        high=high,
                        low=low,
                        is_swing_high=True,
                        is_swing_low=False,
                    )
                )
            if is_low:
                swing_lows.append(
                    SwingPoint(
                        index=i,
                        price=low,
                        high=high,
                        low=low,
                        is_swing_high=False,
                        is_swing_low=True,
                    )
                )

        higher_highs, lower_highs = self._classify_highs(swing_highs)
        higher_lows, lower_lows = self._classify_lows(swing_lows)
        break_type = self._detect_break(
            swing_highs,
            swing_lows,
            higher_highs,
            higher_lows,
            lower_highs,
            lower_lows,
        )
        confidence = self._confidence(swing_highs, swing_lows, break_type)
        reasons.extend(
            self._reasons(
                swing_highs,
                swing_lows,
                higher_highs,
                higher_lows,
                lower_highs,
                lower_lows,
                break_type,
            )
        )

        return SwingStructure(
            swing_highs=tuple(swing_highs),
            swing_lows=tuple(swing_lows),
            higher_highs=tuple(higher_highs),
            higher_lows=tuple(higher_lows),
            lower_highs=tuple(lower_highs),
            lower_lows=tuple(lower_lows),
            break_type=break_type,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _classify_highs(
        self,
        swing_highs: list[SwingPoint],
    ) -> tuple[list[float], list[float]]:
        higher: list[float] = []
        lower: list[float] = []

        for i in range(1, len(swing_highs)):
            prev = swing_highs[i - 1].price
            curr = swing_highs[i].price
            if curr > prev:
                higher.append(curr)
            elif curr < prev:
                lower.append(curr)

        return higher, lower

    def _classify_lows(
        self,
        swing_lows: list[SwingPoint],
    ) -> tuple[list[float], list[float]]:
        higher: list[float] = []
        lower: list[float] = []

        for i in range(1, len(swing_lows)):
            prev = swing_lows[i - 1].price
            curr = swing_lows[i].price
            if curr > prev:
                higher.append(curr)
            elif curr < prev:
                lower.append(curr)

        return higher, lower

    def _detect_break(
        self,
        swing_highs: list[SwingPoint],
        swing_lows: list[SwingPoint],
        higher_highs: list[float],
        higher_lows: list[float],
        lower_highs: list[float],
        lower_lows: list[float],
    ) -> BreakType:
        if not swing_highs or not swing_lows:
            return BreakType.NONE

        if higher_highs and higher_lows:
            uptrend_established = len(higher_highs) >= 2 and len(higher_lows) >= 2
            if uptrend_established and lower_lows:
                recent_lows = lower_lows[-3:] if len(lower_lows) >= 3 else lower_lows
                if any(v < higher_lows[-1] for v in recent_lows):
                    return BreakType.CHOCH
                return BreakType.BOS

        if lower_highs and lower_lows:
            downtrend_established = len(lower_highs) >= 2 and len(lower_lows) >= 2
            if downtrend_established and higher_highs:
                recent_highs = (
                    higher_highs[-3:] if len(higher_highs) >= 3 else higher_highs
                )
                if any(h > lower_highs[-1] for h in recent_highs):
                    return BreakType.CHOCH
                return BreakType.BOS

        if higher_highs and lower_lows:
            return BreakType.CHOCH

        if higher_lows and lower_highs:
            return BreakType.CHOCH

        return BreakType.NONE

    def _confidence(
        self,
        swing_highs: list[SwingPoint],
        swing_lows: list[SwingPoint],
        break_type: BreakType,
    ) -> float:
        total_swings = len(swing_highs) + len(swing_lows)

        if total_swings == 0:
            return 0.0

        base = min(1.0, total_swings / 10)
        if break_type is not BreakType.NONE:
            base = min(1.0, base + 0.2)

        return base

    def _reasons(
        self,
        swing_highs: list[SwingPoint],
        swing_lows: list[SwingPoint],
        higher_highs: list[float],
        higher_lows: list[float],
        lower_highs: list[float],
        lower_lows: list[float],
        break_type: BreakType,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Identified {len(swing_highs)} swing high(s).")
        reasons.append(f"Identified {len(swing_lows)} swing low(s).")

        if higher_highs:
            reasons.append(f"{len(higher_highs)} higher high(s) detected.")
        if higher_lows:
            reasons.append(f"{len(higher_lows)} higher low(s) detected.")
        if lower_highs:
            reasons.append(f"{len(lower_highs)} lower high(s) detected.")
        if lower_lows:
            reasons.append(f"{len(lower_lows)} lower low(s) detected.")

        if break_type is BreakType.BOS:
            reasons.append("Break of Structure (BOS) detected.")
        elif break_type is BreakType.CHOCH:
            reasons.append("Change of Character (CHOCH) detected.")
        else:
            reasons.append("No structure break detected.")

        return reasons
