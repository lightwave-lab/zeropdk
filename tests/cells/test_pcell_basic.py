import pytest
import os
from ..context import zeropdk  # noqa
from zeropdk.pcell import PCell, PCellParameter, ParamContainer, \
    TypeDouble, TypeInt
from zeropdk.pcell import GDSCell

import klayout.db as kdb

lt = kdb

pad_size = PCellParameter(
    name='pad_size',
    type=TypeDouble,
    description="Size of electrical pad.",
    default=100,
    unit='um'
)

pad_array_count = PCellParameter(
    name='pad_array_count',
    type=TypeInt,
    description="Number of pads",
)


class Pad(PCell):
    params = ParamContainer(pad_size)


class PadArray(Pad):
    params = ParamContainer(pad_array_count)


def test_pcell_inheritance():
    pad = Pad(name='testname', backend=lt)
    pad_array = PadArray(name='testname', backend=lt)
    assert 'pad_size' in pad_array.params
    assert 'pad_array_count' in pad_array.params

    assert pad_array.params['pad_size'] is pad.params['pad_size']
    assert pad_array.params['pad_size'] is pad_array.cp.pad_size


# Testing the most basic cells: GDSCell

gdslibpath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../gdslibrary'))


@pytest.fixture
def top_cell():
    def _top_cell(backend):
        layout = backend.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


def test_gdscell(top_cell):

    gds_dir = gdslibpath
    princeton_logo = GDSCell(lt, 'princeton_logo',
        'princeton_logo_simple.gds', gds_dir)(name='xyz', backend=lt)
    TOP, layout = top_cell(lt)
    ex = lt.DPoint(1, 0)
    plogo = princeton_logo.new_cell(layout)
    size = (plogo.bbox().p2 - plogo.bbox().p1).norm()
    for i in range(10):
        angle = 10 * i
        origin = ex * i * size
        TOP.insert_cell(plogo, origin, angle)

    # The top cell will contain several instances of the same cell
    # Deleting cell named 'priceton_logo' will delete all instances:
    # plogo.delete()
    TOP.write('tests/tmp/princeton_logo_test.gds')

    cell_count = 0
    for cell in layout.each_cell():
        if cell.name.startswith('xyz'):
            cell_count += 1
    assert cell_count == 1


def test_gdscellcache(top_cell):

    gds_dir = gdslibpath
    princeton_logo = GDSCell(lt, 'princeton_logo',
        'princeton_logo_simple.gds', gds_dir)(name='xyz', backend=lt)
    TOP, layout = top_cell(lt)
    ex = lt.DPoint(1, 0)

    for i in range(10):
        # The new_cell method does not create new cells,
        # it returns the same previously instantiated cell
        plogo = princeton_logo.new_cell(layout)
        size = (plogo.bbox().p2 - plogo.bbox().p1).norm()
        angle = 10 * i
        origin = ex * i * size
        TOP.insert_cell(plogo, origin, angle)

    # The top cell will contain several instances of different cells
    # 'plogo'. All 'plogos' will contain the same instance of the inner
    # gdscell loaded from a file.
    TOP.write('tests/tmp/princeton_logo_testcache.gds')

    # ony one cell "xyz" exists
    cell_count = 0
    for cell in layout.each_cell():
        if cell.name.startswith('xyz'):
            cell_count += 1
    assert cell_count == 1

    # 10 instances of cell "xyz" exists
    inst_count = 0
    for inst in TOP.each_inst():
        if inst.cell.name.startswith('xyz'):
            inst_count += 1
    assert inst_count == 10

    cell_count = 0
    for cell in layout.each_cell():
        if cell.name.startswith('princeton_logo'):
            cell_count += 1
    assert cell_count == 1
