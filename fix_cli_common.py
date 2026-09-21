
path = 'titan/cli/common.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """def create_runtime_engine(
    config: TitanConfig,
    run_mode=None,
    symbol: str | None = None,
    *,
    target_symbol: str = "RELIANCE",
    target_exchange: str = "NSE",
) -> RuntimeEngine:"""
replacement1 = """def create_runtime_engine(
    config: TitanConfig,
    run_mode=None,
    symbols: list[str] | None = None,
    *,
    target_symbol: str = "RELIANCE",
    target_exchange: str = "NSE",
) -> RuntimeEngine:"""
content = content.replace(target1, replacement1)

target2 = """    if symbol:
        engine.target_symbol = symbol"""
replacement2 = """    if symbols:
        engine.watchlist = symbols
    elif target_symbol:
        engine.watchlist = [target_symbol]"""
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
