from datetime import datetime

from titan.market.models import Candle


def test_candle():
    candle = Candle(
        timestamp=datetime.now(),
        open=100,
        high=105,
        low=99,
        close=104,
        volume=10000,
    )

    assert candle.close == 104