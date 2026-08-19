from datetime import datetime
from typing import Any

from titan.options.analytics.models import (
    CalendarResult,
    TermStructureExpiry,
    TermStructureSnapshot,
)

MAX_VALID_IV = 10.0
EVENT_PREMIUM_DEVIATION = 0.02
MIN_EXPIRIES_FOR_CURVE = 2
MIN_EXPIRIES_FOR_EVENT = 3
MIN_EXPIRIES_RELIABLE = 3
MIN_EXPIRIES_PARTIAL = 2


class CalendarAnalyzer:
    """Analyze calendar spread metrics from volatility term structure data.

    Computes front/back IV, calendar spread, curve slope, event premium,
    and related metrics from a collection of expiry data points.
    Consumes supplied values only. Never estimates volatility.
    """

    name = "CalendarAnalyzer"

    def analyze(self, snapshot: TermStructureSnapshot) -> CalendarResult:
        if not isinstance(snapshot, TermStructureSnapshot):
            raise TypeError("snapshot must be a TermStructureSnapshot.")

        if not snapshot.expiries:
            return CalendarResult(warnings=("No expiry data provided.",))

        valid = self._valid_expiries(snapshot.expiries)
        if len(valid) < MIN_EXPIRIES_FOR_CURVE:
            return CalendarResult(
                warnings=(
                    ("Insufficient expiries with valid IV data "
                    f"({len(valid)} available, {MIN_EXPIRIES_FOR_CURVE}+ required)."),
                ),
            )

        front_iv = valid[0][1]
        back_iv = valid[-1][1]
        calendar_spread = back_iv - front_iv

        num_steps = len(valid) - 1
        curve_slope = calendar_spread / num_steps if num_steps > 0 else None

        slopes: list[float] = []
        diffs: list[float] = []
        for i in range(len(valid) - 1):
            diff = valid[i + 1][1] - valid[i][1]
            diffs.append(abs(diff))
            slopes.append(diff)
        average_slope = sum(slopes) / len(slopes) if slopes else None
        max_discontinuity = max(diffs) if diffs else None

        event_premium = self._compute_event_premium(valid)

        confidence = self._calculate_confidence(snapshot.expiries, len(valid))
        warnings = self._generate_warnings(snapshot.expiries, len(valid), event_premium)

        return CalendarResult(
            front_iv=front_iv,
            back_iv=back_iv,
            calendar_spread=calendar_spread,
            event_premium=event_premium,
            curve_slope=curve_slope,
            average_slope=average_slope,
            max_discontinuity=max_discontinuity,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(snapshot),
        )

    def _resolve_iv(self, expiry: TermStructureExpiry) -> float | None:
        iv = expiry.atm_iv if expiry.atm_iv is not None else expiry.average_iv
        return self._safe_iv(iv)

    def _safe_iv(self, iv: float | None) -> float | None:
        if iv is None:
            return None
        if iv <= 0 or iv >= MAX_VALID_IV:
            return None
        return iv

    def _valid_expiries(
        self,
        expiries: tuple[TermStructureExpiry, ...],
    ) -> list[tuple[datetime, float]]:
        sorted_expiries = sorted(expiries, key=lambda e: e.expiry)
        valid: list[tuple[datetime, float]] = []
        for e in sorted_expiries:
            iv = self._resolve_iv(e)
            if iv is not None:
                valid.append((e.expiry, iv))
        return valid

    def _compute_event_premium(
        self,
        valid: list[tuple[datetime, float]],
    ) -> float | None:
        if len(valid) < MIN_EXPIRIES_FOR_EVENT:
            return None

        residuals: list[float] = []
        for i in range(1, len(valid) - 1):
            _, iv_i = valid[i]
            _, iv_prev = valid[i - 1]
            _, iv_next = valid[i + 1]
            interpolated = (iv_prev + iv_next) / 2.0
            residual = iv_i - interpolated
            if residual > EVENT_PREMIUM_DEVIATION:
                residuals.append(residual)

        return max(residuals) if residuals else None

    def _calculate_confidence(
        self,
        expiries: tuple[TermStructureExpiry, ...],
        valid_count: int,
    ) -> float:
        total = len(expiries)
        if total == 0:
            return 0.0
        completeness = valid_count / total
        if valid_count >= MIN_EXPIRIES_RELIABLE:
            return min(0.5 + completeness * 0.4, 0.95)
        if valid_count >= MIN_EXPIRIES_PARTIAL:
            return min(0.2 + completeness * 0.3, 0.60)
        return 0.0

    def _generate_warnings(
        self,
        expiries: tuple[TermStructureExpiry, ...],
        valid_count: int,
        event_premium: float | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        total = len(expiries)
        if valid_count < total:
            warnings.append(
                f"Missing IV data for {total - valid_count} of {total} expiries."
            )
        if valid_count < MIN_EXPIRIES_RELIABLE:
            warnings.append(
                f"Insufficient expiries for reliable analysis "
                f"({valid_count} with IV, {MIN_EXPIRIES_RELIABLE}+ recommended)."
            )
        if event_premium is not None:
            warnings.append(
                f"Event premium detected: {event_premium:.2%} above interpolated curve."
            )
        return tuple(warnings)

    def _metadata(self, snapshot: TermStructureSnapshot) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "underlying": snapshot.underlying,
            "timestamp": snapshot.timestamp.isoformat() if snapshot.timestamp else None,
            "expiry_count": len(snapshot.expiries),
        }
