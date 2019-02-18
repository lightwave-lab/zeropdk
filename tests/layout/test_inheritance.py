import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
import zeropdk.abstract.backend as ab


@pytest.mark.parametrize('lt', backends)
def test_abc(lt):
    issubclass(lt.Point, ab.Point)
    issubclass(lt.Vector, ab.Vector)
