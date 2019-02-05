import random
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
from zeropdk.layout.polygons import square


@pytest.mark.parametrize('lt', backends)
def test_square(lt):
    a, b = 0, 10
    ex = lt.Vector(1, 0)
    size = random.uniform(a, b)
    origin = lt.Point(0, 0)
    sq = square(lt, origin, size, ex)

    # This is true for any rectangle
    p1, p2, p3, p4 = sq.each_point()
    assert p1 + p3 == p2 + p4
    assert p2 - p1 == p3 - p4
    assert p3 - p2 == p4 - p1

    # True for squares only
    assert (p2 - p1).norm() == (p4 - p1).norm()

    # area computes normally
    assert pytest.approx(sq.area(), size ** 2)

    # origin is inside square
    assert sq.inside(origin)
