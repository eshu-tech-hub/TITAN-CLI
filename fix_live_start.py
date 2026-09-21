
path = 'titan/cli/commands/live.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    if verbose:
        _start_with_progress(config, symbol=symbol, exchange=exchange)
    else:
        _start_silent(config, symbol=symbol, exchange=exchange)


def _start_silent(config: TitanConfig, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:
    try:
        engine = create_runtime_engine(
            config,
            target_symbol=symbol.upper(),
            target_exchange=exchange.upper(),
        )
        set_runtime_engine(engine)
        engine.target_symbol = symbol.upper()"""

replacement1 = """    if verbose:
        _start_with_progress(config, symbols=symbols, exchange=exchange)
    else:
        _start_silent(config, symbols=symbols, exchange=exchange)


def _start_silent(config: TitanConfig, *, symbols: list[str] | None = None, exchange: str = "nse") -> None:
    try:
        engine = create_runtime_engine(
            config,
            symbols=symbols,
            target_exchange=exchange.upper(),
        )
        set_runtime_engine(engine)
        if symbols:
            engine.watchlist = [s.upper() for s in symbols]"""

content = content.replace(target1, replacement1)

target2 = """def _start_with_progress(config: TitanConfig, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:"""
replacement2 = """def _start_with_progress(config: TitanConfig, *, symbols: list[str] | None = None, exchange: str = "nse") -> None:"""
content = content.replace(target2, replacement2)

target3 = """        try:
            engine = create_runtime_engine(
                config,
                target_symbol=symbol.upper(),
                target_exchange=exchange.upper(),
            )
            set_runtime_engine(engine)
            engine.target_symbol = symbol.upper()"""
replacement3 = """        try:
            engine = create_runtime_engine(
                config,
                symbols=symbols,
                target_exchange=exchange.upper(),
            )
            set_runtime_engine(engine)
            if symbols:
                engine.watchlist = [s.upper() for s in symbols]"""
content = content.replace(target3, replacement3)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
