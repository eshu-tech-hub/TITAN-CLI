"""titan runtime - Lightweight local IPC transport for detached processes."""

import json
import socket
import threading
from dataclasses import asdict
from typing import Any, cast

from titan.runtime.exceptions import RuntimeError as TitanRuntimeError
from titan.runtime.models import RuntimeReport
from titan.runtime.service import RuntimeService
from titan.runtime.transport import RuntimeTransport

DEFAULT_PORT = 55555


class LocalTransportServer:
    """A minimal TCP server to expose RuntimeService status and commands."""

    def __init__(self, service: RuntimeService, port: int = DEFAULT_PORT):
        self.service = service
        self.port = port
        self._server_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._stop_event.clear()
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("[8] Transport server binding", flush=True)
        self._server_socket.bind(("127.0.0.1", self.port))
        import os

        print(f"PID: {os.getpid()}", flush=True)
        print(f"Listening: 127.0.0.1:{self.port}", flush=True)
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self._server_socket:
                break
            try:
                conn, _ = self._server_socket.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            try:
                data = conn.recv(1024).decode("utf-8").strip()
                if not data:
                    conn.close()
                    continue

                response = self._handle_request(data)
                conn.sendall(json.dumps(response).encode("utf-8"))
            except Exception:
                pass
            finally:
                conn.close()

    def _handle_request(self, command: str) -> dict[str, Any]:
        if command == "status":
            try:
                report = self.service.status()
                return {"status": "ok", "data": _report_to_dict(report)}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif command == "stop":
            try:
                # Issue the stop command asynchronously so we can return OK
                threading.Thread(target=self.service.stop, daemon=True).start()
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif command == "enable_paper":
            try:
                self.service.enable_paper()
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif command == "disable_paper":
            try:
                self.service.disable_paper()
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif command == "paper_status":
            try:
                broker = self.service.engine.broker
                from decimal import Decimal
                from datetime import datetime, timezone

                open_positions = (
                    broker.position_engine.open_positions()
                    if hasattr(broker, "position_engine")
                    else []
                )
                if hasattr(broker, "portfolio"):
                    portfolio_state = broker.portfolio.compute_state(open_positions)
                else:
                    portfolio_state = None

                perf = None
                if hasattr(broker, "performance") and portfolio_state:
                    perf = broker.performance.compute(portfolio_state)

                all_orders = (
                    broker.journal.all_orders() if hasattr(broker, "journal") else []
                )
                all_trades = (
                    broker.journal.to_broker_trades()
                    if hasattr(broker, "journal")
                    else []
                )

                realized_pnl = sum(
                    (p.realized_pnl for p in open_positions), Decimal("0")
                )

                def _d(v):
                    return float(v) if v is not None else 0.0

                data = {
                    "running": True,
                    "connected": broker.is_connected(),
                    "initial_cash": _d(getattr(broker, "_initial_cash", 100000.0)),
                    "cash_balance": (
                        _d(portfolio_state.cash) if portfolio_state else 0.0
                    ),
                    "portfolio_value": (
                        _d(portfolio_state.equity) if portfolio_state else 0.0
                    ),
                    "buying_power": (
                        _d(portfolio_state.buying_power) if portfolio_state else 0.0
                    ),
                    "exposure": (
                        _d(portfolio_state.exposure) if portfolio_state else 0.0
                    ),
                    "open_positions": len(open_positions),
                    "closed_trades": len(all_trades),
                    "total_orders": len(all_orders),
                    "filled_orders": sum(
                        1
                        for o in all_orders
                        if getattr(o.status, "value", str(o.status)) == "filled"
                    ),
                    "realized_pnl": _d(realized_pnl),
                    "unrealized_pnl": _d(
                        (portfolio_state.total_pnl - realized_pnl)
                        if portfolio_state
                        else 0.0
                    ),
                    "total_pnl": (
                        _d(portfolio_state.total_pnl) if portfolio_state else 0.0
                    ),
                    "daily_pnl": (
                        _d(portfolio_state.daily_pnl) if portfolio_state else 0.0
                    ),
                    "drawdown": (
                        _d(portfolio_state.drawdown) if portfolio_state else 0.0
                    ),
                    "win_rate": _d(perf.win_rate) if perf else 0.0,
                    "loss_rate": _d(perf.loss_rate) if perf else 0.0,
                    "profit_factor": _d(perf.profit_factor) if perf else 0.0,
                    "max_drawdown": _d(perf.max_drawdown) if perf else 0.0,
                    "total_trades": perf.total_trades if perf else 0,
                    "winning_trades": perf.winning_trades if perf else 0,
                    "losing_trades": perf.losing_trades if perf else 0,
                    "expectancy": _d(perf.expectancy) if perf else 0.0,
                    "session_uptime_seconds": self.service.engine.uptime_seconds,
                    "start_time": getattr(
                        self.service.engine, "_start_time", datetime.now(timezone.utc)
                    ).isoformat(),
                }
                return {"status": "ok", "data": data}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}


def _report_to_dict(report: RuntimeReport) -> dict[str, Any]:
    data = asdict(report)

    def _clean(obj: object) -> Any:
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_clean(i) for i in obj]
        if hasattr(obj, "isoformat"):
            return str(obj.isoformat())
        if hasattr(obj, "value"):
            return str(obj.value)
        return obj

    return cast(dict[str, Any], _clean(data))


class LocalTransport(RuntimeTransport):
    """Client for the local TCP IPC server."""

    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port

    def _send_command(self, command: str) -> dict[str, Any]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(("127.0.0.1", self.port))
                s.sendall(command.encode("utf-8"))
                response_data = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                return cast(dict[str, Any], json.loads(response_data.decode("utf-8")))
        except ConnectionRefusedError:
            raise TitanRuntimeError(
                "Runtime engine is not running (connection refused)."
            )
        except socket.timeout:
            raise TitanRuntimeError("Timeout waiting for runtime engine response.")
        except Exception as e:
            raise TitanRuntimeError(f"IPC error: {e}")

    def start(self) -> None:
        raise NotImplementedError(
            "LocalTransport client cannot start a detached process."
        )

    def stop(self) -> None:
        resp = self._send_command("stop")
        if resp.get("status") != "ok":
            raise TitanRuntimeError(resp.get("message", "Unknown error"))

    def restart(self) -> None:
        raise NotImplementedError("Restart not supported over IPC.")

    def status(self) -> RuntimeReport:
        resp = self._send_command("status")
        if resp.get("status") != "ok":
            raise TitanRuntimeError(resp.get("message", "Unknown error"))

        # We need to reconstruct the RuntimeReport from JSON dict
        # Since it's nested dataclasses, we do a basic structural recreation
        # To avoid massive boilerplate, we return a mock RuntimeReport using
        # the raw dict if needed, or we just rely on the CLI handling dict.
        # However, the Transport protocol returns `RuntimeReport`.
        data = resp["data"]
        return self._reconstruct_report(data)

    def enable_paper(self) -> None:
        resp = self._send_command("enable_paper")
        if resp.get("status") != "ok":
            raise TitanRuntimeError(resp.get("message", "Unknown error"))

    def disable_paper(self) -> None:
        resp = self._send_command("disable_paper")
        if resp.get("status") != "ok":
            raise TitanRuntimeError(resp.get("message", "Unknown error"))

    def paper_status(self) -> dict[str, Any]:
        resp = self._send_command("paper_status")
        if resp.get("status") != "ok":
            raise TitanRuntimeError(resp.get("message", "Unknown error"))
        return cast(dict[str, Any], resp.get("data", {}))

    def _reconstruct_report(self, data: dict[str, Any]) -> RuntimeReport:
        from titan.runtime.models import (
            RuntimeStatus,
            RuntimeHealth,
            SchedulerStatus,
            BrokerStatus,
            MarketStatus,
            JournalStatus,
            ResourceStatus,
            PerformanceStatus,
            RecoveryStatus,
            PaperBrokerStatus,
            PortfolioStatus,
            ComponentHealth,
            HealthStatus,
        )
        from titan.brokers.models import ConnectionStatus
        from datetime import datetime

        def parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return None

        # Component health
        comp_health = []
        for ch in data.get("health", {}).get("component_health", []):
            try:
                status_enum = HealthStatus(ch.get("status", "unknown"))
            except ValueError:
                status_enum = HealthStatus.UNKNOWN

            comp_health.append(
                ComponentHealth(
                    component_name=ch.get("component_name", ""),
                    status=status_enum,
                    status_changed_at=parse_dt(ch.get("status_changed_at"))
                    or datetime.now(),
                    last_update=parse_dt(ch.get("last_update")),
                    latency_ms=ch.get("latency_ms", 0.0),
                    error=ch.get("error", ""),
                )
            )

        health = RuntimeHealth(
            component_health=tuple(comp_health),
            warnings=tuple(data.get("health", {}).get("warnings", [])),
            errors=tuple(data.get("health", {}).get("errors", [])),
        )

        try:
            conn_status = ConnectionStatus(
                data.get("broker", {}).get("connection", "disconnected")
            )
        except ValueError:
            conn_status = ConnectionStatus.DISCONNECTED

        broker = BrokerStatus(connection=conn_status)

        scheduler = SchedulerStatus(
            active=data.get("scheduler", {}).get("active", False),
            pipeline_executions=data.get("scheduler", {}).get("pipeline_executions", 0),
            last_pipeline_time=parse_dt(
                data.get("scheduler", {}).get("last_pipeline_time")
            ),
        )

        market = MarketStatus(
            stream_status=data.get("market", {}).get("stream_status", "disconnected"),
            active_subscriptions=data.get("market", {}).get("active_subscriptions", 0),
            last_quote_time=parse_dt(data.get("market", {}).get("last_quote_time")),
        )

        perf = PerformanceStatus(
            uptime_seconds=data.get("performance", {}).get("uptime_seconds", 0.0)
        )

        try:
            rs = RuntimeStatus[data.get("runtime_status", "STOPPED").upper()]
        except KeyError:
            rs = RuntimeStatus.STOPPED

        return RuntimeReport(
            runtime_status=rs,
            health=health,
            scheduler=scheduler,
            broker=broker,
            market=market,
            journal=JournalStatus(),
            resource=ResourceStatus(),
            performance=perf,
            recovery=RecoveryStatus(),
            paper=PaperBrokerStatus(active=data.get("paper", {}).get("active", False)),
            portfolio=PortfolioStatus(),
            timestamp=parse_dt(data.get("timestamp")) or datetime.now(),
        )
