from copy import copy
import pickle
import random
import pytest

from zeropdk.klayout_helper.polygon import ZeroPDKDSimplePolygon
from ..context import zeropdk  # noqa
from zeropdk.layout.polygons import box, rectangle, square
import klayout.db as kdb
from math import inf


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
    assert moved_dpoly2.bbox().center() == origin + dv
    assert moved_dpoly == moved_dpoly2

    with pytest.raises(TypeError):
        dpoly.moved(1.5)
        dpoly.moved(dv, 1.5)
        dpoly.moved("test")


def test_transform_and_rotate():
    a, b = 1, 1
    ex = kdb.DVector(1, 0)
    ey = kdb.DVector(0, 1)
    origin = kdb.DPoint(0, 0)
    original_dpoly = box(origin, origin + a * ex + b * ey, ex, ey)
    dpoly = copy(original_dpoly)
    assert dpoly.area() == a * b
    dpoly.transform_and_rotate(ex)
    assert set(kdb.DPoint(x, y) for x, y in ((1, 0), (2, 0), (1, 1), (2, 1))) == set(
        dpoly.each_point()
    )
    dpoly = copy(original_dpoly)
    dpoly.transform_and_rotate(ex, ey)
    assert set(kdb.DPoint(x, y) for x, y in ((1, 0), (0, 0), (0, 1), (1, 1))) == set(
        dpoly.each_point()
    )
    dpoly = copy(original_dpoly)
    dpoly.transform_and_rotate(ex, ex, ex + ey)
    assert set(kdb.DPoint(x, y) for x, y in ((1, 0), (2, 1), (3, 1), (2, 0))) == set(
        dpoly.each_point()
    )


@pytest.fixture
def generate_unitbox():
    def _unitbox() -> ZeroPDKDSimplePolygon:
        ex = kdb.DVector(1, 0)
        ey = kdb.DVector(0, 1)
        origin = kdb.DPoint(0, 0)
        return box(origin, origin + ex + ey, ex, ey)

    return _unitbox


def test_bbox_inside_polygon(generate_unitbox):
    dpoly: ZeroPDKDSimplePolygon = generate_unitbox()
    a, b = 0.2, 0.8
    dpoly.clip(x_bounds=(a, b), y_bounds=(a, b))  # should be totally inside the polygon
    assert set(kdb.DPoint(x, y) for x, y in ((a, a), (a, b), (b, a), (b, b))) == set(
        dpoly.each_point()
    )


def test_clip_cut(generate_unitbox):
    dpoly: ZeroPDKDSimplePolygon = generate_unitbox()
    a, b = 0.2, 0.8
    # Dealing with infinite points in klayout!
    inf_point = kdb.DPoint(0.5, inf)
    assert not dpoly.inside(inf_point)
    inf_box = kdb.DBox(a, -inf, b, inf)
    inf_dpoly = ZeroPDKDSimplePolygon(inf_box)
    assert inf_dpoly.inside(inf_point)

    # Two cuts
    dpoly.clip(x_bounds=(a, b))
    assert set(kdb.DPoint(x, y) for x, y in ((a, 0), (a, 1), (b, 0), (b, 1))) == set(
        dpoly.each_point()
    )


def test_clip_single_cut(generate_unitbox):
    dpoly: ZeroPDKDSimplePolygon = generate_unitbox()
    # Divide rectangle in two
    a, b = 0.2, 1.5
    dpoly.clip(x_bounds=(a, b))
    assert set(kdb.DPoint(x, y) for x, y in ((a, 0), (a, 1), (1, 0), (1, 1))) == set(
        dpoly.each_point()
    )


def test_polygon_inside_bbox(generate_unitbox):
    dpoly: ZeroPDKDSimplePolygon = generate_unitbox()
    # Divide rectangle in two
    a, b = -1, 1.5
    dpoly.clip(x_bounds=(a, b))
    assert set(kdb.DPoint(x, y) for x, y in ((0, 0), (0, 1), (1, 0), (1, 1))) == set(
        dpoly.each_point()
    )


def test_non_overlapping(generate_unitbox):
    dpoly: ZeroPDKDSimplePolygon = generate_unitbox()
    # Divide rectangle in two
    a, b = 1.2, 1.5
    dpoly.clip(x_bounds=(a, b))
    assert dpoly.is_empty()


def test_overlapping(generate_unitbox):
    dpoly: ZeroPDKDSimplePolygon = generate_unitbox()
    dpoly.clip(x_bounds=(0.5, 1.5), y_bounds=(0.4, -1))
    assert set(kdb.DPoint(x, y) for x, y in ((0.5, 0.4), (1, 0.4), (1, 0), (0.5, 0))) == set(
        dpoly.each_point()
    )


def test_overlapping2():
    dpoly = ZeroPDKDSimplePolygon([kdb.DPoint(x, y) for x, y in ((0, 0), (0, 1), (1, 1))])
    dpoly.clip(x_bounds=(0.2, inf), y_bounds=(-inf, 0.8))
    assert set(kdb.DPoint(x, y) for x, y in ((0.2, 0.2), (0.2, 0.8), (0.8, 0.8))) == set(
        dpoly.each_point()
    )
