import threading

from titan.paper.broker import PaperBroker
from titan.runtime.local_transport import LocalTransport, LocalTransportServer
from titan.runtime.runtime import RuntimeEngine
from titan.runtime.service import RuntimeService


def test_paper_runtime_lifecycle() -> None:
    engine = RuntimeEngine(broker=PaperBroker())
    service = RuntimeService(engine)
    server = LocalTransportServer(service, port=0)

    engine.start()
    server.start()
    worker = threading.Thread(target=engine.run_until_stopped)
    worker.start()

    try:
        transport = LocalTransport(port=server.port)
        assert transport.status().runtime_status.name == "RUNNING"
        assert transport.paper_status()["running"] is True
        transport.stop()
        worker.join(timeout=2.0)
        assert not worker.is_alive()
        assert not engine.is_running
    finally:
        if engine.is_running:
            engine.stop()
        worker.join(timeout=2.0)
        server.stop()
