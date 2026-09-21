import re

layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_read_market = """def _read_market(report=None) -> MarketInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        connected = report.broker.connection.lower() == "connected"
        return MarketInfo(
            broker_connected=connected,
            broker_provider="Paper",
            stream_connected=report.market.stream_status.lower() == "connected",
            symbols_tracked=report.market.active_subscriptions,
            last_quote_time=(
                report.market.last_quote_time.strftime("%H:%M:%S")
                if getattr(report.market, "last_quote_time", None)
                else "Never"
            ),
        )
    except Exception:
        return MarketInfo()"""

content = re.sub(r"def _read_market\(\) -> MarketInfo:[\s\S]*?(?=\ndef _read_trading)", new_read_market, content)

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)
