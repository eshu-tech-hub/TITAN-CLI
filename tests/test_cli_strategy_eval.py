from unittest.mock import patch

from typer.testing import CliRunner

from titan.cli.commands.backtest import app

runner = CliRunner()


def test_backtest_evaluate_cli_empty():
    """Verify the evaluate command handles an empty journal gracefully."""
    with patch("titan.cli.common.get_runtime_engine") as mock_engine:
        # Mock an empty repository
        mock_engine.return_value.trade_journal.repository.list.return_value = []

        result = runner.invoke(app, ["evaluate"])

        assert result.exit_code == 0
        assert "No strategies found" in result.output


def test_backtest_evaluate_cli_json():
    """Verify the evaluate command produces valid JSON output."""
    with patch("titan.cli.common.get_runtime_engine") as mock_engine:
        mock_engine.return_value.trade_journal.repository.list.return_value = []

        result = runner.invoke(app, ["evaluate", "--json"])

        assert result.exit_code == 0
        assert "strategies" in result.output
