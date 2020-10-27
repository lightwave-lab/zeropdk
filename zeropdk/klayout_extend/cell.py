"""Extends kdb.Cell object by introducint or replacing with the following methods:
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

old_cell_shapes = Cell.shapes


@wraps(old_cell_shapes)
def cell_shapes(self, layer):
    if layer is not None and not isinstance(layer, int):
        layer = self.layout().layer(layer)
    return old_cell_shapes(self, layer)


Cell.shapes = cell_shapes
