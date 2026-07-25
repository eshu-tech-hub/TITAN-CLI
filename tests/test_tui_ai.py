from titan.tui.layout import build_ai_state
from titan.tui.models import AIExplanationInfo, AIScreenState
from titan.tui.screens.ai_assistant import AIAssistantScreen


def test_ai_screen_state_defaults():
    state = AIScreenState()
    assert isinstance(state.portfolio_explanation, AIExplanationInfo)
    assert isinstance(state.strategy_explanation, AIExplanationInfo)
    assert state.last_refresh == ""


def test_build_ai_state_fallback():
    state = build_ai_state(provider_name="mock")
    assert isinstance(state, AIScreenState)
    assert state.last_refresh != ""


def test_ai_screen_builder_injection():
    screen = AIAssistantScreen()
    assert screen._state.last_refresh == ""

    def mock_builder() -> AIScreenState:
        return AIScreenState(
            portfolio_explanation=AIExplanationInfo(title="Test Port"),
            last_refresh="18:00:00",
        )

    screen.set_state_builder(mock_builder)
    screen._refresh_state()

    assert screen._state.last_refresh == "18:00:00"
    assert screen._state.portfolio_explanation.title == "Test Port"
