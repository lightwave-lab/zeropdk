import pytest
from ..context import zeropdk  # noqa


from zeropdk.tech import Tech


class ExampleTech(Tech):
    def __init__(self):
        super().__init__()
        self.create_layer('layer_metal', '1/0')
        self.create_layer('layer_opening', '1/0')


def test_layers():
    t = ExampleTech()
    assert t.layers['layer_metal'] == '1/0'
