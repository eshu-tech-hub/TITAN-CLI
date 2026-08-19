import pytest

from titan.market.options import OptionChainManager


@pytest.fixture
def dummy_scrip_data():
    return [
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "19900.000000",
            "symbol": "NIFTY24OCT19900CE",
            "token": "101",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "19950.000000",
            "symbol": "NIFTY24OCT19950CE",
            "token": "102",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "20000.000000",
            "symbol": "NIFTY24OCT20000CE",
            "token": "103",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "20050.000000",
            "symbol": "NIFTY24OCT20050CE",
            "token": "104",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "19900.000000",
            "symbol": "NIFTY24OCT19900PE",
            "token": "201",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "19950.000000",
            "symbol": "NIFTY24OCT19950PE",
            "token": "202",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "20000.000000",
            "symbol": "NIFTY24OCT20000PE",
            "token": "203",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTIDX",
            "name": "NIFTY",
            "strike": "20050.000000",
            "symbol": "NIFTY24OCT20050PE",
            "token": "204",
            "expiry": "24OCT2024",
        },
        {
            "instrumenttype": "OPTSTK",
            "name": "RELIANCE",
            "strike": "2500.000000",
            "symbol": "RELIANCE24OCT2500CE",
            "token": "301",
            "expiry": "24OCT2024",
        },
    ]


def test_fetch_and_filter(dummy_scrip_data):
    manager = OptionChainManager()
    contracts = manager.fetch_and_filter(dummy_scrip_data, "NIFTY")

    assert len(contracts) == 8
    assert all(c.symbol.startswith("NIFTY") for c in contracts)
    assert all(c.option_type in ["CE", "PE"] for c in contracts)

    # Test mapping
    ce_19900 = next(
        c for c in contracts if c.strike == 19900.0 and c.option_type == "CE"
    )
    assert ce_19900.token == "101"


def test_get_atm_strike():
    manager = OptionChainManager()
    assert manager.get_atm_strike(20024.0, 50) == 20000.0
    assert manager.get_atm_strike(20026.0, 50) == 20050.0


def test_get_option_chain(dummy_scrip_data):
    manager = OptionChainManager()
    manager.fetch_and_filter(dummy_scrip_data, "NIFTY")

    # Convert filtered_data back to dictionaries for testing the full cycle if needed
    # Wait, the method signature expects scrip_data (list of dicts) but inside it just checks for instrumenttype
    chain = manager.get_option_chain(20010.0, 50.0, 1, dummy_scrip_data)

    # ATM is 20000. Distance 1 means we need 19950, 20000, 20050
    assert "CE" in chain and "PE" in chain
    assert len(chain["CE"]) == 3
    assert len(chain["PE"]) == 3

    strikes = [c.strike for c in chain["CE"]]
    assert strikes == [19950.0, 20000.0, 20050.0]
