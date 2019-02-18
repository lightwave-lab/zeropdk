import numpy as np
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
from zeropdk.layout.waveguides import waveguide_polygon
from zeropdk.layout import insert_shape


@pytest.fixture
def top_cell():
    def _top_cell(backend):
        layout = backend.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


@pytest.mark.parametrize('lt', backends)
def test_waveguide(lt, top_cell):
    t = np.linspace(-1, 1, 100)
    ex = lt.Point(1, 0)
    ey = lt.Point(0, 1)

    # list of points depicting a parabola
    points_list = 100 * t * ex + 100 * t ** 2 * ey
    dbu = 0.001
    width = 1

    wg = waveguide_polygon(lt, points_list, width, dbu, smooth=True)

    # write to test_waveguide.gds (we should see a parabola)
    TOP, layout = top_cell(lt)
    layer = '1/0'
    insert_shape(TOP, layer, wg)
    TOP.write('tests/tmp/test_waveguide.gds')
