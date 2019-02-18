import pytest
from ..context import zeropdk, pcell_library  # noqa
from zeropdk.layout import backends
from zeropdk.abstract.backend import Point

import pcell_library.io

DCPad = pcell_library.io.DCPad
DCPad.params.layer_metal = '1/0'
DCPad.params.layer_opening = '2/0'


@pytest.fixture
def top_cell():
    def _top_cell(backend):
        layout = backend.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


@pytest.mark.parametrize('lt', backends)
def test_pad_pcell(lt, top_cell):
    pad = DCPad(name='testname', backend=lt)
    # TODO set defaults here
    TOP, layout = top_cell(lt)
    cell = pad.new_cell(layout)
    origin, angle = Point(0, 0), 0
    TOP.insert_cell(cell, origin, angle)
    TOP.write('tests/tmp/pad.gds')
