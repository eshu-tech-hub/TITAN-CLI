from titan.analysis.models import IndicatorResult


def test_indicator_result_defaults():
    result = IndicatorResult(
        name="SMA",
        value=150.25,
    )

    assert result.name == "SMA"
    assert result.value == 150.25
    assert result.signal == "Neutral"
    assert result.metadata == {}


def test_indicator_result_metadata():
    result = IndicatorResult(
        name="RSI",
        value=62.4,
        signal="Bullish",
        metadata={"period": 14},
    )

    assert result.metadata["period"] == 14