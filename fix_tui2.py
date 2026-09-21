import re

layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

def patch_func(func_name, code):
    global content
    pattern = rf"(def {func_name}\(report=None\).*?:[\s\S]*?)(?=\n\n\w)"
    content = re.sub(pattern, code, content)

engine_code = """def _read_runtime_engine(report=None) -> RuntimeEngineInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            status = engine.status.name
            is_running = engine.is_running
            report = engine.generate_report()
        else:
            status = report.runtime_status.name
            is_running = status == "RUNNING"
            
        uptime = _format_uptime(report.performance.uptime_seconds)
        scheduler_active = report.scheduler.active

        return RuntimeEngineInfo(
            status=status,
            uptime=uptime,
            is_running=is_running,
            scheduler_active=scheduler_active,
        )
    except Exception:
        return RuntimeEngineInfo()"""

stream_code = """def _read_runtime_stream(report=None) -> RuntimeStreamInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        return RuntimeStreamInfo(
            connected=report.market.stream_status.lower() == "connected",
            symbols_tracked=report.market.active_subscriptions,
            tick_rate="N/A",
        )
    except Exception:
        return RuntimeStreamInfo()"""

pipeline_code = """def _read_runtime_pipeline(report=None) -> RuntimePipelineInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        return RuntimePipelineInfo(
            executions=report.scheduler.pipeline_executions,
            avg_runtime="N/A",
            last_run=_format_relative_time(report.scheduler.last_pipeline_time),
        )
    except Exception:
        return RuntimePipelineInfo()"""

eb_code = """def _read_runtime_event_bus(report=None) -> RuntimeEventBusInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            bus = engine.event_bus
            from titan.runtime.models import RuntimeEventType
            total_subscribers = sum(bus.listener_count(et) for et in RuntimeEventType)
        else:
            total_subscribers = 0 # Not exposed in RuntimeReport currently
            
        return RuntimeEventBusInfo(
            published=0,
            subscribers=total_subscribers,
        )
    except Exception:
        return RuntimeEventBusInfo()"""

comp_code = """def _read_runtime_components(report=None) -> tuple[RuntimeComponentInfo, ...]:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        return tuple(
            RuntimeComponentInfo(
                name=comp.component_name,
                status=comp.status.value,
            )
            for comp in report.health.component_health
        )
    except Exception:
        return ()"""

events_code = """def _read_runtime_events(report=None) -> tuple[RuntimeEventEntry, ...]:
    entries = []
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        for warning in report.health.warnings:
            entries.append(RuntimeEventEntry(level="warning", source="runtime", message=warning))
        for error in report.health.errors:
            entries.append(RuntimeEventEntry(level="error", source="runtime", message=error))
    except Exception:
        pass
    return tuple(entries[-20:])"""

# Dashboard read funcs
dr_runtime = """def _read_runtime(report=None) -> RuntimeInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        is_running = report.runtime_status.name == "RUNNING"
        return RuntimeInfo(
            status=report.runtime_status.name,
            uptime=_format_uptime(report.performance.uptime_seconds),
            is_running=is_running,
            pipeline_executions=report.scheduler.pipeline_executions,
            broker_status=report.broker.connection,
            stream_status=report.market.stream_status,
        )
    except Exception:
        return RuntimeInfo()"""

dr_market = """def _read_market(report=None) -> DashboardMarketInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        return DashboardMarketInfo(
            active_subscriptions=report.market.active_subscriptions,
            ticks_processed=0,
            errors=0,
        )
    except Exception:
        return DashboardMarketInfo()"""

dr_trading = """def _read_trading(report=None) -> TradingInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        return TradingInfo(
            signals_generated=0,
            orders_placed=report.paper.total_orders if report.paper else 0,
            active_positions=report.portfolio.active_positions if report.portfolio else 0,
            win_rate=0.0,
        )
    except Exception:
        return TradingInfo()"""

dr_health = """def _read_health(report=None) -> HealthInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        degraded = sum(1 for c in report.health.component_health if c.status.value != "healthy")
        return HealthInfo(
            system_status="Healthy" if degraded == 0 else "Degraded",
            degraded_components=degraded,
            last_error=report.health.errors[-1] if report.health.errors else "None",
        )
    except Exception:
        return HealthInfo()"""

dr_system = """def _read_system(report=None) -> SystemInfo:
    try:
        if report is None:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
        return SystemInfo(
            cpu_usage=report.resource.cpu_percent,
            memory_usage=report.resource.memory_percent,
            threads=0,
            latency=0.0,
        )
    except Exception:
        return SystemInfo()"""


content = re.sub(r"def _read_runtime_engine\(report=None\) -> RuntimeEngineInfo:[\s\S]*?(?=\ndef _read_runtime_stream)", engine_code, content)
content = re.sub(r"def _read_runtime_stream\(report=None\) -> RuntimeStreamInfo:[\s\S]*?(?=\ndef _read_runtime_pipeline)", stream_code, content)
content = re.sub(r"def _read_runtime_pipeline\(report=None\) -> RuntimePipelineInfo:[\s\S]*?(?=\ndef _read_runtime_event_bus)", pipeline_code, content)
content = re.sub(r"def _read_runtime_event_bus\(report=None\) -> RuntimeEventBusInfo:[\s\S]*?(?=\ndef _read_runtime_components)", eb_code, content)
content = re.sub(r"def _read_runtime_components\(report=None\) -> tuple\[RuntimeComponentInfo, \.\.\.\]:[\s\S]*?(?=\ndef _read_runtime_events)", comp_code, content)
content = re.sub(r"def _read_runtime_events\(report=None\) -> tuple\[RuntimeEventEntry, \.\.\.\]:[\s\S]*?(?=\n\n\ndef _)", events_code, content)

content = re.sub(r"def _read_runtime\(report=None\) -> RuntimeInfo:[\s\S]*?(?=\ndef _read_market)", dr_runtime, content)
content = re.sub(r"def _read_market\(report=None\) -> DashboardMarketInfo:[\s\S]*?(?=\ndef _read_trading)", dr_market, content)
content = re.sub(r"def _read_trading\(report=None\) -> TradingInfo:[\s\S]*?(?=\ndef _read_health)", dr_trading, content)
content = re.sub(r"def _read_health\(report=None\) -> HealthInfo:[\s\S]*?(?=\ndef _read_system)", dr_health, content)
content = re.sub(r"def _read_system\(report=None\) -> SystemInfo:[\s\S]*?(?=\n\n\ndef _format)", dr_system, content)

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)

