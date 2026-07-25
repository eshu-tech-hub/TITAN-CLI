import pytest
from unittest.mock import patch
from typer.testing import CliRunner

from titan.cli import app
from titan.portfolio.analytics import PortfolioAnalytics
from titan.portfolio.models import ExistingPortfolio
from titan.trading.journal import TradeJournalEntry

runner = CliRunner()


@pytest.fixture
def mock_analytics_data():
    """Mock the data retrieval to test CLI formatting cleanly."""
    with patch("titan.cli.commands.portfolio._get_analytics_data") as mock_get:
        analytics = PortfolioAnalytics()
        portfolio = ExistingPortfolio(total_capital=100000.0)
        entries: list[TradeJournalEntry] = []
        mock_get.return_value = (analytics, portfolio, entries)
        yield mock_get


def test_portfolio_summary_cli(mock_analytics_data):
    result = runner.invoke(app, ["portfolio", "summary"])
    assert result.exit_code == 0
    assert "Portfolio Summary" in result.output
    assert "Total Capital" in result.output


def test_portfolio_risk_cli(mock_analytics_data):
    result = runner.invoke(app, ["portfolio", "risk"])
    assert result.exit_code == 0
    assert "Risk & Exposure Analysis" in result.output
    assert "Gross Exposure" in result.output


def test_portfolio_performance_cli(mock_analytics_data):
    result = runner.invoke(app, ["portfolio", "performance"])
    assert result.exit_code == 0
    assert "Performance Analytics" in result.output
    assert "Win Rate" in result.output


def test_portfolio_allocation_cli(mock_analytics_data):
    result = runner.invoke(app, ["portfolio", "allocation"])
    assert result.exit_code == 0
    assert "Sector Allocation" in result.output


def test_portfolio_export_cli(mock_analytics_data, tmp_path):
    out_file = tmp_path / "report.json"
    result = runner.invoke(
        app, ["portfolio", "export", "--out", str(out_file), "--format", "json"]
    )
    assert result.exit_code == 0
    assert "Success" in result.output
    assert out_file.exists()
