import random
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout.polygons import rectangle, square
import klayout.db as kdb


def test_square():
    a, b = 0, 10
    ex = kdb.DVector(1, 0)
    ey = kdb.DVector(0, 1)
    size = random.uniform(a, b)
    origin = kdb.DPoint(0, 0)
    sq = square(origin, size, ex, ey)

    # This is true for any rectangle
    p1, p2, p3, p4 = sq.each_point()
    # assert p1 + p3 == p2 + p4  # adding points is unsupported.
    assert p2 - p1 == p3 - p4
    assert p3 - p2 == p4 - p1

    # True for squares only
    assert (p2 - p1).sq_length() == (p4 - p1).sq_length()

    # area computes normally
    assert sq.area() == pytest.approx(size**2)

    # origin is inside square
    assert sq.inside(origin)
