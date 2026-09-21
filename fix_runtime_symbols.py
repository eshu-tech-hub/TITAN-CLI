
path = 'titan/cli/commands/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        titan_exe = [sys.executable, "-m", "titan", "runtime", "start"]
        if symbol:
            titan_exe.extend(["--symbol", symbol])
        if verbose:"""

replacement = """        titan_exe = [sys.executable, "-m", "titan", "runtime", "start"]
        if symbols:
            for sym in symbols:
                titan_exe.extend(["--symbol", sym])
        if verbose:"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
