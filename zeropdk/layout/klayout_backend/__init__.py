import klayout.db as pya
from . import extend  # noqa

# This is a temporary API implementation. Ideally, we will define
# all these classes in an abstract way and wrap klayout's classes
# with them.

# For example, if you do DPointA - DPointB, klayout returns a DVector.
# In the wrapped backend, we want PointA - PointB returning a Vector,
# not DVector, which is not trivial.
# Another example. A cell needs a layout. So in KLayout, cell.layout()
# returns a pya.Layout object.

Point = pya.DPoint
Vector = pya.DVector

Edge = pya.DEdge

Polygon = pya.DPolygon
SimplePolygon = pya.DSimplePolygon

Cell = pya.Cell


def cell_insert_cell(cell: Cell, other_cell: Cell,
                     origin: Point, angle: float):
    mag = 1
    rot = angle
    mirrx = False
    u = origin
    trans = pya.DCplxTrans(mag, rot, mirrx, u)

    cell.insert(
        pya.DCellInstArray(other_cell.cell_index(),
                           trans))
    return cell


Cell.insert_cell = cell_insert_cell


Cell.bbox = Cell.dbbox

# Layout API

Layout = pya.Layout


def layout_read_cell(layout, cell_name, filepath):
    # BUG loading this file twice segfaults klayout
    layout2 = Layout()
    layout2.read(filepath)
    gdscell2 = layout2.cell(cell_name)
    gdscell = layout.create_cell(cell_name)
    gdscell.copy_tree(gdscell2)
    del gdscell2
    del layout2
    return gdscell


Layout.read_cell = layout_read_cell
