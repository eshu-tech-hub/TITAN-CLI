from datetime import datetime, timedelta

import pytest

from titan.market import (
    Candle,
    MarketDataProvider,
    MarketDataProviderError,
    MarketDataService,
    MarketDataValidationError,
    Symbol,
    SymbolValidationError,
    Timeframe,
    TimeframeValidationError,
    validate_historical_request,
    validate_symbol,
    validate_timeframe,
)


class StaticProvider(MarketDataProvider):
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.last_symbol: Symbol | None = None
        self.last_timeframe: Timeframe | None = None

    def get_historical_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        self.last_symbol = symbol
        self.last_timeframe = timeframe
        return self.candles


class FailingProvider(MarketDataProvider):
    def get_historical_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        raise RuntimeError("provider unavailable")


def make_candles() -> list[Candle]:
    return [
        Candle(
            timestamp=datetime(2026, 1, 1, 9, 15),
            open=100.0,
            high=105.0,
            low=99.0,
            close=104.0,
            volume=1000,
        )
    ]


def test_market_data_provider_is_abstract():
    with pytest.raises(TypeError):
        MarketDataProvider()


def test_symbol_model_is_immutable():
    symbol = Symbol(exchange="NSE", ticker="RELIANCE")

    with pytest.raises(AttributeError):
        symbol.ticker = "TCS"


def test_validate_symbol_rejects_missing_exchange():
    with pytest.raises(SymbolValidationError):
        validate_symbol(Symbol(exchange="", ticker="RELIANCE"))


def test_validate_symbol_rejects_missing_ticker():
    with pytest.raises(SymbolValidationError):
        validate_symbol(Symbol(exchange="NSE", ticker=" "))


def test_validate_timeframe_accepts_enum_and_string():
    assert validate_timeframe(Timeframe.FIVE_MINUTES) is Timeframe.FIVE_MINUTES
    assert validate_timeframe("5m") is Timeframe.FIVE_MINUTES


def test_validate_timeframe_rejects_unknown_value():
    with pytest.raises(TimeframeValidationError):
        validate_timeframe("7m")


def test_validate_historical_request_rejects_invalid_date_range():
    start = datetime(2026, 1, 2)
    end = start - timedelta(days=1)

    with pytest.raises(MarketDataValidationError):
        validate_historical_request(
            Symbol(exchange="NSE", ticker="RELIANCE"),
            Timeframe.ONE_DAY,
            start=start,
            end=end,
        )


def test_validate_historical_request_rejects_invalid_limit():
    with pytest.raises(MarketDataValidationError):
        validate_historical_request(
            Symbol(exchange="NSE", ticker="RELIANCE"),
            Timeframe.ONE_DAY,
            limit=0,
        )


def test_market_data_service_returns_validated_series():
    symbol = Symbol(exchange="NSE", ticker="RELIANCE")
    provider = StaticProvider(make_candles())
    service = MarketDataService(provider)

    series = service.get_historical_candles(
        symbol,
        "5m",
        limit=1,
    )

    assert len(series) == 1
    assert series.closes == [104.0]
    assert provider.last_symbol == symbol
    assert provider.last_timeframe is Timeframe.FIVE_MINUTES


def test_market_data_service_validates_provider_response():
    provider = StaticProvider(
        [
            Candle(
                timestamp=datetime(2026, 1, 1, 9, 15),
                open=100.0,
                high=90.0,
                low=99.0,
                close=104.0,
                volume=1000,
            )
        ]
    )
    service = MarketDataService(provider)

    with pytest.raises(MarketDataValidationError):
        service.get_historical_candles(
            Symbol(exchange="NSE", ticker="RELIANCE"),
            Timeframe.ONE_MINUTE,
        )


def test_market_data_service_wraps_provider_failures():
    service = MarketDataService(FailingProvider())

    with pytest.raises(MarketDataProviderError):
        service.get_historical_candles(
            Symbol(exchange="NSE", ticker="RELIANCE"),
            Timeframe.ONE_MINUTE,
        )
