import random
import numpy as np
from ..context import zeropdk  # noqa

import klayout.db as kdb


def random_point(Point, a=-10, b=10):
    a = 0
    b = 10

    x = random.uniform(a, b)
    y = random.uniform(a, b)
    p = Point(x, y)
    return p


def test_add_sub():
    p1 = random_point(kdb.Point)
    p2 = random_point(kdb.Point)

    sump = p1 + p2
    assert sump.x == p1.x + p2.x
    assert sump.y == p1.y + p2.y
    assert isinstance(sump, kdb.Point)

    diffp = p2 - p1
    assert diffp.x == p2.x - p1.x
    assert diffp.y == p2.y - p1.y
    assert isinstance(diffp, kdb.Vector)

    assert p1 == (sump - diffp) / 2
    assert p2 == (sump + diffp) / 2


def test_mul():
    p_classes = (kdb.Point, kdb.Vector)

    for p_class in p_classes:
        p1 = random_point(kdb.Vector)
        p2 = random_point(kdb.Vector)

        assert p1 * p2 == p1.x * p2.x + p1.y * p2.y

        p3 = p1 * 2
        assert p3.x == p1.x * 2
        assert p3.y == p1.y * 2


def test_numpy():
    t = np.arange(3)
    ex = kdb.Point(1, 0)

    # Point should consume a numpy array and produce a np.array of points
    point_array = t * ex
    assert isinstance(point_array, np.ndarray)
    assert np.all([0 * ex, 1 * ex, 2 * ex] == point_array)

def test_float_operations():
    assert kdb.DPoint(1, 2) / 1.0 == kdb.DPoint(1, 2)
    assert 0.5 * kdb.DPoint(1, 2) == kdb.DPoint(0.5, 1)
