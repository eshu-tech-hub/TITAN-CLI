
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def _warmup_historical_context(self) -> None:
        import yfinance as yf

        from titan.brokers.models import Exchange"""

replacement = """    def _warmup_historical_context(self) -> None:
        import pandas as pd
        import yfinance as yf

        from titan.brokers.models import Exchange"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
