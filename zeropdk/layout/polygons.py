from zeropdk.layout.geometry import rotate90
from zeropdk.layout import insert_shape


def box(backend, point1, point3, ex):
    """ Returns a polygon of a box defined by point1, point3 and orientation ex.
    """
    # position point2 to the right of point1
    ey = rotate90(ex)
    point2 = point1 * ex * ex + point3 * ey * ey
    point4 = point3 * ex * ex + point1 * ey * ey

    return backend.SimplePolygon([point1, point2, point3, point4])


def rectangle(backend, center, width, height, ex):
    """
    returns the polygon of a rectangle centered at center,
    aligned with ex, with width and height in microns
    """

    ey = rotate90(ex)

    point1 = center - width / 2 * ex - height / 2 * ey
    point3 = center + width / 2 * ex + height / 2 * ey

    return box(backend, point1, point3, ex=ex)


def square(backend, center, width, ex):
    """
    returns the polygon of a square centered at center,
    aligned with ex, with width in microns
    """
    return rectangle(backend, center, width, width, ex=ex)


def layout_square(backend, cell, layer, center, width, ex):
    """ Lays out a square in a layer

    Args:
        center: pya.DPoint (um units)
        width: float (um units)
        ex: orientation

    """

    if ex is None:
        ex = backend.Point(1, 0)

    sq = square(backend, center, width, ex)
    insert_shape(cell, layer, sq)
    return sq
