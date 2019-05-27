from ..context import zeropdk  # noqa

import klayout.db as kdb

from zeropdk.tech import Tech


class ExampleTech(Tech):
    def __init__(self):
        super().__init__()
        self.add_layer("layer_metal", "1/0")
        self.add_layer("layer_opening", "1/0")


def test_layers():
    t = ExampleTech()
    assert t.layers["layer_metal"] == kdb.LayerInfo(1, 0, "layer_metal")
