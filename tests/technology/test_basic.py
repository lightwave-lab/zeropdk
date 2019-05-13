from ..context import zeropdk  # noqa

import klayout.db as kdb

lt = kdb

from zeropdk.tech import Tech


class ExampleTech(Tech):
    def __init__(self, backend):
        super().__init__(backend)
        self.add_layer('layer_metal', '1/0')
        self.add_layer('layer_opening', '1/0')


def test_layers():
    t = ExampleTech(lt)
    assert t.layers['layer_metal'] == lt.LayerInfo(1, 0, 'layer_metal')
