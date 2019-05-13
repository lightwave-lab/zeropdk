import pytest
from ..context import zeropdk  # noqa

import klayout.db as kdb

from pathlib import Path
import os
from zeropdk.tech import Tech


lt = kdb


def test_load_from_xml():
    filepath = Path(os.path.dirname(__file__)).resolve() / 'EBeam.lyp'
    ebeam = Tech.load_from_xml(lt, filepath)
    assert ebeam.layers['M1'] == lt.LayerInfo(41, 0, 'M1')
