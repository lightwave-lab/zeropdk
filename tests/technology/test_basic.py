import pytest
from ..context import zeropdk  # noqa
from zeropdk.layout import backends


from zeropdk.tech import Tech


class ExampleTech(Tech):
    def __init__(self, backend):
        super().__init__(backend)
        self.add_layer('layer_metal', '1/0')
        self.add_layer('layer_opening', '1/0')


@pytest.mark.parametrize('lt', backends)
def test_layers(lt):
    t = ExampleTech(lt)
    assert t.layers['layer_metal'] == lt.LayerInfo(1, 0, 'layer_metal')
