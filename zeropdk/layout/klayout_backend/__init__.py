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
Layout = pya.Layout
