
path = 'titan/cli/commands/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """def start(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show startup progress")
    ] = False,
    detach: Annotated[
        bool, typer.Option("--detach", "-d", help="Run in background")
    ] = False,
) -> None:"""

replacement = """def start(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show startup progress")
    ] = False,
    detach: Annotated[
        bool, typer.Option("--detach", "-d", help="Run in background")
    ] = False,
    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol")
    ] = "RELIANCE",
) -> None:"""
content = content.replace(target, replacement)

target2 = """        titan_exe = [sys.executable, "-m", "titan", "runtime", "start"]
        if verbose:
            titan_exe.append("--verbose")"""

replacement2 = """        titan_exe = [sys.executable, "-m", "titan", "runtime", "start"]
        if symbol:
            titan_exe.extend(["--symbol", symbol])
        if verbose:
            titan_exe.append("--verbose")"""

content = content.replace(target2, replacement2)

target3 = """    engine = get_runtime_engine()
    service = RuntimeService(engine)"""

replacement3 = """    engine = get_runtime_engine()
    if symbol:
        engine.target_symbol = symbol.upper()
    service = RuntimeService(engine)"""
content = content.replace(target3, replacement3)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
