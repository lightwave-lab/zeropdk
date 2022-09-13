import random
import pytest

from zeropdk.klayout_helper.polygon import ZeroPDKDSimplePolygon
from ..context import zeropdk  # noqa
from zeropdk.layout.polygons import rectangle, square
import klayout.db as kdb


def test_simple_polygon_resize():
    a, b = 10, 20
    ex = kdb.DVector(1, 0)
    ey = kdb.DVector(0, 1)
    origin = kdb.DPoint(0, 0)
    dpoly = rectangle(origin, a, b, ex, ey)
    assert dpoly.area() == a * b
    dx = 1
    dpoly.resize(dx, 0.001)
    assert dpoly.area() == (a + 2 * dx) * (b + 2 * dx)


def test_simple_polygon_moved():
    a, b = 10, 20
    ex = kdb.DVector(1, 0)
    ey = kdb.DVector(0, 1)
    dv = 4 * ex + 8 * ey
    origin = kdb.DPoint(0, 0)
    dpoly = rectangle(origin, a, b, ex, ey)
    assert dpoly.bbox().center() == origin
    moved_dpoly = dpoly.moved(dv)
    assert isinstance(moved_dpoly, ZeroPDKDSimplePolygon)
    assert moved_dpoly.bbox().center() == origin + dv
    moved_dpoly2 = dpoly.moved(dv.x, dv.y)
    assert moved_dpoly == moved_dpoly2
