from unittest.mock import MagicMock

from titan.runtime.models import RuntimeStatus
from titan.runtime.runtime import RuntimeEngine
from titan.runtime.service import RuntimeService


def test_runtime_service_wrapper():
    broker_mock = MagicMock()
    engine = RuntimeEngine(broker=broker_mock)
    service = RuntimeService(engine)
    assert service.status().runtime_status == RuntimeStatus.STOPPED
