import random
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends


def random_point(Point, a=-10, b=10):
    a = 0
    b = 10

    x = random.uniform(a, b)
    y = random.uniform(a, b)
    p = Point(x, y)
    return p


@pytest.mark.parametrize('lt', backends)
def test_add_sub(lt):
    p1 = random_point(lt.Point)
    p2 = random_point(lt.Point)

    sump = p1 + p2
    assert sump.x == p1.x + p2.x
    assert sump.y == p1.y + p2.y
    assert isinstance(sump, lt.Point)

    diffp = p2 - p1
    assert diffp.x == p2.x - p1.x
    assert diffp.y == p2.y - p1.y
    assert isinstance(diffp, lt.Vector)

    assert p1 == (sump - diffp) / 2
    assert p2 == (sump + diffp) / 2


@pytest.mark.parametrize('lt', backends)
def test_mul(lt):
    p_classes = (lt.Point, lt.Vector)

    for p_class in p_classes:
        p1 = random_point(lt.Vector)
        p2 = random_point(lt.Vector)

        assert p1 * p2 == p1.x * p2.x + p1.y * p2.y

        p3 = p1 * 2
        assert p3.x == p1.x * 2
        assert p3.y == p1.y * 2
