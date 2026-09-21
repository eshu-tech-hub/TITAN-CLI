
path = 'titan/cli/commands/paper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol to trade")
    ] = "RELIANCE","""
replacement1 = """    symbols: Annotated[
        list[str], typer.Option("--symbol", "-s", help="Target symbols to trade")
    ] = ["RELIANCE"],"""
content = content.replace(target1, replacement1)

target2 = """            _launch_paper_runtime(symbol=symbol)
            
            from titan.cli.common import create_runtime_engine, set_runtime_engine
            from titan.runtime.models import RunMode
            
            # Start background daemon components safely.
            config_mgr = get_config_manager()
            config = config_mgr.get_config()
            engine = create_runtime_engine(config, run_mode=RunMode.PAPER, symbol=symbol)
            if symbol:
                engine.target_symbol = symbol.upper()
            set_runtime_engine(engine)"""
replacement2 = """            _launch_paper_runtime(symbols=symbols)
            
            from titan.cli.common import create_runtime_engine, set_runtime_engine
            from titan.runtime.models import RunMode
            
            # Start background daemon components safely.
            config_mgr = get_config_manager()
            config = config_mgr.get_config()
            engine = create_runtime_engine(config, run_mode=RunMode.PAPER, symbols=symbols)
            if symbols:
                engine.watchlist = [s.upper() for s in symbols]
            set_runtime_engine(engine)"""
content = content.replace(target2, replacement2)

target3 = """def _launch_paper_runtime(symbol: str = "RELIANCE") -> None:"""
replacement3 = """def _launch_paper_runtime(symbols: list[str] | None = None) -> None:"""
content = content.replace(target3, replacement3)

target4 = """    cmd = [sys.executable, titan_exe, "paper", "serve"]
    if symbol:
        cmd.extend(["-s", symbol])"""
replacement4 = """    cmd = [sys.executable, titan_exe, "paper", "serve"]
    if symbols:
        for sym in symbols:
            cmd.extend(["-s", sym])"""
content = content.replace(target4, replacement4)

target5 = """def serve(
    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol to trade")
    ] = "RELIANCE",
) -> None:"""
replacement5 = """def serve(
    symbols: Annotated[
        list[str], typer.Option("--symbol", "-s", help="Target symbols to trade")
    ] = ["RELIANCE"],
) -> None:"""
content = content.replace(target5, replacement5)

target6 = """    engine = create_runtime_engine(config, run_mode=RunMode.PAPER, symbol=symbol)
    if symbol:
        engine.target_symbol = symbol.upper()"""
replacement6 = """    engine = create_runtime_engine(config, run_mode=RunMode.PAPER, symbols=symbols)
    if symbols:
        engine.watchlist = [s.upper() for s in symbols]"""
content = content.replace(target6, replacement6)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
