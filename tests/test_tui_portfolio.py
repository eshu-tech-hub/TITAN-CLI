from titan.portfolio.models import (
    AllocationAnalysis,
    DiversificationAnalysis,
    DrawdownAnalysis,
    ExposureAnalysis,
    PortfolioPerformance,
    PortfolioSnapshot,
)
from titan.tui.layout import build_portfolio_state
from titan.tui.models import PortfolioScreenState
from titan.tui.screens.portfolio import PortfolioDashboardScreen


def test_portfolio_screen_state_defaults():
    """Verify the DTO initializes with safe, frozen defaults."""
    state = PortfolioScreenState()
    assert isinstance(state.snapshot, PortfolioSnapshot)
    assert isinstance(state.exposure, ExposureAnalysis)
    assert isinstance(state.allocation, AllocationAnalysis)
    assert isinstance(state.diversification, DiversificationAnalysis)
    assert isinstance(state.drawdown, DrawdownAnalysis)
    assert isinstance(state.performance, PortfolioPerformance)
    assert state.last_refresh == ""


def test_build_portfolio_state_fallback():
    """
    Verify the layout builder safely catches exceptions (like missing runtime engine)
    and returns a fallback state rather than crashing the TUI.
    """
    state = build_portfolio_state()
    assert isinstance(state, PortfolioScreenState)
    # The layout builder should still stamp the refresh time even on a fallback
    assert state.last_refresh != ""


def test_portfolio_screen_builder_injection():
    """Verify the screen cleanly accepts a state builder and updates its DTO."""
    screen = PortfolioDashboardScreen()

    # Assert initial state
    assert screen.state.last_refresh == ""

    # Create a deterministic mock builder
    def mock_builder() -> PortfolioScreenState:
        return PortfolioScreenState(last_refresh="15:30:00")

    # Inject and trigger refresh
    screen.set_state_builder(mock_builder)
    screen._refresh_state()

    # Verify the screen safely consumed the mocked DTO
    assert screen.state.last_refresh == "15:30:00"
