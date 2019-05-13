from zeropdk.layout.geometry import cross_prod, project

import klayout.db as kdb


def box(point1, point3, ex, ey):
    """ Returns a polygon of a box defined by point1, point3 and orientation ex.
    p2 ----- p3
    |        |
    p1 ----- p4
    ex --->

    """

    point2 = project(point3 - point1, ey, ex) * ey + point1
    point4 = point1 + point3 - point2

    return kdb.DSimplePolygon([point1, point2, point3, point4])


def rectangle(center, width, height, ex, ey):
    """
    returns the polygon of a rectangle centered at center,
    aligned with ex, with width and height in microns

    Args:
        center: pya.DPoint (um units)
        width (x axis): float (um units)
        height (y axis): float (um unit)
        ex: orientation of x axis
        ey: orientation of y axis
    """

    if cross_prod(ex, ey) == 0:
        raise RuntimeError('ex={} and ey={} are not orthogonal.'.format(repr(ex), repr(ey)))

    point1 = center - width / 2 * ex - height / 2 * ey
    point3 = center + width / 2 * ex + height / 2 * ey

    return box(point1, point3, ex=ex, ey=ey)


def square(center, width, ex, ey):
    """
    returns the polygon of a square centered at center,
    aligned with ex, with width in microns

    Args:
        center: pya.DPoint (um units)
        width: float (um units)
        ex: orientation
    """
    return rectangle(center, width, width, ex=ex, ey=ey)
