import random
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout.polygons import rectangle
from zeropdk.layout import insert_shape

import klayout.db as kdb

lt = kdb


@pytest.fixture
def top_cell():
    def _top_cell(backend):
        layout = backend.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


def test_rectangle_write(top_cell):
    TOP, layout = top_cell(lt)
    layer = '1/0'
    center = lt.DPoint(0, 0)
    width = 20
    height = 10
    ex = lt.DVector(1, 1)
    ey = lt.DVector(0, 1)
    r = rectangle(lt, center, width, height, ex, ey)
    assert repr(r) == '(-10,-15;-10,-5;10,15;10,5)'

    insert_shape(TOP, layer, r)
    TOP.write('tests/tmp/test_rectangle.gds')
