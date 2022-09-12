from numbers import Number
from typing import Union
import klayout.db as kdb
from zeropdk.types import GeneralLayer

def insert_shape(cell: kdb.Cell, layer: GeneralLayer, shape):
    if layer is None:
        return
    if isinstance(layer, (kdb.LayerInfo, str)):
        layer_index = cell.layout().layer(layer)
    elif isinstance(layer, Number):
        layer_index = layer
    cell.shapes(layer_index).insert(shape) # type: ignore

def layout_pgtext(cell: kdb.Cell, layer, x, y, text, mag, inv=False, angle=0):
    layout = kdb.Layout()
    lylayer = layout.layer(layer)
    for i, line in enumerate(text.splitlines()):
        pcell = layout.create_cell(
            "TEXT", "Basic", {"text": line, "layer": layer, "mag": mag, "inverse": inv}
        )
        pcell.transform_into(kdb.DCplxTrans(1, angle, False, x, y - i * mag * 5 / 4))
        lylayer_new = cell.layout().layer(layer)
        cell.shapes(lylayer_new).insert(pcell.shapes(lylayer))


from .polygons import *
from .waveguides import *
from .routing import *
