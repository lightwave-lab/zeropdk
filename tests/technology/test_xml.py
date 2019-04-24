import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends

from pathlib import Path
import os
from zeropdk.tech import Tech


@pytest.mark.parametrize('lt', backends)
def test_load_from_xml(lt):
    filepath = Path(os.path.dirname(__file__)).resolve() / 'EBeam.lyp'
    ebeam = Tech.load_from_xml(lt, filepath)
    assert ebeam.layers['M1'] == lt.LayerInfo(41, 0, 'M1')
