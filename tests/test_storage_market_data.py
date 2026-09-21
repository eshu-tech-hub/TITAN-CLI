from datetime import UTC, datetime

from titan.market.models import Candle
from titan.storage.market_data import MarketDataStore


def test_market_data_store_memory():
    store = MarketDataStore(":memory:")
    
    # Create some dummy candles
    candles = [
        Candle(
            timestamp=datetime(2023, 1, 1, 9, 15, tzinfo=UTC),
            open=100.0,
            high=105.0,
            low=99.0,
            close=102.0,
            volume=1000
        ),
        Candle(
            timestamp=datetime(2023, 1, 1, 9, 16, tzinfo=UTC),
            open=102.0,
            high=104.0,
            low=101.0,
            close=103.0,
            volume=500
        )
    ]
    
    store.save_candles("RELIANCE", "1m", candles)
    
    loaded = store.load_candles("RELIANCE", "1m")
    assert len(loaded) == 2
    assert loaded[0].open == 100.0
    assert loaded[1].volume == 500
    assert loaded[0].timestamp.tzinfo is not None
    
    # Test loading with date range
    loaded_range = store.load_candles(
        "RELIANCE", "1m", 
        start=datetime(2023, 1, 1, 9, 16, tzinfo=UTC)
    )
    assert len(loaded_range) == 1
    assert loaded_range[0].open == 102.0
