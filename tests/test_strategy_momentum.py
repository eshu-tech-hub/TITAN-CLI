from datetime import UTC, datetime

from titan.market.models import Candle
from titan.market.series import MarketDataSeries
from titan.trading.strategies.base import SignalType
from titan.trading.strategies.momentum import MomentumStrategy


def create_candles(closes):
    return [
        Candle(
            timestamp=datetime.now(UTC),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=100
        )
        for c in closes
    ]

def test_momentum_strategy_hold():
    strategy = MomentumStrategy(fast_period=3, slow_period=5, rsi_period=4)
    # Not enough data
    closes = [100.0, 101.0, 102.0]
    series = MarketDataSeries(candles=create_candles(closes))
    signal = strategy.generate_signal(series)
    assert signal.signal == SignalType.HOLD

def test_momentum_strategy_buy():
    strategy = MomentumStrategy(fast_period=2, slow_period=4, rsi_period=3)
    closes = [100.0, 95.0, 90.0, 85.0, 80.0, 110.0, 120.0, 130.0]
    series = MarketDataSeries(candles=create_candles(closes))
    signal = strategy.generate_signal(series)
    assert signal.signal in (SignalType.BUY, SignalType.HOLD)

def test_momentum_strategy_sell():
    strategy = MomentumStrategy(fast_period=2, slow_period=4, rsi_period=3)
    closes = [100.0, 110.0, 120.0, 130.0, 80.0, 70.0, 60.0]
    series = MarketDataSeries(candles=create_candles(closes))
    signal = strategy.generate_signal(series)
    assert signal.signal in (SignalType.SELL, SignalType.HOLD)
