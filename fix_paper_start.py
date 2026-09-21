
path = 'titan/cli/commands/paper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    if verbose:
        _start_with_progress(cash, symbol=symbol, exchange=exchange)
    else:
        _start_silent(cash, symbol=symbol, exchange=exchange)


def _start_silent(initial_cash: float, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:
    try:
        _launch_paper_runtime(initial_cash, symbol=symbol, exchange=exchange)"""

replacement1 = """    if verbose:
        _start_with_progress(cash, symbols=symbols, exchange=exchange)
    else:
        _start_silent(cash, symbols=symbols, exchange=exchange)


def _start_silent(initial_cash: float, *, symbols: list[str] | None = None, exchange: str = "nse") -> None:
    try:
        _launch_paper_runtime(initial_cash, symbols=symbols, exchange=exchange)"""

content = content.replace(target1, replacement1)

target2 = """def _start_with_progress(initial_cash: float, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:
    _start_silent(initial_cash, symbol=symbol, exchange=exchange)


def _launch_paper_runtime(initial_cash: float, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:"""

replacement2 = """def _start_with_progress(initial_cash: float, *, symbols: list[str] | None = None, exchange: str = "nse") -> None:
    _start_silent(initial_cash, symbols=symbols, exchange=exchange)


def _launch_paper_runtime(initial_cash: float, *, symbols: list[str] | None = None, exchange: str = "nse") -> None:"""

content = content.replace(target2, replacement2)

target3 = """            "serve",
            "--cash",
            str(initial_cash),
            "--symbol",
            symbol,
            "--exchange",
            exchange,
        ]"""
replacement3 = """            "serve",
            "--cash",
            str(initial_cash),
            "--exchange",
            exchange,
        ]
        if symbols:
            for sym in symbols:
                cmd.extend(["--symbol", sym])"""

content = content.replace(target3, replacement3)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
