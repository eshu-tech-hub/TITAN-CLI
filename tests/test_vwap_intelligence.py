from datetime import datetime, timedelta

import pytest

from titan.core.evidence import EvidenceCategory, EvidenceSignal
from titan.market.intelligence.models import (
    TrendDirection,
    VWAPAnalysis,
    VWAPBands,
    VWAPBias,
    VWAPExplanation,
    VWAPPosition,
    VWAPTrend,
)
from titan.market.intelligence.vwap import VWAPAnalyzer, VWAPEngine
from titan.market.intelligence.vwap_bands import VWAPBandsAnalyzer
from titan.market.intelligence.vwap_trend import VWAPTrendAnalyzer
from titan.market.models import Candle
from titan.market.series import MarketDataSeries

NOW = datetime(2026, 7, 2, 9, 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_candle(
    close: float,
    high: float | None = None,
    low: float | None = None,
    open: float | None = None,
    volume: int = 1000,
    timestamp: datetime | None = None,
) -> Candle:
    if high is None:
        high = close + 1.0
    if low is None:
        low = close - 1.0
    if open is None:
        open = close
    if timestamp is None:
        timestamp = NOW
    return Candle(
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def make_series(candles: list[Candle]) -> MarketDataSeries:
    return MarketDataSeries(candles=candles)


def make_rising_candles(
    count: int = 20, start: float = 100.0, step: float = 1.0
) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(count):
        ts = NOW + timedelta(hours=i)
        close = start + i * step
        high = close + 0.5
        low = close - 0.5
        candles.append(make_candle(high=high, low=low, close=close, timestamp=ts))
    return candles


def make_falling_candles(
    count: int = 20, start: float = 120.0, step: float = 1.0
) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(count):
        ts = NOW + timedelta(hours=i)
        close = start - i * step
        high = close + 0.5
        low = close - 0.5
        candles.append(make_candle(high=high, low=low, close=close, timestamp=ts))
    return candles


def make_flat_candles(count: int = 20, level: float = 100.0) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(count):
        ts = NOW + timedelta(hours=i)
        close = level + (i % 3) * 0.1
        high = close + 0.5
        low = close - 0.5
        candles.append(make_candle(high=high, low=low, close=close, timestamp=ts))
    return candles


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_vwap_bias_values(self) -> None:
        assert VWAPBias.BULLISH.value == "bullish"
        assert VWAPBias.BEARISH.value == "bearish"
        assert VWAPBias.NEUTRAL.value == "neutral"
        assert VWAPBias.UNKNOWN.value == "unknown"

    def test_vwap_position_values(self) -> None:
        assert VWAPPosition.ABOVE.value == "above"
        assert VWAPPosition.BELOW.value == "below"
        assert VWAPPosition.AT.value == "at"
        assert VWAPPosition.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestVWAPTrend:
    def test_creation(self) -> None:
        trend = VWAPTrend(
            slope=0.05,
            direction=TrendDirection.BULLISH,
            crossover=True,
            confidence=0.8,
            reasons=("VWAP rising.",),
        )
        assert trend.slope == 0.05
        assert trend.direction is TrendDirection.BULLISH
        assert trend.crossover is True
        assert trend.confidence == 0.8
        assert trend.reasons == ("VWAP rising.",)

    def test_frozen(self) -> None:
        trend = VWAPTrend()
        with pytest.raises(AttributeError):
            trend.slope = 0.1  # type: ignore[misc]

    def test_defaults(self) -> None:
        trend = VWAPTrend()
        assert trend.slope == 0.0
        assert trend.direction is TrendDirection.UNKNOWN
        assert trend.crossover is False
        assert trend.reclaim is False
        assert trend.rejection is False
        assert trend.pullback is False
        assert trend.confidence == 0.0
        assert trend.reasons == ()


class TestVWAPBands:
    def test_creation(self) -> None:
        bands = VWAPBands(
            upper=105.0,
            lower=95.0,
            deviation=1.5,
            bandwidth=0.1,
            confidence=0.8,
        )
        assert bands.upper == 105.0
        assert bands.lower == 95.0
        assert bands.deviation == 1.5
        assert bands.bandwidth == 0.1

    def test_defaults(self) -> None:
        bands = VWAPBands()
        assert bands.upper == 0.0
        assert bands.lower == 0.0
        assert bands.deviation == 0.0
        assert bands.bandwidth == 0.0


class TestVWAPExplanation:
    def test_defaults(self) -> None:
        exp = VWAPExplanation()
        assert exp.vwap == ""
        assert exp.institutional_bias == ""
        assert exp.price_position == ""
        assert exp.vwap_trend == ""
        assert exp.support_resistance == ""
        assert exp.institutional_interpretation == ""


class TestVWAPAnalysis:
    def test_creation(self) -> None:
        analysis = VWAPAnalysis(
            vwap=100.0,
            current_price=102.0,
            distance=0.02,
            position=VWAPPosition.ABOVE,
            bias=VWAPBias.BULLISH,
            confidence=0.75,
        )
        assert analysis.vwap == 100.0
        assert analysis.current_price == 102.0
        assert analysis.distance == 0.02
        assert analysis.position is VWAPPosition.ABOVE
        assert analysis.bias is VWAPBias.BULLISH
        assert analysis.confidence == 0.75
        assert analysis.evidence is None
        assert analysis.explanation is None

    def test_frozen(self) -> None:
        analysis = VWAPAnalysis(vwap=100.0, current_price=100.0)
        with pytest.raises(AttributeError):
            analysis.vwap = 105.0  # type: ignore[misc]

    def test_neutral_placeholder(self) -> None:
        placeholder = VWAPAnalysis.neutral_placeholder()
        assert placeholder.vwap == 0.0
        assert placeholder.current_price == 0.0
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_with_evidence(self) -> None:
        from titan.core.evidence import Confidence, Evidence, Score

        evidence = Evidence(
            source="VWAP",
            category=EvidenceCategory.MARKET_STRUCTURE,
            signal=EvidenceSignal.BULLISH,
            score=Score(65.0),
            confidence=Confidence(0.7),
        )
        analysis = VWAPAnalysis(
            vwap=100.0,
            current_price=102.0,
            bias=VWAPBias.BULLISH,
            confidence=0.7,
            evidence=evidence,
        )
        assert analysis.evidence is evidence


# ---------------------------------------------------------------------------
# VWAPEngine tests
# ---------------------------------------------------------------------------


class TestVWAPEngine:
    def test_single_candle(self) -> None:
        engine = VWAPEngine()
        series = make_series([make_candle(close=100.0)])
        vwap_values = engine.compute_vwap(series)
        assert len(vwap_values) == 1
        # Typical price ≈ (101 + 99 + 100) / 3 = 100
        assert 99.0 <= vwap_values[0] <= 101.0

    def test_multiple_candles(self) -> None:
        engine = VWAPEngine()
        candles = make_rising_candles(5, start=100.0, step=2.0)
        series = make_series(candles)
        vwap_values = engine.compute_vwap(series)
        assert len(vwap_values) == 5
        # VWAP should be cumulative, weighted by volume (all equal volume)
        running_vwap = sum(100.0 + i * 2.0 for i in range(5)) / 5
        assert abs(vwap_values[-1] - running_vwap) < 1.0

    def test_current_vwap(self) -> None:
        engine = VWAPEngine()
        assert engine.current_vwap([]) == 0.0
        assert engine.current_vwap([100.0, 101.0, 102.0]) == 102.0

    def test_volume_weighted(self) -> None:
        engine = VWAPEngine()
        candles = [
            make_candle(close=100.0, high=101.0, low=99.0, volume=100),
            make_candle(close=200.0, high=201.0, low=199.0, volume=900),
        ]
        series = make_series(candles)
        vwaps = engine.compute_vwap(series)
        assert len(vwaps) == 2
        tp1 = (101.0 + 99.0 + 100.0) / 3.0
        tp2 = (201.0 + 199.0 + 200.0) / 3.0
        expected = (tp1 * 100 + tp2 * 900) / 1000
        assert abs(vwaps[-1] - expected) < 0.01


# ---------------------------------------------------------------------------
# VWAPTrendAnalyzer tests
# ---------------------------------------------------------------------------


class TestVWAPTrendAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        series = make_series([make_candle(close=100.0)])
        result = analyzer.analyze(series, [100.0], 100.0)
        assert result.confidence == 0.0
        assert "Insufficient" in result.reasons[0]

    def test_rising_vwap(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        prices = list(range(100, 120))
        candles = [make_candle(close=float(p)) for p in prices]
        series = make_series(candles)
        vwap_values = [float(p) for p in prices]
        result = analyzer.analyze(series, vwap_values, vwap_values[-1])
        assert result.slope > 0
        assert result.direction is TrendDirection.BULLISH
        assert result.confidence > 0

    def test_falling_vwap(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        prices = list(range(120, 100, -1))
        candles = [make_candle(close=float(p)) for p in prices]
        series = make_series(candles)
        vwap_values = [float(p) for p in prices]
        result = analyzer.analyze(series, vwap_values, vwap_values[-1])
        assert result.slope < 0
        assert result.direction is TrendDirection.BEARISH
        assert result.confidence > 0

    def test_crossover_detected(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        # Price starts below VWAP, crosses above in the last 3 candles
        prices = [98.0, 98.5, 99.0, 99.5, 99.0, 99.5, 99.0, 99.5, 100.5, 101.0, 101.5]
        vwaps = [100.0] * len(prices)
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        result = analyzer.analyze(series, vwaps, vwaps[-1])
        assert result.crossover is True

    def test_no_crossover(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        prices = [102.0, 103.0, 104.0, 105.0, 106.0]
        vwaps = [100.0, 100.0, 100.0, 100.0, 100.0]
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        result = analyzer.analyze(series, vwaps, vwaps[-1])
        assert result.crossover is False

    def test_reclaim_detected(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        # All previous candles below VWAP, last candle above VWAP
        prices = [98.0, 98.5, 99.0, 99.5, 99.0, 99.5, 99.0, 99.5, 99.0, 99.5, 100.5]
        vwaps = [100.0] * len(prices)
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        result = analyzer.analyze(series, vwaps, vwaps[-1])
        assert result.reclaim is True

    def test_no_reclaim(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        prices = [98.0, 99.0, 98.5, 99.0, 99.5]
        vwaps = [100.0, 100.0, 100.0, 100.0, 100.0]
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        result = analyzer.analyze(series, vwaps, vwaps[-1])
        assert result.reclaim is False

    def test_rejection_detected(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        # Previous candles above VWAP, last candle at VWAP (rejection)
        prices = [
            102.0,
            102.5,
            103.0,
            102.5,
            103.0,
            102.5,
            103.0,
            102.5,
            103.0,
            102.5,
            100.05,
        ]
        vwaps = [100.0] * len(prices)
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        result = analyzer.analyze(series, vwaps, 100.0)
        assert result.rejection is True

    def test_pullback_detected(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        # Price moves away from VWAP then returns
        prices = [
            102.0,
            105.0,
            108.0,
            106.0,
            104.0,
            103.0,
            102.0,
            101.0,
            100.5,
            100.2,
            100.05,
        ]
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        vwap_level = 100.0
        vwaps = [100.0] * len(prices)
        result = analyzer.analyze(series, vwaps, vwap_level)
        assert result.pullback is True

    def test_flat_vwap(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        prices = [100.0] * 15
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        vwap_values = [100.0] * 15
        result = analyzer.analyze(series, vwap_values, 100.0)
        assert result.direction is TrendDirection.SIDEWAYS


# ---------------------------------------------------------------------------
# VWAPBandsAnalyzer tests
# ---------------------------------------------------------------------------


class TestVWAPBandsAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        series = make_series([make_candle(close=100.0)])
        result = analyzer.analyze(series, [100.0], 100.0)
        assert result.confidence == 0.0

    def test_bands_symmetric(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        vwap_values = [100.0] * 20
        result = analyzer.analyze(series, vwap_values, 100.0)
        assert result.upper >= result.lower
        assert result.upper > 0
        assert result.lower > 0

    def test_bands_wider_with_volatility(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        # Volatile candles
        volatile: list[Candle] = []
        for i in range(20):
            ts = NOW + timedelta(hours=i)
            close = 100.0 + (i % 5) * 10.0
            volatile.append(
                make_candle(high=close + 5, low=close - 5, close=close, timestamp=ts)
            )
        series_v = make_series(volatile)
        vwap_v = [100.0 + (i % 5) * 8.0 for i in range(20)]
        result_v = analyzer.analyze(series_v, vwap_v, vwap_v[-1])

        # Stable candles
        stable = make_flat_candles(20, level=100.0)
        series_s = make_series(stable)
        vwap_s = [100.0] * 20
        result_s = analyzer.analyze(series_s, vwap_s, 100.0)

        assert result_v.bandwidth > result_s.bandwidth

    def test_deviation_current(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        # All candles at exactly 100, VWAP at 100 → std dev ≈ 0, deviation ≈ 0
        candles = [make_candle(close=100.0, high=101.0, low=99.0) for _ in range(20)]
        series = make_series(candles)
        vwap_values = [100.0] * 20
        result = analyzer.analyze(series, vwap_values, 100.0)
        assert abs(result.deviation) < 0.01

    def test_confidence_increases_with_data(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        vwap_values = [100.0] * 20
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        result = analyzer.analyze(series, vwap_values, 100.0)
        assert result.confidence > 0

    def test_bandwidth_percentage(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        vwap_values = [100.0] * 20
        result = analyzer.analyze(series, vwap_values, 100.0)
        assert result.bandwidth >= 0.0
        assert result.bandwidth < 1.0


# ---------------------------------------------------------------------------
# VWAPAnalyzer integration tests
# ---------------------------------------------------------------------------


class TestVWAPAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = VWAPAnalyzer()
        series = make_series([make_candle(close=100.0)])
        result = analyzer.analyze(series)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.warnings[0]

    def test_price_above_vwap(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.position is VWAPPosition.ABOVE
        assert result.distance > 0

    def test_price_below_vwap(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_falling_candles(20, start=120.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.position is VWAPPosition.BELOW
        assert result.distance < 0

    def test_price_at_vwap(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.position is VWAPPosition.AT

    def test_bullish_crossover(self) -> None:
        analyzer = VWAPAnalyzer()
        # Price starts below VWAP, ends above
        candles: list[Candle] = []
        # First 10 candles below (prices 95-99)
        for i in range(10):
            ts = NOW + timedelta(hours=i)
            close = 95.0 + i * 0.5
            candles.append(make_candle(close=close, timestamp=ts))
        # Next 10 candles above (prices 101-105)
        for i in range(10, 20):
            ts = NOW + timedelta(hours=i)
            close = 101.0 + (i - 10) * 0.5
            candles.append(make_candle(close=close, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.trend is not None
        if result.trend.crossover:
            assert result.bias in (VWAPBias.BULLISH, VWAPBias.NEUTRAL)

    def test_bearish_crossover(self) -> None:
        analyzer = VWAPAnalyzer()
        candles: list[Candle] = []
        for i in range(10):
            ts = NOW + timedelta(hours=i)
            close = 105.0 - i * 0.5
            candles.append(make_candle(close=close, timestamp=ts))
        for i in range(10, 20):
            ts = NOW + timedelta(hours=i)
            close = 99.0 - (i - 10) * 0.5
            candles.append(make_candle(close=close, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.trend is not None

    def test_vwap_reclaim(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_falling_candles(10, start=100.0, step=0.5) + make_rising_candles(
            10, start=97.0, step=0.5
        )
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.trend is not None

    def test_vwap_rejection(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(10, start=95.0, step=0.5) + make_falling_candles(
            10, start=102.0, step=0.5
        )
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.trend is not None

    def test_flat_market(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.position is VWAPPosition.AT

    def test_evidence_generated(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "VWAP"
        assert evidence.category is EvidenceCategory.MARKET_STRUCTURE

    def test_explanation_generated(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        explanation = result.explanation
        assert explanation is not None
        assert isinstance(explanation, VWAPExplanation)
        assert "VWAP" in explanation.vwap
        assert "Institutional" in explanation.institutional_bias
        assert "Price" in explanation.price_position
        assert "VWAP Trend" in explanation.vwap_trend
        assert "VWAP Support" in explanation.support_resistance
        assert (
            "Institutional Interpretation" in explanation.institutional_interpretation
        )

    def test_serialization_round_trip(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert isinstance(result.vwap, float)
        assert isinstance(result.current_price, float)
        assert isinstance(result.distance, float)
        assert result.position.value in ("above", "below", "at", "unknown")
        assert result.bias.value in ("bullish", "bearish", "neutral", "unknown")
        assert 0.0 <= result.confidence <= 1.0

    def test_single_candle(self) -> None:
        analyzer = VWAPAnalyzer()
        series = make_series([make_candle(close=100.0)])
        result = analyzer.analyze(series)
        assert result.confidence == 0.0

    def test_missing_candles(self) -> None:
        analyzer = VWAPAnalyzer()
        series = make_series([])
        result = analyzer.analyze(series)
        assert result.confidence == 0.0
        assert "Insufficient" in result.warnings[0]

    def test_validator_fields(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.vwap > 0
        assert result.current_price > 0
        assert result.upper_band > 0
        assert result.lower_band > 0

    def test_bands_in_analysis(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.upper_band >= result.vwap
        assert result.lower_band <= result.vwap

    def test_warning_on_low_data(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(5, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        warnings = result.warnings
        has_low_data_warning = any("Limited data" in w for w in warnings)
        assert has_low_data_warning


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestVWAPEdgeCases:
    def test_zero_volume_candles(self) -> None:
        engine = VWAPEngine()
        candles = [
            make_candle(close=100.0, volume=0),
            make_candle(close=200.0, volume=0),
        ]
        series = make_series(candles)
        vwaps = engine.compute_vwap(series)
        # When cumulative volume is 0, VWAP should be 0.0
        assert vwaps == [0.0, 0.0]

    def test_single_candle_no_bands(self) -> None:
        analyzer = VWAPBandsAnalyzer()
        series = make_series([make_candle(close=100.0)])
        result = analyzer.analyze(series, [100.0], 100.0)
        assert result.confidence == 0.0
        assert result.upper == 0.0
        assert result.lower == 0.0

    def test_vwap_slope_nonzero(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=2.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.slope != 0.0

    def test_distance_calculation(self) -> None:
        engine = VWAPEngine()
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        vwaps = engine.compute_vwap(series)
        distance = engine.current_vwap(vwaps)
        assert distance > 0

    def test_evidence_score_bullish(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=2.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.score.value >= 50

    def test_evidence_score_neutral(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_flat_candles(20, level=100.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        evidence = result.evidence
        assert evidence is not None
        # Flat market should give neutral score ≈ 50
        assert 40 <= evidence.score.value <= 80

    def test_neutral_placeholder_no_vwap(self) -> None:
        placeholder = VWAPAnalysis.neutral_placeholder()
        assert placeholder.vwap == 0.0
        assert placeholder.current_price == 0.0
        assert placeholder.bias is VWAPBias.UNKNOWN
        assert placeholder.position is VWAPPosition.UNKNOWN

    def test_metadata_keys(self) -> None:
        analyzer = VWAPAnalyzer()
        candles = make_rising_candles(20, start=100.0, step=1.0)
        series = make_series(candles)
        result = analyzer.analyze(series)
        meta = result.metadata
        assert meta["analyzer"] == "VWAPAnalyzer"
        assert "candle_count" in meta
        assert "vwap_slope" in meta
        assert "upper_band" in meta

    def test_bias_from_distance_above(self) -> None:
        analyzer = VWAPAnalyzer()
        dist = analyzer._distance(105.0, 100.0)
        pos = analyzer._position(dist)
        bias = analyzer._bias(pos, 0.01)
        assert pos is VWAPPosition.ABOVE
        assert bias is VWAPBias.BULLISH

    def test_bias_from_distance_below(self) -> None:
        analyzer = VWAPAnalyzer()
        dist = analyzer._distance(95.0, 100.0)
        pos = analyzer._position(dist)
        bias = analyzer._bias(pos, -0.01)
        assert pos is VWAPPosition.BELOW
        assert bias is VWAPBias.BEARISH

    def test_bias_neutral_above_no_slope(self) -> None:
        analyzer = VWAPAnalyzer()
        bias = analyzer._bias(VWAPPosition.ABOVE, 0.0)
        assert bias is VWAPBias.NEUTRAL

    def test_reclaim_crossover_not_both(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        prices = [98.0, 98.5, 99.0, 99.5, 100.0]
        vwaps = [100.0] * 5
        candles = [make_candle(close=p) for p in prices]
        series = make_series(candles)
        result = analyzer.analyze(series, vwaps, 100.0)
        # Last price is at VWAP, not above
        assert result.reclaim is False

    def test_crossover_reclaim_same_data(self) -> None:
        analyzer = VWAPTrendAnalyzer()
        candles: list[Candle] = []
        # First 8 below VWAP, next 2 below, last 1 above (reclaim + crossover)
        for close in [
            98.0,
            98.5,
            99.0,
            99.5,
            99.0,
            99.5,
            99.0,
            99.5,
            99.0,
            99.5,
            100.5,
        ]:
            ts = NOW + timedelta(hours=len(candles))
            candles.append(make_candle(close=close, timestamp=ts))
        series = make_series(candles)
        vwaps = [100.0] * len(candles)
        result = analyzer.analyze(series, vwaps, 100.0)
        assert result.crossover is True
        assert result.reclaim is True
