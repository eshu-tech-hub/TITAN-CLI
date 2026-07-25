from titan.ai.engine import AIAssistantEngine
from titan.ai.models import AIResponse, PromptContext
from titan.ai.providers.gemini import GeminiAIProvider, MockAIProvider
from titan.backtesting.evaluation import StrategyEvaluationReport, StrategyMetrics
from titan.portfolio.models import PortfolioSnapshot


def test_mock_ai_provider():
    provider = MockAIProvider(fixed_response="Test Success")
    context = PromptContext(
        template_name="test",
        system_prompt="sys",
        user_prompt="usr",
    )
    response = provider.generate(context)
    assert isinstance(response, AIResponse)
    assert "Test Success" in response.content
    assert response.provider_name == "mock"


def test_gemini_provider_missing_key():
    provider = GeminiAIProvider(api_key="")
    context = PromptContext(
        template_name="test",
        system_prompt="sys",
        user_prompt="usr",
    )
    response = provider.generate(context)
    assert isinstance(response, AIResponse)
    assert "Missing GEMINI_API_KEY" in response.content


def test_ai_assistant_engine_portfolio_explanation():
    engine = AIAssistantEngine(provider=MockAIProvider())
    snapshot = PortfolioSnapshot(total_capital=100000.0, capital_used=20000.0)
    response = engine.explain_portfolio(snapshot)
    assert isinstance(response, AIResponse)
    assert "explain_portfolio" in response.content


def test_ai_assistant_engine_strategy_explanation():
    engine = AIAssistantEngine(provider=MockAIProvider())
    report = StrategyEvaluationReport(
        strategies=(
            StrategyMetrics(strategy_name="Alpha", total_trades=10, net_pnl=500.0),
        ),
        overall_best_strategy="Alpha",
    )
    response = engine.explain_strategy_evaluation(report)
    assert isinstance(response, AIResponse)
    assert "explain_strategy_evaluation" in response.content
