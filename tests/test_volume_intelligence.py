from datetime import datetime, timedelta

import pytest

from titan.core.evidence import EvidenceCategory, EvidenceSignal
from titan.market.intelligence.accumulation_distribution import (
    AccumulationDistributionAnalyzer,
)
from titan.market.intelligence.models import (
    AccumulationDistribution,
    ParticipationLevel,
    RelativeVolume,
    VolumeAnalysis,
    VolumeBias,
    VolumeExplanation,
    VolumeTrend,
)
from titan.market.intelligence.relative_volume import (
    RelativeVolumeAnalyzer,
)
from titan.market.intelligence.volume import VolumeAnalyzer
from titan.market.intelligence.volume_trend import VolumeTrendAnalyzer
from titan.market.models import Candle
from titan.market.series import MarketDataSeries

NOW = datetime(2026, 7, 2, 9, 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_candle(
    close: float = 100.0,
    volume: int = 1_000_000,
    timestamp: datetime | None = None,
) -> Candle:
    return Candle(
        timestamp=timestamp or NOW,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=volume,
    )


def make_series(volumes: list[int]) -> MarketDataSeries:
    candles: list[Candle] = []
    for i, v in enumerate(volumes):
        candles.append(
            make_candle(
                volume=v,
                timestamp=NOW + timedelta(hours=i),
            )
        )
    return MarketDataSeries(candles=candles)


def make_priced_series(
    closes: list[float],
    volumes: list[int],
) -> MarketDataSeries:
    candles: list[Candle] = []
    for i, (c, v) in enumerate(zip(closes, volumes)):
        candles.append(
            Candle(
                timestamp=NOW + timedelta(hours=i),
                open=c,
                high=c + 1.0,
                low=c - 1.0,
                close=c,
                volume=v,
            )
        )
    return MarketDataSeries(candles=candles)


# ---------------------------------------------------------------------------
# VolumeTrendAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestVolumeTrendAnalyzer:
    def test_insufficient_data(self) -> None:
        series = make_series([100] * 2)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.reasons[0]

    def test_expanding_volume(self) -> None:
        volumes = [1000] * 10 + [5000] * 5
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.expanding is True

    def test_contracting_volume(self) -> None:
        volumes = [5000] * 10 + [1000] * 5
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.contracting is True

    def test_stable_volume(self) -> None:
        volumes = [2000] * 15
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.expanding is False
        assert result.contracting is False

    def test_slope_computation(self) -> None:
        volumes = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.slope > 0

    def test_slope_negative(self) -> None:
        volumes = [10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1000]
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.slope < 0

    def test_expansion_ratio(self) -> None:
        volumes = [1000] * 10 + [5000] * 5
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.expansion_ratio >= 3.0

    def test_exact_threshold_expansion(self) -> None:
        volumes = [1000] * 10 + [1250] * 5
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.expanding is True

    def test_exact_threshold_contraction(self) -> None:
        volumes = [1000] * 10 + [749] * 5
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.contracting is True

    def test_single_candle(self) -> None:
        series = make_series([1000])
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.reasons[0]

    def test_missing_volume_zeros(self) -> None:
        volumes = [1000] * 5 + [0] * 5
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.contracting is True

    def test_reasons_include_slope(self) -> None:
        volumes = [1000, 2000, 3000, 4000, 5000] * 3
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert any("Volume slope" in r for r in result.reasons)

    def test_flat_slope(self) -> None:
        volumes = [1000] * 15
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert "flat" in result.reasons[0]


# ---------------------------------------------------------------------------
# RelativeVolumeAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestRelativeVolumeAnalyzer:
    def test_insufficient_data(self) -> None:
        series = make_series([100])
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.confidence == 0.0

    def test_rvol_one(self) -> None:
        volumes = [2000] * 20
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.rvol == pytest.approx(1.0, abs=0.01)
        assert result.participation is ParticipationLevel.NORMAL

    def test_high_rvol(self) -> None:
        volumes = [1000] * 20 + [3000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.rvol > 1.0
        assert result.participation is ParticipationLevel.HIGH

    def test_very_low_participation(self) -> None:
        volumes = [100000] * 20 + [10000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.participation is ParticipationLevel.VERY_LOW

    def test_low_participation(self) -> None:
        volumes = [100000] * 20 + [50000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.participation is ParticipationLevel.LOW

    def test_extreme_rvol(self) -> None:
        volumes = [1000] * 20 + [4000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.participation is ParticipationLevel.EXTREME

    def test_reasons_include_rvol(self) -> None:
        volumes = [1000] * 20
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert any("RVOL" in r for r in result.reasons)

    def test_zero_avg_volume(self) -> None:
        volumes = [0] * 10
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.rvol == 0.0
        assert result.participation is ParticipationLevel.VERY_LOW

    def test_high_rvol_single_spike(self) -> None:
        volumes = [1000] * 19 + [50000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.rvol > 1.0
        assert result.participation is ParticipationLevel.EXTREME

    def test_rvol_edge_boundary_low(self) -> None:
        volumes = [100000] * 20 + [20000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.participation is ParticipationLevel.VERY_LOW

    def test_rvol_edge_boundary_normal(self) -> None:
        volumes = [100000] * 20 + [100000]
        series = make_series(volumes)
        result = RelativeVolumeAnalyzer().analyze(series)
        assert result.participation is ParticipationLevel.NORMAL


# ---------------------------------------------------------------------------
# AccumulationDistributionAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestAccumulationDistributionAnalyzer:
    def test_insufficient_data(self) -> None:
        series = make_series([100] * 2)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.confidence == 0.0

    def test_accumulation_detected(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [100, 500, 600, 700, 800, 900]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.accumulation is True

    def test_distribution_detected(self) -> None:
        closes = [105.0, 104.0, 103.0, 102.0, 101.0, 100.0]
        volumes = [100, 500, 600, 700, 800, 900]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.distribution is True

    def test_no_clear_accumulation_distribution(self) -> None:
        closes = [100.0, 100.05, 100.0, 100.05, 100.0, 100.05]
        volumes = [1000, 1000, 1000, 1000, 1000, 1000]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.accumulation is False
        assert result.distribution is False

    def test_price_volume_divergence(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [500, 300, 200, 150, 100, 50]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.divergence is True

    def test_ad_ratio_midpoint(self) -> None:
        closes = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        volumes = [1000, 1000, 1000, 1000, 1000, 1000]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.ad_ratio == 0.5

    def test_ad_ratio_extreme_accumulation(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [100, 500, 500, 500, 500, 500]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.ad_ratio > 0.6

    def test_ad_ratio_extreme_distribution(self) -> None:
        closes = [105.0, 104.0, 103.0, 102.0, 101.0, 100.0]
        volumes = [100, 500, 500, 500, 500, 500]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.ad_ratio < 0.4

    def test_reasons_accumulation(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [100, 500, 600, 700, 800, 900]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert any("Accumulation" in r for r in result.reasons)

    def test_reasons_distribution(self) -> None:
        closes = [105.0, 104.0, 103.0, 102.0, 101.0, 100.0]
        volumes = [100, 500, 600, 700, 800, 900]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert any("Distribution" in r for r in result.reasons)

    def test_reasons_divergence(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [500, 300, 200, 150, 100, 50]
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert any("divergence" in r for r in result.reasons)

    def test_single_candle(self) -> None:
        series = make_series([1000])
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# VolumeAnalyzer orchestrator tests
# ---------------------------------------------------------------------------


class TestVolumeAnalyzer:
    def test_insufficient_data(self) -> None:
        series = make_series([100])
        result = VolumeAnalyzer().analyze(series)
        assert result.confidence == 0.0
        assert "Insufficient data" in result.warnings[0]

    def test_normal_volume_analysis(self) -> None:
        closes = [100.0] * 15 + [101.0, 102.0, 103.0, 104.0, 105.0]
        volumes = [1_000_000] * 20
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.current_volume > 0
        assert result.average_volume > 0

    def test_high_rvol_bullish(self) -> None:
        closes = [
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            106.0,
            107.0,
            108.0,
            109.0,
            110.0,
            111.0,
            112.0,
            113.0,
            114.0,
            115.0,
            116.0,
            117.0,
            118.0,
            119.0,
            120.0,
        ]
        volumes = [1000] * 15 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.volume_bias is VolumeBias.BULLISH

    def test_high_rvol_bearish(self) -> None:
        closes = [
            120.0,
            119.0,
            118.0,
            117.0,
            116.0,
            115.0,
            114.0,
            113.0,
            112.0,
            111.0,
            110.0,
            109.0,
            108.0,
            107.0,
            106.0,
            105.0,
            104.0,
            103.0,
            102.0,
            101.0,
            100.0,
        ]
        volumes = [1000] * 15 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.volume_bias is VolumeBias.BEARISH

    def test_neutral_bias_low_rvol(self) -> None:
        volumes = [1_000_000] * 20 + [400_000]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.volume_bias is VolumeBias.NEUTRAL

    def test_breakout_confirmation(self) -> None:
        closes = [
            100.0,
            102.0,
            104.0,
            106.0,
            108.0,
            110.0,
            112.0,
            114.0,
            116.0,
            118.0,
            120.0,
        ]
        volumes = [1000] * 6 + [5000] * 5
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.breakout_confirmation is True

    def test_no_breakout_confirmation(self) -> None:
        closes = [100.0] * 11
        volumes = [1000] * 6 + [5000] * 5
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.breakout_confirmation is False

    def test_exhaustion_high_rvol(self) -> None:
        volumes = [1000] * 18 + [10000, 10000]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.exhaustion_probability >= 0.4

    def test_participation_level_normal(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.participation_level is not None

    def test_warnings_limited_data(self) -> None:
        volumes = [1000] * 3
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert any("Limited" in w for w in result.warnings)

    def test_metadata_present(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert "analyzer" in result.metadata
        assert result.metadata["analyzer"] == "VolumeAnalyzer"

    def test_explanation_generated(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.explanation is not None
        assert isinstance(result.explanation, VolumeExplanation)

    def test_explanation_sections(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        exp = result.explanation
        assert exp.current_volume != ""
        assert exp.relative_volume != ""
        assert exp.participation != ""
        assert exp.accumulation_distribution != ""
        assert exp.breakout_quality != ""
        assert exp.institutional_interpretation != ""

    def test_evidence_generated(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.evidence is not None
        assert result.evidence.category is EvidenceCategory.VOLUME
        assert result.evidence.source == "Volume"

    def test_evidence_signal_mapping(self) -> None:
        closes = [
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            106.0,
            107.0,
            108.0,
            109.0,
            110.0,
            111.0,
            112.0,
            113.0,
            114.0,
            115.0,
            116.0,
            117.0,
            118.0,
            119.0,
            120.0,
        ]
        volumes = [1000] * 15 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BULLISH

    def test_evidence_score_bullish(self) -> None:
        closes = [
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            106.0,
            107.0,
            108.0,
            109.0,
            110.0,
            111.0,
            112.0,
            113.0,
            114.0,
            115.0,
            116.0,
            117.0,
            118.0,
            119.0,
            120.0,
        ]
        volumes = [1000] * 15 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.evidence is not None
        assert result.evidence.score.value >= 50.0

    def test_evidence_score_bearish(self) -> None:
        closes = [
            120.0,
            119.0,
            118.0,
            117.0,
            116.0,
            115.0,
            114.0,
            113.0,
            112.0,
            111.0,
            110.0,
            109.0,
            108.0,
            107.0,
            106.0,
            105.0,
            104.0,
            103.0,
            102.0,
            101.0,
            100.0,
        ]
        volumes = [1000] * 15 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.evidence is not None
        assert result.evidence.score.value <= 50.0

    def test_evidence_reasons(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.evidence is not None
        assert len(result.evidence.reasons) > 0

    def test_evidence_weight(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.evidence is not None
        assert result.evidence.weight == 1.0

    def test_neutral_placeholder(self) -> None:
        result = VolumeAnalysis.neutral_placeholder()
        assert result.confidence == 0.0
        assert "Volume data unavailable." in result.warnings

    def test_accumulation_distribution_subresult(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.accumulation_distribution is not None
        assert isinstance(result.accumulation_distribution, AccumulationDistribution)

    def test_relative_volume_subresult(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.relative is not None
        assert isinstance(result.relative, RelativeVolume)

    def test_trend_subresult(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.trend is not None
        assert isinstance(result.trend, VolumeTrend)

    def test_empty_analysis(self) -> None:
        series = make_series([])
        result = VolumeAnalyzer().analyze(series)
        assert result.confidence == 0.0
        assert len(result.warnings) >= 1

    def test_empty_analysis_explanation(self) -> None:
        series = make_series([])
        result = VolumeAnalyzer().analyze(series)
        assert result.explanation is not None
        assert "unavailable" in result.explanation.current_volume

    def test_volume_analysis_type(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert isinstance(result, VolumeAnalysis)

    def test_exhaustion_with_contraction(self) -> None:
        volumes = [
            10000,
            9000,
            8000,
            7000,
            6000,
            5000,
            4000,
            3000,
            2000,
            1000,
            900,
            800,
            700,
            600,
            500,
            400,
            300,
            200,
            100,
            50,
        ]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.exhaustion_probability > 0

    def test_exhaustion_with_decreasing_sequence(self) -> None:
        volumes = [5000, 4800, 4500, 10000, 5000, 4800, 4500]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.exhaustion_probability >= 0.0

    def test_volume_bias_unknown_flat(self) -> None:
        volumes = [1000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.volume_bias is VolumeBias.UNKNOWN

    def test_exhaustion_probability_range(self) -> None:
        volumes = [1_000_000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert 0.0 <= result.exhaustion_probability <= 1.0


# ---------------------------------------------------------------------------
# Validation and serialization tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_volume_analysis_frozen(self) -> None:
        result = VolumeAnalysis.neutral_placeholder()
        with pytest.raises(AttributeError):
            result.current_volume = 100

    def test_volume_trend_frozen(self) -> None:
        t = VolumeTrend()
        with pytest.raises(AttributeError):
            t.slope = 1.0

    def test_volume_explanation_slots(self) -> None:
        e = VolumeExplanation()
        with pytest.raises(AttributeError):
            e.new_attr = "test"

    def test_volume_trend_slots(self) -> None:
        t = VolumeTrend()
        with pytest.raises(AttributeError):
            t.new_attr = "test"

    def test_accumulation_distribution_frozen(self) -> None:
        ad = AccumulationDistribution()
        with pytest.raises(AttributeError):
            ad.accumulation = True

    def test_relative_volume_frozen(self) -> None:
        rv = RelativeVolume()
        with pytest.raises(AttributeError):
            rv.rvol = 2.0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_volume_all_zeros(self) -> None:
        volumes = [0] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.average_volume == 0.0
        assert result.relative_volume == 0.0

    def test_single_candle_volume(self) -> None:
        series = make_series([1000])
        result = VolumeAnalyzer().analyze(series)
        assert result.confidence == 0.0

    def test_two_candles(self) -> None:
        volumes = [1000, 2000]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.current_volume == 2000
        assert result.average_volume > 0

    def test_volume_with_gap(self) -> None:
        volumes = [1000] * 10 + [0] + [1000] * 10
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.current_volume > 0

    def test_extreme_volume_spike(self) -> None:
        volumes = [1000] * 19 + [100000]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.participation_level is ParticipationLevel.EXTREME
        assert result.relative_volume > 1.0

    def test_accumulation_without_price_change(self) -> None:
        closes = [100.0] * 10
        volumes = list(range(100, 1100, 100))
        series = make_priced_series(closes, volumes)
        result = AccumulationDistributionAnalyzer().analyze(series)
        assert result.accumulation is False
        assert result.distribution is False

    def test_volume_trend_single_high_value(self) -> None:
        volumes = [1000, 1000, 1000, 1000, 1000, 10000]
        series = make_series(volumes)
        result = VolumeTrendAnalyzer().analyze(series)
        assert result.expanding is True

    def test_confidence_bounds(self) -> None:
        volumes = [1_000_000] * 50
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert 0.0 <= result.confidence <= 1.0

    def test_average_volume_matches(self) -> None:
        volumes = [1000] * 20
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.average_volume == 1000.0

    def test_relative_volume_subresult_matches(self) -> None:
        volumes = [1000] * 20 + [2000]
        series = make_series(volumes)
        result = VolumeAnalyzer().analyze(series)
        assert result.relative is not None
        assert result.relative.rvol == result.relative_volume

    def test_institutional_interpretation_bullish(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0] * 4
        volumes = [1000] * 18 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert "bullish" in result.explanation.institutional_interpretation.lower()

    def test_institutional_interpretation_bearish(self) -> None:
        closes = [105.0, 104.0, 103.0, 102.0, 101.0, 100.0] * 4
        volumes = [1000] * 18 + [3000] * 6
        series = make_priced_series(closes, volumes)
        result = VolumeAnalyzer().analyze(series)
        assert "bearish" in result.explanation.institutional_interpretation.lower()

    def test_institutional_interpretation_unavailable(self) -> None:
        series = make_series([])
        result = VolumeAnalyzer().analyze(series)
        assert "unavailable" in result.explanation.institutional_interpretation.lower()
