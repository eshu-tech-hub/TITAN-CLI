
layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add _get_runtime_data and _get_dashboard_data
if 'def _get_runtime_data' not in content:
    get_data_funcs = """

def _get_runtime_data():
    def _fetch_runtime_ipc():
        from titan.runtime.local_transport import LocalTransport
        try:
            client = LocalTransport()
            return client.status()
        except Exception as e:
            return None

    try:
        from titan.tui.layout import _ipc_executor
        future = _ipc_executor.submit(_fetch_runtime_ipc)
        return future.result(timeout=1.0)
    except Exception:
        return None

def _get_dashboard_data():
    def _fetch_dashboard_ipc():
        from titan.runtime.local_transport import LocalTransport
        try:
            client = LocalTransport()
            return client.status()
        except Exception as e:
            return None

    try:
        from titan.tui.layout import _ipc_executor
        future = _ipc_executor.submit(_fetch_dashboard_ipc)
        return future.result(timeout=1.0)
    except Exception:
        return None

def _get_paper_data"""
    content = content.replace("def _get_paper_data", get_data_funcs)


# Patch _read_runtime_engine and friends to accept report
replacements = [
    ("def _read_runtime_engine() -> RuntimeEngineInfo:", "def _read_runtime_engine(report=None) -> RuntimeEngineInfo:"),
    ("def _read_runtime_stream() -> RuntimeStreamInfo:", "def _read_runtime_stream(report=None) -> RuntimeStreamInfo:"),
    ("def _read_runtime_pipeline() -> RuntimePipelineInfo:", "def _read_runtime_pipeline(report=None) -> RuntimePipelineInfo:"),
    ("def _read_runtime_event_bus() -> RuntimeEventBusInfo:", "def _read_runtime_event_bus(report=None) -> RuntimeEventBusInfo:"),
    ("def _read_runtime_components() -> tuple[RuntimeComponentInfo, ...]:", "def _read_runtime_components(report=None) -> tuple[RuntimeComponentInfo, ...]:"),
    ("def _read_runtime_events() -> tuple[RuntimeEventEntry, ...]:", "def _read_runtime_events(report=None) -> tuple[RuntimeEventEntry, ...]:"),

    ("def _read_runtime() -> RuntimeInfo:", "def _read_runtime(report=None) -> RuntimeInfo:"),
    ("def _read_market() -> DashboardMarketInfo:", "def _read_market(report=None) -> DashboardMarketInfo:"),
    ("def _read_trading() -> TradingInfo:", "def _read_trading(report=None) -> TradingInfo:"),
    ("def _read_health() -> HealthInfo:", "def _read_health(report=None) -> HealthInfo:"),
    ("def _read_system() -> SystemInfo:", "def _read_system(report=None) -> SystemInfo:"),
]

for old, new in replacements:
    content = content.replace(old, new)

# We also need to patch their implementations to USE the report if provided!
# We'll just do a global replace for the common pattern.
# They all do:
#        from titan.cli.common import get_runtime_engine
#        engine = get_runtime_engine()
#        report = engine.generate_report()

def apply_report_fallback(func_name, var_name="report"):
    global content
    # We want to insert 'if report is None: ... engine = ... report = ...'
    # Actually, simpler: replace `engine = get_runtime_engine()` with
    # `if report is None: engine = get_runtime_engine(); report = engine.generate_report()`

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)

