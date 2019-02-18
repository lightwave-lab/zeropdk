import pytest
from ..context import zeropdk
from zeropdk.pcell import ParamContainer, PCellParameter
from zeropdk.layout import Point


def test_basic_usage():
    pc = ParamContainer()

    pc.add_param(PCellParameter(name='orange', default=1))
    assert pc.orange == 1

    pc.orange = 2
    assert pc.orange == 2
    pc['orange'] == 2  # it is also accessible as a dictionary

    with pytest.raises(TypeError, match="Cannot set 'orange' to 'blah'"):
        pc.orange = 'blah'

    pc.add_param(PCellParameter(name='apple'))
    pc.apple = 1  # WARNING  'apple' type is unknown. Setting to 'int'

    with pytest.raises(TypeError, match="Cannot set 'apple' to 'one'"):
        pc.apple = 'one'

    pc.add_param(PCellParameter(name='strawberry', default=Point(0, 0)))
    assert type(pc.strawberry) == Point

    with pytest.raises(TypeError, match="Cannot set 'strawberry' to 'test'"):
        pc.strawberry = 'test'


def test_quirky_cases():
    pc = ParamContainer()

    pc.add_param(PCellParameter(name='orange', default=1))

    # Don't try to set any value here
    with pytest.raises(TypeError, match="'ParamContainer' object does not support item assignment"):
        pc['orange'] = 2