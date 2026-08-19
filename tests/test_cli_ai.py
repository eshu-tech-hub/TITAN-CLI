from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from titan.cli import app
from titan.portfolio.analytics import PortfolioAnalytics
from titan.portfolio.models import ExistingPortfolio
from titan.trading.journal import TradeJournalEntry

runner = CliRunner()


@pytest.fixture
def mock_analytics_data():
    with patch("titan.cli.commands.portfolio._get_analytics_data") as mock_get:
        analytics = PortfolioAnalytics()
        portfolio = ExistingPortfolio(total_capital=100000.0)
        entries: list[TradeJournalEntry] = []
        mock_get.return_value = (analytics, portfolio, entries)
        yield mock_get


def test_ai_portfolio_cli(mock_analytics_data):
    result = runner.invoke(app, ["ai", "portfolio", "--provider", "mock"])
    assert result.exit_code == 0
    assert "AI Portfolio Analysis" in result.output


def test_ai_strategy_cli():
    with patch("titan.cli.common.get_runtime_engine") as mock_engine:
        mock_engine.return_value.trade_journal.repository.list.return_value = []
        result = runner.invoke(app, ["ai", "strategy", "--provider", "mock"])
        assert result.exit_code == 0
        assert "AI Strategy Synthesis" in result.output
