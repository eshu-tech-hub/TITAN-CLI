from unittest.mock import MagicMock
from titan.runtime.runtime import RuntimeEngine
from titan.runtime.models import RuntimeStatus


def test_runtime_status_report():
    broker_mock = MagicMock()
    engine = RuntimeEngine(broker=broker_mock)
    report = engine.generate_report()
    assert report.runtime_status == RuntimeStatus.STOPPED
