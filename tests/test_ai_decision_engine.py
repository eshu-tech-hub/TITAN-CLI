import pytest

from titan.ai.decision_engine import AIDecisionSynthesizer
from titan.market.options import OptionContract


@pytest.fixture
def dummy_option_chain():
    return {
        "CE": [
            OptionContract(
                symbol="NIFTY19900CE",
                token="101",
                strike=19900.0,
                option_type="CE",
                expiry="24OCT",
            ),
            OptionContract(
                symbol="NIFTY20000CE",
                token="102",
                strike=20000.0,
                option_type="CE",
                expiry="24OCT",
            ),
            OptionContract(
                symbol="NIFTY20100CE",
                token="103",
                strike=20100.0,
                option_type="CE",
                expiry="24OCT",
            ),
        ],
        "PE": [
            OptionContract(
                symbol="NIFTY19900PE",
                token="201",
                strike=19900.0,
                option_type="PE",
                expiry="24OCT",
            ),
            OptionContract(
                symbol="NIFTY20000PE",
                token="202",
                strike=20000.0,
                option_type="PE",
                expiry="24OCT",
            ),
            OptionContract(
                symbol="NIFTY20100PE",
                token="203",
                strike=20100.0,
                option_type="PE",
                expiry="24OCT",
            ),
        ],
    }


def test_evaluate_technicals():
    engine = AIDecisionSynthesizer()
    assert engine.evaluate_technicals(sma=100.0, ema=105.0, rsi=65.0) == "BULLISH"
    assert engine.evaluate_technicals(sma=100.0, ema=95.0, rsi=35.0) == "BEARISH"
    assert engine.evaluate_technicals(sma=100.0, ema=105.0, rsi=50.0) == "NEUTRAL"


def test_select_contract(dummy_option_chain):
    engine = AIDecisionSynthesizer()
    contract_ce = engine.select_contract("BULLISH", dummy_option_chain, 20000.0)
    assert contract_ce.option_type == "CE"
    assert contract_ce.strike == 20000.0

    contract_pe = engine.select_contract("BEARISH", dummy_option_chain, 20100.0)
    assert contract_pe.option_type == "PE"
    assert contract_pe.strike == 20100.0


def test_generate_trade(dummy_option_chain):
    engine = AIDecisionSynthesizer()

    technicals_bullish = {"sma": 100.0, "ema": 105.0, "rsi": 65.0}

    trade = engine.generate_trade(
        spot_price=20010.0,
        technicals=technicals_bullish,
        option_chain=dummy_option_chain,
    )

    assert trade is not None
    assert trade["action"] == "BUY"
    assert trade["option_symbol"] == "NIFTY20000CE"
    assert trade["strike"] == 20000.0
    assert trade["entry_price"] == 100.0
    assert trade["target"] == 150.0
    assert trade["stop_loss"] == 75.0
    assert "BULLISH" in trade["rationale"]


def test_generate_trade_neutral(dummy_option_chain):
    engine = AIDecisionSynthesizer()
    technicals_neutral = {"sma": 100.0, "ema": 105.0, "rsi": 50.0}
    trade = engine.generate_trade(
        spot_price=20010.0,
        technicals=technicals_neutral,
        option_chain=dummy_option_chain,
    )

    assert trade is None
