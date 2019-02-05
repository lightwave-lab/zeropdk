import random
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
from zeropdk.layout.polygons import layout_rectangle


@pytest.fixture
def top_cell():
    def _top_cell(backend):
        layout = backend.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


@pytest.mark.parametrize('lt', backends)
def test_rectangle_write(top_cell, lt):
    TOP, layout = top_cell(lt)
    layer = layout.layer('1/0')  # TODO fix
    center = lt.Point(0, 0)
    width = 20
    height = 10
    ex = lt.Vector(1, 1)
    ey = lt.Vector(0, 1)
    r = layout_rectangle(lt, TOP, layer, center, width, height, ex, ey)
    assert repr(r) == '(-10,-15;-10,-5;10,15;10,5)'
    TOP.write('test_rectangle.gds')
