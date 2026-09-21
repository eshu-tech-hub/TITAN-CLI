
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # Gemini AI Synthesis Hook
        from titan.pipeline.models import PipelineStatus
        if getattr(report, "status", None) == PipelineStatus.SUCCESS:
            try:
                from titan.ai.models import PromptContext
                from titan.ai.providers.gemini import GeminiAIProvider
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
                logger.warning(f"Gemini synthesis failed: {ai_e}")"""

replacement = """        # Gemini AI Synthesis Hook
        from titan.pipeline.models import PipelineStatus
        if getattr(report, "status", None) == PipelineStatus.SUCCESS:
            import time
            from titan.core.logger import logger
            
            # Rate limiting cache
            if not hasattr(self, "_gemini_last_called"):
                self._gemini_last_called = {}
                
            current_time = time.time()
            last_called = self._gemini_last_called.get(symbol, 0.0)
            
            # 60 second cooldown per symbol
            if current_time - last_called >= 60.0:
                try:
                    from titan.ai.models import PromptContext
                    from titan.ai.providers.gemini import GeminiAIProvider
                    
                    gemini = GeminiAIProvider()
                    metrics_summary = f"Symbol: {symbol}, Decision: {report.decision_action}, Evidence: {report.evidence_count}"
                    ctx = PromptContext(
                        template_name="trade_bias",
                        system_prompt="You are an institutional trading AI.",
                        user_prompt=f"Given these metrics: {metrics_summary}. Respond with LONG, SHORT, or HOLD."
                    )
                    ai_response = gemini.generate(ctx)
                    logger.info(f"Gemini synthesis for {symbol}: {ai_response.content}")
                    
                    # Update cache on success
                    self._gemini_last_called[symbol] = current_time
                    
                except Exception as ai_e:
                    logger.warning(f"Gemini synthesis failed: {ai_e}")
                    # If rate limited (429), back off by artificially extending the last called time
                    if "429" in str(ai_e):
                        logger.warning(f"Gemini Rate Limit hit for {symbol}. Applying 5-minute backoff.")
                        self._gemini_last_called[symbol] = current_time + 240.0  # 4 mins + 1 min normal = 5 mins"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
