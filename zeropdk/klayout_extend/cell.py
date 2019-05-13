import klayout.db as kdb
from klayout.db import Cell, DPoint


def cell_insert_cell(cell: Cell, other_cell: Cell,
                     origin: DPoint, angle: float):
    mag = 1
    rot = angle
    mirrx = False
    u = DPoint(origin)
    trans = kdb.DCplxTrans(mag, rot, mirrx, u)

    cell.insert(
        kdb.DCellInstArray(other_cell.cell_index(),
                           trans))
    return cell


Cell.insert_cell = cell_insert_cell

Cell.bbox = Cell.dbbox

old_cell_shapes = Cell.shapes


def cell_shapes(self, layer):
    if not isinstance(layer, int):
        layer = self.layout().layer(layer)
    return old_cell_shapes(self, layer)


Cell.shapes = cell_shapes
