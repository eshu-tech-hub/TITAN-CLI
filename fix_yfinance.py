import re

path = 'titan/brokers/yfinance/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

subscribe_code = """    def subscribe(self, symbols: list[str] | str, exchange: str | Exchange = "NSE") -> None:
        if isinstance(symbols, str):
            symbols = [symbols]
            
        normalized = []
        for sym in symbols:
            if sym.startswith("^"):
                normalized.append(sym)
            elif not sym.endswith(".NS") and not sym.endswith(".BO"):
                normalized.append(f"{sym}.NS")
            else:
                normalized.append(sym)
        self._subscriptions.update(normalized)

    def unsubscribe(self, symbols: list[str] | str, exchange: str | Exchange = "NSE") -> None:
        if isinstance(symbols, str):
            symbols = [symbols]
            
        normalized = []
        for sym in symbols:
            if sym.startswith("^"):
                normalized.append(sym)
            elif not sym.endswith(".NS") and not sym.endswith(".BO"):
                normalized.append(f"{sym}.NS")
            else:
                normalized.append(sym)
        for sym in normalized:
            self._subscriptions.discard(sym)"""

content = re.sub(r"    def subscribe\(self, symbols: list\[str\] \| str, exchange: str \| Exchange = \"NSE\"\) -> None:[\s\S]*?(?=\n    def _poll_loop)", subscribe_code, content)

# Fix _poll_loop yf_symbol
content = content.replace(
    'yf_symbol = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"',
    'yf_symbol = symbol'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
