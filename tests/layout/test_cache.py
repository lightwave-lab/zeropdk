from functools import partial
import pytest
from math import pi
import os
from shutil import rmtree
from zeropdk.layout.cache import cache_cell, produce_hash
from zeropdk.layout.geometry import rotate, rotate90
from zeropdk.pcell import PCell, ParamContainer, Port, TypeDouble, port_to_pin_helper
from zeropdk.klayout_helper.layout import layout_read_cell
import klayout.db as kdb

CACHE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tmp", "cache")

cache_cell = partial(
    cache_cell,
    cache_dir=CACHE_DIR,
)

def define_param(name, type, description, default=None, **kwargs):
    from zeropdk.pcell import PCellParameter

    return PCellParameter(
        name=name, type=type, description=description, default=default, **kwargs
    )

@cache_cell
class EmptyPCell(PCell): # type: ignore
    params = ParamContainer(
        define_param("angle_ex", TypeDouble, "x-axis angle (deg)", default=0),
    )

    def origin_ex_ey(self, multiple_of_90=False):  # pylint: disable=unused-argument
        EX = kdb.DVector(1, 0)
        cp = self.get_cell_params()
        origin = kdb.DPoint(0, 0)
        # if 'angle_ex' not in cp.__dict__:
        #     cp.angle_ex = 0
        if multiple_of_90:
            if cp.angle_ex % 90 != 0:
                raise RuntimeError("Specify an angle multiple of 90 degrees")
        ex = rotate(EX, cp.angle_ex * pi / 180)
        ey = rotate90(ex)
        return origin, ex, ey


    def draw(self, cell):
        layout = cell.layout()

        origin, ex, ey = self.origin_ex_ey()
        waveguide_width = 1
        layer = kdb.LayerInfo(1, 0)

        ports = [Port("opt1", origin, ex, waveguide_width)]
        port_to_pin_helper(ports, cell, layer)

        return cell, {port.name: port for port in ports}

@pytest.fixture
def top_cell():
    rmtree(CACHE_DIR, ignore_errors=True)
    def _top_cell():
        layout = kdb.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell

def test_new_pcell(top_cell):
    TOP, layout = top_cell()
    ex = kdb.DPoint(1, 0)
    pcell = EmptyPCell("single_port")
    pcell.place_cell(TOP, 0 * ex, "opt1")
    pcell.place_cell(TOP, 100 * ex)

    pcell2 = EmptyPCell("single_port2")
    pcell2.place_cell(TOP, 0 * ex, "opt1")

    TOP.write("tests/tmp/single_port.gds")

    # Inspect written file
    layout2 = kdb.Layout()
    layout2.dbu = 0.001

    TOP2: kdb.Cell = layout_read_cell(layout2, "TOP", "tests/tmp/single_port.gds")
    assert TOP2.name == "TOP"
    cell_list = [c.name for c in layout2.each_cell()]
    short_hash = produce_hash(pcell, extra=(layout.dbu, None))
    assert "TOP" in cell_list
    cell_list.remove("TOP")
    assert "single_port" in cell_list
    cell_list.remove("single_port")
    assert "single_port$1" in cell_list
    cell_list.remove("single_port$1")
    assert "single_port2" in cell_list
    cell_list.remove("single_port2")
    assert len(cell_list) == 2
    assert f"cache_EmptyPCell_{short_hash}" in cell_list
    assert cell_list[0].startswith("cache_EmptyPCell")
    assert cell_list[1].startswith("cache_EmptyPCell")

    # Creating cell in a new layout (force reading from cache)
    layout3 = kdb.Layout()
    layout3.dbu = 0.001

    TOP3 = layout3.create_cell("TOP3")
    pcell.place_cell(TOP3, 0 * ex)
    cell_list = [c.name for c in layout3.each_cell()]
    assert "TOP3" in cell_list
    cell_list.remove("TOP3")
    assert "single_port" in cell_list
    cell_list.remove("single_port")

    assert len(cell_list) == 1
    assert cell_list[0].startswith("cache_EmptyPCell")
    assert f"cache_EmptyPCell_{short_hash}" == cell_list[0]