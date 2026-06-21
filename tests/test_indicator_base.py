import pytest

from titan.analysis.base import Indicator


def test_indicator_is_abstract():
    with pytest.raises(TypeError):
        Indicator()
