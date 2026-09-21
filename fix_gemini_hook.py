
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # Record execution results if any orders were submitted"""

replacement = """        # Gemini AI Synthesis Hook
        from titan.pipeline.models import PipelineStatus
        if getattr(report, "status", None) == PipelineStatus.SUCCESS:
            try:
                from titan.ai.providers.gemini import GeminiAIProvider
                from titan.ai.models import PromptContext
                from titan.core.logger import logger
                
                gemini = GeminiAIProvider()
                metrics_summary = f"Symbol: {symbol}, Decision: {report.decision_action}, Evidence: {report.evidence_count}"
                ctx = PromptContext(
                    template_name="trade_bias",
                    system_prompt="You are an institutional trading AI.",
                    user_prompt=f"Given these metrics: {metrics_summary}. Respond with LONG, SHORT, or HOLD."
                )
                ai_response = gemini.generate(ctx)
                logger.info(f"Gemini synthesis for {symbol}: {ai_response.content}")
            except Exception as ai_e:
                from titan.core.logger import logger
                logger.warning(f"Gemini synthesis failed: {ai_e}")

        # Record execution results if any orders were submitted"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
