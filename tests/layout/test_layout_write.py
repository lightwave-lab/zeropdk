from typing import Callable, Tuple
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout.polygons import rectangle
from zeropdk.layout import insert_shape

import klayout.db as kdb


@pytest.fixture
def top_cell():
    def _top_cell():
        layout = kdb.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


def test_rectangle_write(top_cell: Callable[[], Tuple[kdb.Cell, kdb.Layout]]):
    TOP, layout = top_cell()
    layer = "1/0"
    center = kdb.DPoint(0, 0)
    width = 20
    height = 10
    ex = kdb.DVector(1, 1)
    ey = kdb.DVector(0, 1)
    r = rectangle(center, width, height, ex, ey)
    assert str(r) == "(-10,-15;-10,-5;10,15;10,5)"
    insert_shape(TOP, layer, r)
    assert str(list(TOP.shapes(0).each())[0]) == "simple_polygon (-10000,-15000;-10000,-5000;10000,15000;10000,5000)"
    TOP.write("tests/tmp/test_rectangle.gds")
