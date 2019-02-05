import pytest
import os
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
from zeropdk.pcell import PCell, PCellParameter, TypeDouble, TypeInt
from zeropdk.pcell import GDSCell

pad_size = PCellParameter(
    type=TypeDouble,
    description="Size of electrical pad.",
    default=100,
    unit='um'
)

pad_array_count = PCellParameter(
    type=TypeInt,
    description="Number of pads",
)


class Pad(PCell):
    params = {'pad_size': pad_size}


class PadArray(Pad):
    params = {'pad_array_count': pad_array_count}


@pytest.mark.parametrize('lt', backends)
def test_pcell_inheritance(lt):
    pad = Pad(name='testname', backend=lt)
    pad_array = PadArray(name='testname', backend=lt)
    assert 'pad_size' in pad_array.params
    assert 'pad_array_count' in pad_array.params

    assert pad_array.params['pad_size'] is pad.params['pad_size']


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


@pytest.mark.parametrize('lt', backends)
def test_gdscell(lt, top_cell):

    gds_dir = gdslibpath
    princeton_logo = GDSCell(lt, 'princeton_logo',
        'princeton_logo_simple.gds', gds_dir)(name='xyz', backend=lt)
    TOP, layout = top_cell(lt)
    ex = lt.Point(1, 0)
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


@pytest.mark.parametrize('lt', backends)
def test_gdscellcache(lt, top_cell):

    gds_dir = gdslibpath
    princeton_logo = GDSCell(lt, 'princeton_logo',
        'princeton_logo_simple.gds', gds_dir)(name='xyz', backend=lt)
    TOP, layout = top_cell(lt)
    ex = lt.Point(1, 0)

    for i in range(10):
        plogo = princeton_logo.new_cell(layout)
        size = (plogo.bbox().p2 - plogo.bbox().p1).norm()
        angle = 10 * i
        origin = ex * i * size
        TOP.insert_cell(plogo, origin, angle)

    # The top cell will contain several instances of different cells
    # 'plogo'. All 'plogos' will contain the same instance of the inner
    # gdscell loaded from a file.
    TOP.write('tests/tmp/princeton_logo_testcache.gds')

    cell_count = 0
    for cell in layout.each_cell():
        if cell.name.startswith('xyz'):
            cell_count += 1
    assert cell_count == 10

    cell_count = 0
    for cell in layout.each_cell():
        if cell.name.startswith('princeton_logo'):
            cell_count += 1
    assert cell_count == 1
