from ..context import zeropdk  # noqa

from pathlib import Path
import os
from zeropdk.tech import Tech


def test_load_from_xml():
    filepath = Path(os.path.dirname(__file__)).resolve() / 'EBeam.lyp'
    ebeam = Tech.load_from_xml(filepath)
    assert ebeam.layers['M1'] == '41/0'
