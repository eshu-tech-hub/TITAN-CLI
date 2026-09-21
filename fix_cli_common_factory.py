
path = 'titan/cli/common.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """def create_runtime_engine(
    config: TitanConfig,
    run_mode=None,
    symbols: list[str] | None = None,
    *,
    target_symbol: str = "RELIANCE",
    target_exchange: str = "NSE",
) -> RuntimeEngine:"""

replacement = """def create_runtime_engine(
    config: TitanConfig,
    run_mode=None,
    symbols: list[str] | None = None,
    **kwargs,
) -> RuntimeEngine:
    # Safely extract optional kwargs
    target_symbol = kwargs.pop("target_symbol", "RELIANCE")
    target_exchange = kwargs.pop("target_exchange", "NSE")
    watchlist = kwargs.pop("watchlist", None)
    
    if not watchlist:
        watchlist = symbols if symbols else [target_symbol]"""

content = content.replace(target, replacement)

target2 = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        watchlist=symbols if symbols else [target_symbol],
        target_exchange=target_exchange,
    )"""

replacement2 = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        watchlist=watchlist,
        target_exchange=target_exchange,
    )"""

content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
