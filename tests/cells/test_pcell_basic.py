import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends
from zeropdk.pcell import PCell, PCellParameter, TypeDouble, TypeInt

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
