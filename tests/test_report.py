from datetime import datetime

from titan.analysis.models import IndicatorResult
from titan.analysis.report import AnalysisReport


def test_add_indicator():

    report = AnalysisReport(
        symbol="NIFTY",
        timeframe="15m",
        timestamp=datetime.now(),
    )

    report.add(
        IndicatorResult(
            name="SMA",
            value=25000,
        )
    )

    assert report.has("SMA")


def test_get_indicator():

    report = AnalysisReport(
        symbol="NIFTY",
        timeframe="15m",
        timestamp=datetime.now(),
    )

    result = IndicatorResult(
        name="EMA",
        value=25100,
    )

    report.add(result)

    assert report.get("EMA") == result


def test_missing_indicator():

    report = AnalysisReport(
        symbol="BANKNIFTY",
        timeframe="5m",
        timestamp=datetime.now(),
    )

    assert report.get("RSI") is None
