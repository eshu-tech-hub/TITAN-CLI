from datetime import datetime, timedelta

import pytest

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.market.intelligence import (
    BreakType,
    MarketStructureAnalysis,
    MarketStructureAnalyzer,
    MarketStructureExplanation,
    StructureState,
    SupportResistanceAnalyzer,
    SupportResistanceStructure,
    SwingAnalyzer,
    SwingPoint,
    SwingStructure,
    TrendAnalyzer,
    TrendDirection,
    TrendStructure,
)
from titan.market.models import Candle
from titan.market.series import MarketDataSeries

NOW = datetime(2026, 7, 2, 9, 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_candle(
    high: float,
    low: float,
    close: float,
    open: float | None = None,
    volume: int = 1000,
    timestamp: datetime | None = None,
) -> Candle:
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


def make_bullish_candles(count: int = 60) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(count):
        ts = NOW + timedelta(hours=i)
        if i < 20:
            close = 100.0 + (i % 3) * 0.2
        else:
            close = 298.0 + (i % 5) * 0.5
        high = close + 0.5
        low = close - 0.5
        candles.append(make_candle(high=high, low=low, close=close, timestamp=ts))
    return candles


def make_bearish_candles(count: int = 60) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(count):
        ts = NOW + timedelta(hours=i)
        if i < 20:
            close = 298.0 + (i % 3) * 0.2
        else:
            close = 100.0 + (i % 5) * 0.5
        high = close + 0.5
        low = close - 0.5
        candles.append(make_candle(high=high, low=low, close=close, timestamp=ts))
    return candles


def make_sideways_candles(count: int = 60) -> list[Candle]:
    candles: list[Candle] = []
    base = 100.0
    for i in range(count):
        ts = NOW + timedelta(hours=i)
        close = base + ((i % 10) - 5) * 0.3
        high = close + 0.5
        low = close - 0.5
        candles.append(make_candle(high=high, low=low, close=close, timestamp=ts))
    return candles


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_trend_direction_values(self) -> None:
        assert TrendDirection.BULLISH.value == "bullish"
        assert TrendDirection.BEARISH.value == "bearish"
        assert TrendDirection.SIDEWAYS.value == "sideways"
        assert TrendDirection.UNKNOWN.value == "unknown"

    def test_structure_state_values(self) -> None:
        assert StructureState.TRENDING.value == "trending"
        assert StructureState.RANGING.value == "ranging"
        assert StructureState.TRANSITION.value == "transition"
        assert StructureState.UNKNOWN.value == "unknown"

    def test_break_type_values(self) -> None:
        assert BreakType.NONE.value == "none"
        assert BreakType.BOS.value == "bos"
        assert BreakType.CHOCH.value == "choch"


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestTrendStructure:
    def test_creation(self) -> None:
        ts = TrendStructure(
            primary=TrendDirection.BULLISH,
            secondary=TrendDirection.BULLISH,
            strength=0.8,
            confidence=0.7,
            reasons=("Price above SMA.",),
        )
        assert ts.primary is TrendDirection.BULLISH
        assert ts.strength == 0.8
        assert ts.confidence == 0.7
        assert ts.reasons == ("Price above SMA.",)

    def test_frozen(self) -> None:
        ts = TrendStructure(
            primary=TrendDirection.UNKNOWN,
            secondary=TrendDirection.UNKNOWN,
            strength=0.0,
            confidence=0.0,
        )
        with pytest.raises(AttributeError):
            ts.primary = TrendDirection.BULLISH  # type: ignore[misc]

    def test_defaults(self) -> None:
        ts = TrendStructure(
            primary=TrendDirection.UNKNOWN,
            secondary=TrendDirection.UNKNOWN,
            strength=0.0,
            confidence=0.0,
        )
        assert ts.reasons == ()


class TestSwingPoint:
    def test_creation(self) -> None:
        sp = SwingPoint(
            index=5,
            price=105.0,
            high=105.5,
            low=104.5,
            is_swing_high=True,
            is_swing_low=False,
        )
        assert sp.index == 5
        assert sp.price == 105.0
        assert sp.is_swing_high is True
        assert sp.is_swing_low is False


class TestSwingStructure:
    def test_defaults(self) -> None:
        ss = SwingStructure()
        assert ss.swing_highs == ()
        assert ss.swing_lows == ()
        assert ss.break_type is BreakType.NONE
        assert ss.confidence == 0.0


class TestSupportResistanceStructure:
    def test_creation(self) -> None:
        sr = SupportResistanceStructure(
            support_levels=(100.0, 98.0),
            resistance_levels=(105.0, 108.0),
            confidence=0.7,
        )
        assert len(sr.support_levels) == 2
        assert len(sr.resistance_levels) == 2
        assert sr.confidence == 0.7


class TestMarketStructureExplanation:
    def test_defaults(self) -> None:
        exp = MarketStructureExplanation()
        assert exp.trend == ""


class TestMarketStructureAnalysis:
    def test_creation(self) -> None:
        analysis = MarketStructureAnalysis(
            primary_trend=TrendDirection.BULLISH,
            secondary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            support_levels=(100.0,),
            resistance_levels=(110.0,),
            trend_strength=0.8,
            confidence=0.75,
        )
        assert analysis.primary_trend is TrendDirection.BULLISH
        assert analysis.structure_state is StructureState.TRENDING
        assert analysis.trend_strength == 0.8
        assert analysis.confidence == 0.75
        assert analysis.evidence is None
        assert analysis.explanation is None

    def test_frozen(self) -> None:
        analysis = MarketStructureAnalysis(
            primary_trend=TrendDirection.UNKNOWN,
            secondary_trend=TrendDirection.UNKNOWN,
            structure_state=StructureState.UNKNOWN,
        )
        with pytest.raises(AttributeError):
            analysis.primary_trend = TrendDirection.BULLISH  # type: ignore[misc]

    def test_neutral_placeholder(self) -> None:
        placeholder = MarketStructureAnalysis.neutral_placeholder()
        assert placeholder.primary_trend is TrendDirection.UNKNOWN
        assert placeholder.structure_state is StructureState.UNKNOWN
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_with_evidence(self) -> None:
        evidence = Evidence(
            source="test",
            category=EvidenceCategory.MARKET_STRUCTURE,
            signal=EvidenceSignal.NEUTRAL,
            score=Score(50.0),
            confidence=Confidence(0.5),
            weight=1.0,
        )
        analysis = MarketStructureAnalysis(
            primary_trend=TrendDirection.BULLISH,
            secondary_trend=TrendDirection.BULLISH,
            structure_state=StructureState.TRENDING,
            trend_strength=0.7,
            confidence=0.7,
            evidence=evidence,
        )
        assert analysis.evidence is evidence


# ---------------------------------------------------------------------------
# TrendAnalyzer tests
# ---------------------------------------------------------------------------


class TestTrendAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = TrendAnalyzer()
        series = make_series([make_candle(100, 99, 99.5)])
        result = analyzer.analyze(series)
        assert result.primary is TrendDirection.UNKNOWN
        assert result.confidence == 0.0

    def test_bullish_trend(self) -> None:
        analyzer = TrendAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary is TrendDirection.BULLISH
        assert result.strength > 0
        assert result.confidence > 0

    def test_bearish_trend(self) -> None:
        analyzer = TrendAnalyzer()
        candles = make_bearish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary is TrendDirection.BEARISH
        assert result.strength > 0
        assert result.confidence > 0

    def test_sideways_market(self) -> None:
        analyzer = TrendAnalyzer()
        candles = make_sideways_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary is TrendDirection.SIDEWAYS


# ---------------------------------------------------------------------------
# SwingAnalyzer tests
# ---------------------------------------------------------------------------


class TestSwingAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = SwingAnalyzer()
        series = make_series([make_candle(100, 99, 99.5)])
        result = analyzer.analyze(series)
        assert result.confidence == 0.0

    def test_swing_highs_detected(self) -> None:
        analyzer = SwingAnalyzer()
        candles: list[Candle] = []
        prices = [100, 102, 105, 103, 101, 104, 107, 105, 102, 106, 109, 107, 104]
        for i, p in enumerate(prices):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=p + 1, low=p - 1, close=p, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert len(result.swing_highs) >= 3

    def test_swing_lows_detected(self) -> None:
        analyzer = SwingAnalyzer()
        candles: list[Candle] = []
        prices = [105, 103, 100, 102, 104, 101, 98, 100, 103, 99, 96, 98, 101]
        for i, p in enumerate(prices):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=p + 1, low=p - 1, close=p, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert len(result.swing_lows) >= 3

    def test_higher_highs_in_uptrend(self) -> None:
        analyzer = SwingAnalyzer()
        candles: list[Candle] = []
        prices = [100, 102, 105, 103, 101, 104, 107, 105, 102, 106, 109, 107, 104]
        for i, p in enumerate(prices):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=p + 1, low=p - 1, close=p, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert len(result.higher_highs) > 0

    def test_higher_lows_in_uptrend(self) -> None:
        analyzer = SwingAnalyzer()
        candles: list[Candle] = []
        prices = [100, 98, 102, 99, 97, 101, 100, 98, 103, 101, 99, 104, 102]
        for i, p in enumerate(prices):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=p + 1, low=p - 1, close=p, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert len(result.higher_lows) > 0

    def test_single_candle(self) -> None:
        analyzer = SwingAnalyzer()
        series = make_series([make_candle(100, 99, 99.5)])
        result = analyzer.analyze(series)
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# SupportResistanceAnalyzer tests
# ---------------------------------------------------------------------------


class TestSupportResistanceAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = SupportResistanceAnalyzer()
        series = make_series([make_candle(100, 99, 99.5)])
        result = analyzer.analyze(series)
        assert result.confidence == 0.0

    def test_support_levels_from_swing(self) -> None:
        analyzer = SupportResistanceAnalyzer()
        candles: list[Candle] = []
        prices = [105, 103, 100, 102, 104, 101, 98, 100, 103, 99, 96, 98, 101]
        for i, p in enumerate(prices):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=p + 1, low=p - 1, close=p, timestamp=ts))
        series = make_series(candles)

        swing_analyzer = SwingAnalyzer()
        swing = swing_analyzer.analyze(series)

        result = analyzer.analyze(series, swing=swing)
        assert len(result.support_levels) > 0

    def test_resistance_levels_from_swing(self) -> None:
        analyzer = SupportResistanceAnalyzer()
        candles: list[Candle] = []
        prices = [100, 102, 105, 103, 101, 104, 107, 105, 102, 106, 109, 107, 104]
        for i, p in enumerate(prices):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=p + 1, low=p - 1, close=p, timestamp=ts))
        series = make_series(candles)

        swing_analyzer = SwingAnalyzer()
        swing = swing_analyzer.analyze(series)

        result = analyzer.analyze(series, swing=swing)
        assert len(result.resistance_levels) > 0

    def test_levels_no_swing(self) -> None:
        analyzer = SupportResistanceAnalyzer()
        candles: list[Candle] = []
        for i in range(20):
            ts = NOW + timedelta(hours=i)
            candles.append(
                make_candle(
                    high=105 + (i % 5),
                    low=95 + (i % 5),
                    close=100 + (i % 5),
                    timestamp=ts,
                )
            )
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.confidence >= 0.0

    def test_clustering(self) -> None:
        analyzer = SupportResistanceAnalyzer()
        levels = [100.0, 100.1, 100.2, 105.0, 105.1, 110.0]
        clustered = analyzer._cluster_levels(levels)
        assert len(clustered) <= 3
        for val in clustered:
            assert 99.0 <= val <= 111.0


# ---------------------------------------------------------------------------
# MarketStructureAnalyzer tests
# ---------------------------------------------------------------------------


class TestMarketStructureAnalyzer:
    def test_insufficient_data(self) -> None:
        analyzer = MarketStructureAnalyzer()
        series = make_series([make_candle(100, 99, 99.5)])
        result = analyzer.analyze(series)
        assert result.primary_trend is TrendDirection.UNKNOWN
        assert result.structure_state is StructureState.UNKNOWN
        assert result.confidence == 0.0
        assert "Insufficient data" in result.warnings[0]

    def test_bullish_trend(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary_trend is TrendDirection.BULLISH
        assert result.confidence > 0

    def test_bearish_trend(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bearish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary_trend is TrendDirection.BEARISH
        assert result.confidence > 0

    def test_sideways_market(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_sideways_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary_trend is TrendDirection.SIDEWAYS

    def test_evidence_generated(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        evidence = result.evidence
        assert evidence is not None
        assert evidence.source == "Market Structure"
        assert evidence.category is EvidenceCategory.MARKET_STRUCTURE
        assert evidence.signal is EvidenceSignal.BULLISH
        assert len(evidence.reasons) > 0

    def test_explanation_generated(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        explanation = result.explanation
        assert explanation is not None
        assert isinstance(explanation, MarketStructureExplanation)
        assert "Trend" in explanation.trend
        assert "Swing" in explanation.swings
        assert "Support" in explanation.support
        assert "Resistance" in explanation.resistance
        assert "Structure" in explanation.structure
        assert "Interpretation" in explanation.institutional_interpretation

    def test_serialization_round_trip(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary_trend.value in (
            "bullish",
            "bearish",
            "sideways",
            "unknown",
        )
        assert result.structure_state.value in (
            "trending",
            "ranging",
            "transition",
            "unknown",
        )
        assert 0.0 <= result.trend_strength <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_support_and_resistance_in_output(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert isinstance(result.support_levels, tuple)
        assert isinstance(result.resistance_levels, tuple)

    def test_flat_market(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles: list[Candle] = []
        for i in range(60):
            ts = NOW + timedelta(hours=i)
            candles.append(make_candle(high=100.5, low=99.5, close=100.0, timestamp=ts))
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.primary_trend is TrendDirection.SIDEWAYS

    def test_evidence_and_explanation_integration(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(60)
        series = make_series(candles)
        result = analyzer.analyze(series)
        assert result.evidence is not None
        assert result.explanation is not None
        assert len(result.evidence.reasons) > 0
        assert len(result.explanation.trend) > 0

    def test_warning_on_low_data(self) -> None:
        analyzer = MarketStructureAnalyzer()
        candles = make_bullish_candles(10)
        series = make_series(candles)
        result = analyzer.analyze(series)
        warnings = result.warnings
        has_low_data_warning = any("Limited data" in w for w in warnings)
        assert has_low_data_warning
