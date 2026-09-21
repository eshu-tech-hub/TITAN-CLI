
path = 'titan/cli/commands/paper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        watchlist=[s.upper() for s in symbols] if symbols else ["RELIANCE"],
        target_exchange=exchange.upper(),
    )
    market_stream.set_on_quote(engine._pipeline_runner)"""

replacement = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        watchlist=[s.upper() for s in symbols] if symbols else ["RELIANCE"],
        target_exchange=exchange.upper(),
    )
    stream_source.subscribe(engine.watchlist)
    market_stream.set_on_quote(engine._pipeline_runner)"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
