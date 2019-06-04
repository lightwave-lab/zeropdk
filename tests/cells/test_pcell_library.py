import pytest
from ..context import zeropdk  # noqa
from zeropdk.default_library import io

import klayout.db as kdb

DCPad = io.DCPad


@pytest.fixture
def top_cell():
    def _top_cell():
        layout = kdb.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


def test_pad_pcell(top_cell):
    pad = DCPad(name="testname")
    pad.params.layer_metal = kdb.LayerInfo(1, 0)
    pad.params.layer_opening = kdb.LayerInfo(2, 0)

    # This will get automatically converted to LayerInfo
    # No Error
    pad.params.layer_metal = "1/0"

    # TODO set defaults here
    TOP, layout = top_cell()
    cell, ports = pad.new_cell(layout)
    assert "el0" in ports
    origin, angle = kdb.DPoint(0, 0), 0
    TOP.insert_cell(cell, origin, angle)
    TOP.write("tests/tmp/pad.gds")
