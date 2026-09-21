
path = 'titan/cli/commands/paper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        watchlist=[s.upper() for s in symbols] if symbols else ["RELIANCE"],
        target_exchange=exchange.upper(),
    )
    server = LocalTransportServer(RuntimeService(engine))
    try:"""

replacement = """    from titan.brokers.yfinance.stream import YFinanceStreamSource
    from titan.runtime.stream import MarketStream
    stream_source = YFinanceStreamSource(poll_interval=60.0)
    market_stream = MarketStream(source=stream_source)

    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        stream=market_stream,
        watchlist=[s.upper() for s in symbols] if symbols else ["RELIANCE"],
        target_exchange=exchange.upper(),
    )
    market_stream.set_on_quote(engine._pipeline_runner)
    server = LocalTransportServer(RuntimeService(engine))
    try:"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
