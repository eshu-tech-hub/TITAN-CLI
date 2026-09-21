
path = 'titan/brokers/yfinance/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                    if self._on_quote:
                        self._on_quote(quote)"""

replacement = """                    if self._on_quote:
                        try:
                            self._on_quote(quote)
                        except Exception as e:
                            import traceback
                            with open("titan_crash.log", "a") as err_f:
                                err_f.write(f"Pipeline Execution Crash:\\n{traceback.format_exc()}\\n")"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
