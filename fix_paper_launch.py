
path = 'titan/cli/commands/paper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    launcher.launch(
        [
            sys.executable,
            "-m",
            "titan",
            "paper",
            "serve",
            "--cash",
            str(initial_cash),
            "--symbol",
            symbol.upper(),
            "--exchange",
            exchange.lower(),
        ],
        log_path=Path("logs") / "paper_runtime.log","""

replacement = """    cmd = [
        sys.executable,
        "-m",
        "titan",
        "paper",
        "serve",
        "--cash",
        str(initial_cash),
        "--exchange",
        exchange.lower(),
    ]
    if symbols:
        for sym in symbols:
            cmd.extend(["--symbol", sym.upper()])
            
    launcher.launch(
        cmd,
        log_path=Path("logs") / "paper_runtime.log","""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
