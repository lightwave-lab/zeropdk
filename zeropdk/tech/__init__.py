class Tech:
    layers = None

    def __init__(self):
        if self.layers is None:
            self.layers = dict()

    def create_layer(self, layer_name, layer_def):
        self.layers[layer_name] = layer_def
