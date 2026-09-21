
path = 'titan/cli/commands/live.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol to trade")
    ] = "RELIANCE","""
replacement1 = """    symbols: Annotated[
        list[str], typer.Option("--symbol", "-s", help="Target symbols to trade")
    ] = ["RELIANCE"],"""
content = content.replace(target1, replacement1)

target2 = """            from titan.cli.common import create_runtime_engine, set_runtime_engine
            from titan.runtime.models import RunMode
            
            engine = create_runtime_engine(config, run_mode=RunMode.LIVE, symbol=symbol)
            if symbol:
                engine.target_symbol = symbol.upper()
            set_runtime_engine(engine)"""
replacement2 = """            from titan.cli.common import create_runtime_engine, set_runtime_engine
            from titan.runtime.models import RunMode
            
            engine = create_runtime_engine(config, run_mode=RunMode.LIVE, symbols=symbols)
            if symbols:
                engine.watchlist = [s.upper() for s in symbols]
            set_runtime_engine(engine)"""
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
