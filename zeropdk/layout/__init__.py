def insert_shape(cell, layer, shape):
    if layer is not None:
        cell.shapes(layer).insert(shape)
