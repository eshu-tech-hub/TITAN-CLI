
path = 'titan/cli/common.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        target_symbol=target_symbol,
        target_exchange=target_exchange,
    )"""

replacement = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        watchlist=symbols if symbols else [target_symbol],
        target_exchange=target_exchange,
    )"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
