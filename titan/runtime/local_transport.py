"""titan runtime - Lightweight local IPC transport for detached processes."""

import json
import socket
import threading
from dataclasses import asdict
from datetime import UTC
from enum import Enum
from typing import Any, cast

from titan.core.logger import logger
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
        self.publisher = None

    def _publish_status_event(self, event) -> None:
        if self.publisher and not self._stop_event.is_set():
            try:
                status = self._build_paper_status()
                self.publisher.publish("paper.status", status)
            except Exception:  # noqa: BLE001, S110
                pass

    def _publish_trade_event(self, event) -> None:
        if self.publisher and not self._stop_event.is_set():
            try:
                self.publisher.publish("paper.trade", event.data)
            except Exception:  # noqa: BLE001, S110
                pass

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise TitanRuntimeError("Local transport server is already running.")

        self._stop_event.clear()
        
        # Initialize ZeroMQ Publisher
        from titan.runtime.models import RuntimeEventType
        from titan.runtime.publisher import StatePublisher
        self.publisher = StatePublisher()
        
        self.service.engine.event_bus.subscribe(
            RuntimeEventType.SCHEDULER_TICK, self._publish_status_event
        )
        self.service.engine.event_bus.subscribe(
            RuntimeEventType.PIPELINE_EXECUTED, self._publish_status_event
        )
        self.service.engine.event_bus.subscribe(
            RuntimeEventType.TRADE_EXECUTED, self._publish_trade_event
        )

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._server_socket.bind(("127.0.0.1", self.port))
            self.port = cast(int, self._server_socket.getsockname()[1])
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)
        except Exception:
            self._server_socket.close()
            self._server_socket = None
            raise

        self._thread = threading.Thread(
            target=self._run,
            name=f"runtime-transport-{self.port}",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self.publisher:
            try:
                self.publisher.close()
            except Exception:  # noqa: BLE001, S110
                pass
            self.publisher = None
            
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError as exc:
                logger.warning(f"Failed to close local transport socket: {exc}")
            finally:
                self._server_socket = None

        if self._thread:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.error("Local transport server did not stop within two seconds")
            else:
                self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self._server_socket:
                break
            try:
                conn, _ = self._server_socket.accept()
            except TimeoutError:
                continue
            except OSError:
                if not self._stop_event.is_set():
                    logger.exception("Local transport accept failed")
                break

            with conn:
                try:
                    conn.settimeout(2.0)
                    data = conn.recv(1024).decode("utf-8").strip()
                    if not data:
                        continue

                    response = self._handle_request(data)
                    conn.sendall(json.dumps(response).encode("utf-8"))
                except TimeoutError:
                    logger.warning(
                        "Local transport client timed out before completing a request"
                    )
                except OSError as exc:
                    if not self._stop_event.is_set():
                        logger.warning(f"Local transport client I/O failed: {exc}")

    def _handle_request(self, command: str) -> dict[str, Any]:
        if command == "status":
            try:
                report = self.service.status()
                return {"status": "ok", "data": _report_to_dict(report)}
            except Exception as e:  # noqa: BLE001
                return {"status": "error", "message": str(e)}
        elif command == "stop":
            try:
                self.service.stop()
                return {"status": "ok"}
            except Exception as e:  # noqa: BLE001
                return {"status": "error", "message": str(e)}
        elif command == "enable_paper":
            try:
                self.service.enable_paper()
                return {"status": "ok"}
            except Exception as e:  # noqa: BLE001
                return {"status": "error", "message": str(e)}
        elif command == "disable_paper":
            try:
                self.service.disable_paper()
                return {"status": "ok"}
            except Exception as e:  # noqa: BLE001
                return {"status": "error", "message": str(e)}
        elif command == "paper_status":
            try:
                response = self._build_paper_status()
                return {"status": "ok", "data": response.model_dump(mode="json")}
            except Exception as e:  # noqa: BLE001
                return {"status": "error", "message": str(e)}
        elif command == "live_status":
            try:
                broker = self.service.engine.broker
                funds = broker.funds() if hasattr(broker, "funds") else None
                margin = broker.margin() if hasattr(broker, "margin") else None
                positions = broker.positions() if hasattr(broker, "positions") else []
                orders = broker.orders() if hasattr(broker, "orders") else []

                def _d(v):
                    return float(v) if v is not None else 0.0

                data = {
                    "provider": type(broker).__name__,
                    "is_connected": broker.is_connected(),
                    "funds": {
                        "available_cash": _d(funds.available_cash) if funds else 0.0,
                        "payin": _d(funds.payin) if funds else 0.0,
                        "payout": _d(funds.payout) if funds else 0.0,
                    },
                    "margin": {
                        "used_margin": _d(margin.used_margin) if margin else 0.0,
                        "available_margin": _d(margin.available_margin) if margin else 0.0,
                    },
                    "positions": [
                        {
                            "symbol": p.symbol,
                            "exchange": p.exchange.value if hasattr(p.exchange, "value") else str(p.exchange),
                            "product": p.product.value if hasattr(p.product, "value") else str(p.product),
                            "quantity": p.quantity,
                            "buy_qty": getattr(p, "buy_quantity", 0),
                            "sell_qty": getattr(p, "sell_quantity", 0),
                            "avg_price": _d(getattr(p, "buy_price", 0.0)),
                            "current_price": _d(getattr(p, "current_price", 0.0)),
                            "pnl": _d(getattr(p, "pnl", 0.0)),
                            "realised_pnl": _d(getattr(p, "realised_pnl", 0.0)),
                        }
                        for p in positions
                    ],
                    "orders": [
                        {
                            "order_id": o.broker_order_id,
                            "symbol": o.symbol,
                            "side": o.side.value if hasattr(o.side, "value") else str(o.side),
                            "type": o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type),
                            "quantity": getattr(o, "quantity", getattr(o, "total_quantity", 0)),
                            "filled_quantity": getattr(o, "filled_quantity", 0),
                            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                        }
                        for o in orders
                    ],
                    "market_status": {
                        "stream_connected": getattr(self.service.engine.stream, 'connected', getattr(self.service.engine.stream, 'is_connected', False)) if self.service.engine.stream else False,
                        "symbols": list(getattr(self.service.engine.stream, 'symbols', getattr(self.service.engine.stream, 'subscribed_symbols', []))) if self.service.engine.stream else [],
                    }
                }
                return {"status": "ok", "data": data}
            except Exception as e:  # noqa: BLE001
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}



    def _build_paper_status(self):
        broker = self.service.engine.broker
        from datetime import datetime
        from decimal import Decimal

        from titan.paper.broker import PaperBroker

        if not isinstance(broker, PaperBroker):
            raise TypeError("The active runtime is not using the paper broker.")

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

        realized_pnl = sum((p.realized_pnl for p in open_positions), Decimal(0))

        def _d(v):
            return float(v) if v is not None else 0.0

        from titan.ipc.models import (
            PaperAccountPayload,
            PaperOrderPayload,
            PaperPerformancePayload,
            PaperPortfolioPayload,
            PaperPositionPayload,
            PaperSessionPayload,
            PaperStatusResponse,
            PaperTradePayload,
        )

        initial_cash = _d(getattr(broker, "_initial_cash", 100000.0))
        buying_power = _d(portfolio_state.buying_power) if portfolio_state else 0.0
        used_margin = initial_cash - buying_power if buying_power < initial_cash else 0.0

        session_payload = PaperSessionPayload(
            running=self.service.engine.is_running,
            connected=broker.is_connected(),
            stream_connected=getattr(self.service.engine.stream, 'connected', getattr(self.service.engine.stream, 'is_connected', False)),
            stream_symbols=getattr(self.service.engine.stream, 'symbols', getattr(self.service.engine.stream, 'subscribed_symbols', [])),
            session_uptime_seconds=self.service.engine.uptime_seconds,
            start_time=getattr(self.service.engine, "_start_time", datetime.now(UTC)),
        )
        account_payload = PaperAccountPayload(
            initial_cash=initial_cash,
            cash_balance=_d(portfolio_state.cash) if portfolio_state else 0.0,
            buying_power=buying_power,
            used_margin=used_margin,
            payout=0.0,
        )
        portfolio_payload = PaperPortfolioPayload(
            portfolio_value=_d(portfolio_state.equity) if portfolio_state else 0.0,
            exposure=_d(portfolio_state.exposure) if portfolio_state else 0.0,
            open_positions_count=len(open_positions),
            realized_pnl=_d(realized_pnl),
            unrealized_pnl=_d((portfolio_state.total_pnl - realized_pnl) if portfolio_state else 0.0),
            total_pnl=_d(portfolio_state.total_pnl) if portfolio_state else 0.0,
            daily_pnl=_d(portfolio_state.daily_pnl) if portfolio_state else 0.0,
            drawdown=_d(portfolio_state.drawdown) if portfolio_state else 0.0,
        )
        performance_payload = PaperPerformancePayload(
            closed_trades_count=len(all_trades),
            total_orders_count=len(all_orders),
            filled_orders_count=sum(1 for o in all_orders if getattr(o.status, "value", str(o.status)) == "filled"),
            win_rate=_d(perf.win_rate) if perf else 0.0,
            loss_rate=_d(perf.loss_rate) if perf else 0.0,
            profit_factor=_d(perf.profit_factor) if perf else 0.0,
            max_drawdown=_d(perf.max_drawdown) if perf else 0.0,
            total_trades=perf.total_trades if perf else 0,
            winning_trades=perf.winning_trades if perf else 0,
            losing_trades=perf.losing_trades if perf else 0,
            expectancy=_d(perf.expectancy) if perf else 0.0,
        )
        positions_payload = [
            PaperPositionPayload(
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=_d(position.average_price),
                current_price=_d(broker.ltp(position.symbol)),
                unrealized_pnl=_d(position.unrealized_pnl),
                realized_pnl=_d(position.realized_pnl),
            )
            for position in open_positions
        ]
        orders_payload = [
            PaperOrderPayload(
                order_id=order.broker_order_id,
                symbol=order.symbol,
                side=order.side.value if hasattr(order.side, "value") else str(order.side),
                type=order.order_type.value if hasattr(order.order_type, "value") else str(order.order_type),
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                status=order.status.value if hasattr(order.status, "value") else str(order.status),
                price=_d(getattr(order, "average_price", getattr(order, "price", 0))),
                placed_at=order.placed_at if hasattr(order, "placed_at") else None,
            )
            for order in all_orders
        ]
        trades_payload = [
            PaperTradePayload(
                symbol=trade.symbol,
                side=trade.side.value if hasattr(trade.side, "value") else str(trade.side),
                quantity=trade.quantity,
                price=_d(getattr(trade, "price", 0)),
                pnl=_d(getattr(trade, "pnl", 0)),
                timestamp=trade.timestamp if hasattr(trade, "timestamp") else None,
            )
            for trade in all_trades[-20:]
        ]

        return PaperStatusResponse(
            status="ok",
            session=session_payload,
            account=account_payload,
            portfolio=portfolio_payload,
            performance=performance_payload,
            positions=positions_payload,
            orders=orders_payload,
            trades=trades_payload,
        )

def _report_to_dict(report: RuntimeReport) -> dict[str, Any]:
    data = asdict(report)

    def _clean(obj: object) -> Any:
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_clean(i) for i in obj]
        if hasattr(obj, "isoformat"):
            return str(obj.isoformat())
        if isinstance(obj, Enum):
            if isinstance(obj.value, str):
                return obj.value
            return obj.name.lower()
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
        except TimeoutError:
            raise TitanRuntimeError("Timeout waiting for runtime engine response.")
        except Exception as e:  # noqa: BLE001
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

    def live_status(self) -> dict[str, Any]:
        resp = self._send_command("live_status")
        if resp.get("status") != "ok":
            raise TitanRuntimeError(resp.get("message", "Unknown error"))
        return cast(dict[str, Any], resp.get("data", {}))

    def _reconstruct_report(self, data: dict[str, Any]) -> RuntimeReport:
        from datetime import datetime

        from titan.brokers.models import ConnectionStatus
        from titan.runtime.models import (
            BrokerStatus,
            ComponentHealth,
            HealthStatus,
            JournalStatus,
            MarketStatus,
            PaperBrokerStatus,
            PerformanceStatus,
            PortfolioStatus,
            RecoveryStatus,
            ResourceStatus,
            RuntimeHealth,
            RuntimeStatus,
            SchedulerStatus,
        )

        def parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except Exception:  # noqa: BLE001
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
                    or datetime.now(),  # noqa: DTZ005
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
            stream_connected=data.get("market", {}).get("stream_connected", False),
            symbols=tuple(data.get("market", {}).get("symbols", [])),
        )

        perf = PerformanceStatus(
            uptime_seconds=data.get("performance", {}).get("uptime_seconds", 0.0)
        )

        runtime_status = str(data.get("runtime_status", "STOPPED"))
        try:
            rs = RuntimeStatus[runtime_status.upper()]
        except KeyError:
            try:
                rs = RuntimeStatus(int(runtime_status))
            except (TypeError, ValueError):
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
            timestamp=parse_dt(data.get("timestamp")) or datetime.now(),  # noqa: DTZ005
        )
