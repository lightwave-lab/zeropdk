import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
import zeropdk.abstract.backend as ab


@pytest.mark.parametrize('lt', backends)
def test_abc(lt):
    assert issubclass(lt.Point, ab.Point)
    assert issubclass(lt.Vector, ab.Vector)

    a = lt.Point(0, 0)
    assert a == lt.Point(a)
