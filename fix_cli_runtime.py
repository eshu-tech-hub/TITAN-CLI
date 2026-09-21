
path = 'titan/cli/commands/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol")
    ] = "RELIANCE","""
replacement1 = """    symbols: Annotated[
        list[str], typer.Option("--symbol", "-s", help="Target symbols")
    ] = ["RELIANCE"],"""
content = content.replace(target1, replacement1)

target2 = """        cmd = [sys.executable, titan_exe, "runtime", "start"]
        if symbol:
            cmd.extend(["-s", symbol])"""
replacement2 = """        cmd = [sys.executable, titan_exe, "runtime", "start"]
        if symbols:
            for sym in symbols:
                cmd.extend(["-s", sym])"""
content = content.replace(target2, replacement2)

target3 = """        engine = create_runtime_engine(config, symbol=symbol)
        if symbol:
            engine.target_symbol = symbol.upper()
        set_runtime_engine(engine)"""
replacement3 = """        engine = create_runtime_engine(config, symbols=symbols)
        if symbols:
            engine.watchlist = [s.upper() for s in symbols]
        set_runtime_engine(engine)"""
content = content.replace(target3, replacement3)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
