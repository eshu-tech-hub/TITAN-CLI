from titan.tui.layout import build_strategy_eval_state
from titan.tui.models import StrategyEvalScreenState
from titan.tui.screens.strategy_eval import StrategyEvalScreen


def test_strategy_screen_state_defaults():
    state = StrategyEvalScreenState()
    assert state.best_strategy == ""
    assert len(state.scorecards) == 0
    assert state.last_refresh == ""


def test_build_strategy_state_fallback():
    state = build_strategy_eval_state()
    assert isinstance(state, StrategyEvalScreenState)
    assert state.last_refresh != ""


def test_strategy_screen_builder_injection():
    screen = StrategyEvalScreen()
    assert screen._state.last_refresh == ""

    def mock_builder() -> StrategyEvalScreenState:
        return StrategyEvalScreenState(
            best_strategy="MockStrat", last_refresh="12:00:00"
        )

    screen.set_state_builder(mock_builder)
    screen._refresh_state()
    assert screen._state.last_refresh == "12:00:00"
    assert screen._state.best_strategy == "MockStrat"
