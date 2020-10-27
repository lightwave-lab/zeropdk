"""Extends kdb.Cell object by introducing or replacing with the following methods:
- Cell.insert_cell
- Cell.shapes
"""

from typing import Type
from functools import wraps
import klayout.db as kdb
from klayout.db import Cell, DPoint


def cell_insert_cell(
    cell: Type[Cell], other_cell: Type[Cell], origin: Type[DPoint], angle_deg: float
) -> Type[Cell]:
    mag = 1
    rot = angle_deg
    mirrx = False
    u = DPoint(origin)
    trans = kdb.DCplxTrans(mag, rot, mirrx, u)

    cell.insert(kdb.DCellInstArray(other_cell.cell_index(), trans))
    return cell


Cell.insert_cell = cell_insert_cell

def override_layer(method):
    old_method = method
    @wraps(old_method)
    def new_method(self: Type[Cell], layer, *args, **kwargs):
        if isinstance(layer, (kdb.LayerInfo, str)):
            layer_index = self.layout().layer(layer)
        else:
            layer_index = layer
        return old_method(self, layer_index, *args, **kwargs)
    return new_method

# All the methods that have layer_index as first argument
# I would like to allow LayerInfo to be passed as parameter
# Taken from https://www.klayout.de/doc-qt5/code/class_Cell.html
Cell.shapes = override_layer(Cell.shapes)
Cell.begin_shapes_rec = override_layer(Cell.begin_shapes_rec)
Cell.bbox_per_layer = override_layer(Cell.bbox_per_layer)
Cell.dbbox_per_layer = override_layer(Cell.dbbox_per_layer)
Cell.each_shape = override_layer(Cell.each_shape)
Cell.each_touching_shape = override_layer(Cell.each_touching_shape)
Cell.each_overlapping_shape = override_layer(Cell.each_overlapping_shape)
