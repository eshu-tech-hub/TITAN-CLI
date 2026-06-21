import pytest

from titan.broker.base import Broker


def test_broker_is_abstract():
    with pytest.raises(TypeError):
        Broker()