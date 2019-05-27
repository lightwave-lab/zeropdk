from ..context import zeropdk  # noqa

from pathlib import Path
import os
from zeropdk.tech import Tech

import klayout.db as kdb


def test_load_from_xml():
    filepath = Path(os.path.dirname(__file__)).resolve() / "EBeam.lyp"
    ebeam = Tech.load_from_xml(filepath)
    assert ebeam.layers["M1"] == kdb.LayerInfo(41, 0, "M1")
