from zeropdk.layout.geometry import rotate90, cross_prod, project
from zeropdk.layout import insert_shape


def box(backend, point1, point3, ex, ey=None):
    """ Returns a polygon of a box defined by point1, point3 and orientation ex.
    """
    # p2 ----- p3
    # |        |
    # p1 ----- p4
    # ex --->

    if ey is None:
        ey = rotate90(ex)

    point2 = project(point3 - point1, ey, ex) * ey + point1
    point4 = point1 + point3 - point2

    return backend.SimplePolygon([point1, point2, point3, point4])


def rectangle(backend, center, width, height, ex, ey=None):
    """
    returns the polygon of a rectangle centered at center,
    aligned with ex, with width and height in microns
    """

    if ey is None:
        ey = rotate90(ex)

    assert cross_prod(ex, ey) != 0

    point1 = center - width / 2 * ex - height / 2 * ey
    point3 = center + width / 2 * ex + height / 2 * ey

    return box(backend, point1, point3, ex=ex, ey=ey)


def layout_rectangle(backend, cell, layer, center, width, height, ex, ey=None):
    """ Lays out a rectangle

    Args:
        center: pya.DPoint (um units)
        width: float (um units)
        height: float (um unit)
        ex: orientation

    """

    rect = rectangle(backend, center, width, height, ex=ex, ey=ey)
    insert_shape(cell, layer, rect)
    return rect


def square(backend, center, width, ex, ey=None):
    """
    returns the polygon of a square centered at center,
    aligned with ex, with width in microns
    """
    return rectangle(backend, center, width, width, ex=ex, ey=ey)


def layout_square(backend, cell, layer, center, width, ex, ey=None):
    """ Lays out a square in a layer

    Args:
        center: pya.DPoint (um units)
        width: float (um units)
        ex: orientation

    """

    sq = square(backend, center, width, ex, ey=ey)
    insert_shape(cell, layer, sq)
    return sq
