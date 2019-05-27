import numpy as np
import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout.waveguides import waveguide_dpolygon
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


def test_waveguide(top_cell):
    t = np.linspace(-1, 1, 100)
    ex = kdb.DPoint(1, 0)
    ey = kdb.DPoint(0, 1)

    # list of points depicting a parabola
    points_list = 100 * t * ex + 100 * t ** 2 * ey
    dbu = 0.001
    width = 1

    wg = waveguide_dpolygon(points_list, width, dbu, smooth=True)

    # write to test_waveguide.gds (we should see a parabola)
    TOP, layout = top_cell()
    layer = "1/0"
    insert_shape(TOP, layer, wg)
    TOP.write("tests/tmp/test_waveguide.gds")
