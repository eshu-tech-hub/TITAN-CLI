import re

layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

dashboard_state = """def build_dashboard_state(report=None) -> DashboardState:
    runtime = _read_runtime(report)
    market = _read_market(report)
    trading = _read_trading(report)
    health = _read_health(report)
    system = _read_system(report)

    from datetime import datetime
    now = datetime.now().strftime("%H:%M:%S")

    return DashboardState(
        runtime=runtime,
        market=market,
        trading=trading,
        health=health,
        system=system,
        last_refresh=now,
    )"""

runtime_state = """def build_runtime_state(report=None) -> RuntimeScreenState:
    engine_info = _read_runtime_engine(report)
    stream_info = _read_runtime_stream(report)
    pipeline_info = _read_runtime_pipeline(report)
    event_bus_info = _read_runtime_event_bus(report)
    components = _read_runtime_components(report)
    events = _read_runtime_events(report)

    from datetime import datetime
    now = datetime.now().strftime("%H:%M:%S")

    return RuntimeScreenState(
        engine=engine_info,
        stream=stream_info,
        pipeline=pipeline_info,
        event_bus=event_bus_info,
        components=components,
        events=events,
        last_refresh=now,
    )"""

content = re.sub(r"def build_dashboard_state\(\) -> DashboardState:[\s\S]*?(?=\n\n\ndef _read_runtime)", dashboard_state, content)
content = re.sub(r"def build_runtime_state\(\) -> RuntimeScreenState:[\s\S]*?(?=\n\n\ndef _read_runtime_engine)", runtime_state, content)

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)
