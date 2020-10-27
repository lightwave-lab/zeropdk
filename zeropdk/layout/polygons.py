from zeropdk.layout import insert_shape
from zeropdk.layout.geometry import cross_prod, project, rotate90

import klayout.db as kdb


def box(point1, point3, ex, ey):
    """Returns a polygon of a box defined by point1, point3 and orientation ex.
    p2 ----- p3
    |        |
    p1 ----- p4
    ex --->

    """

    point2 = project(point3 - point1, ey, ex) * ey + point1
    point4 = point1 + point3 - point2
    return kdb.DSimplePolygon([point1, point2, point3, point4])


def layout_box(cell, layer, point1, point3, ex):
    """Lays out a box

    Args:
        point1: bottom-left point
        point3: top-right point

    """

    ey = rotate90(ex)
    polygon = box(point1, point3, ex, ey)
    insert_shape(cell, layer, polygon)
    return polygon


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
        raise RuntimeError("ex={} and ey={} are not orthogonal.".format(repr(ex), repr(ey)))

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


def layout_square(cell, layer, center, width, ex=None):
    """Lays out a square in a layer

    Args:
        center: pya.DPoint (um units)
        width: float (um units)
        ex: orientation

    """

    if ex is None:
        ex = pya.DPoint(1, 0)
    ey = rotate90(ex)

    shape = square(center, width, ex, ey)
    insert_shape(cell, layer, shape)
    return shape


def layout_rectangle(cell, layer, center, width, height, ex):
    """Lays out a rectangle

    Args:
        center: pya.DPoint (um units)
        width: float (um units)
        height: float (um unit)
        ex: orientation

    """

    ey = rotate90(ex)

    shape = rectangle(center, width, height, ex, ey)
    insert_shape(cell, layer, shape)
    return shape


# TODO: Reorganize later
pya = kdb
import numpy as np
from math import pi


def layout_path(cell, layer, point_iterator, w):
    """ Simple wrapper for pya.DPath."""
    path = pya.DPath(list(point_iterator), w, 0, 0).to_itype(cell.layout().dbu)
    cell.shapes(layer).insert(pya.Path.from_dpath(path))


def layout_path_with_ends(cell, layer, point_iterator, w):
    """ Simple wrapper for pya.DPath."""
    dpath = pya.DPath(list(point_iterator), w, w / 2, w / 2)
    cell.shapes(layer).insert(dpath)


def append_relative(points, *relative_vectors):
    """Appends to list of points in relative steps:
    It takes a list of points, and adds new points to it in relative coordinates.
    For example, if you call append_relative([A, B], C, D), the result will be [A, B, B+C, B+C+D].
    """
    try:
        if len(points) > 0:
            origin = points[-1]
    except TypeError:
        raise TypeError("First argument must be a list of points")

    for vector in relative_vectors:
        points.append(origin + vector)
        origin = points[-1]
    return points


from zeropdk.layout.algorithms import sample_function


def layout_ring(cell, layer, center, r, w):
    """
    function to produce the layout of a ring
    cell: layout cell to place the layout
    layer: which layer to use
    center: origin DPoint
    r: radius
    w: waveguide width
    units in microns

    """

    # outer arc
    # optimal sampling
    assert r - w / 2 > 0
    radius = r + w / 2
    arc_function = lambda t: np.array([radius * np.cos(t), radius * np.sin(t)])
    t, coords = sample_function(arc_function, [0, 2 * pi], tol=0.002 / radius)

    # create original waveguide poligon prior to clipping and rotation
    points_hull = [center + pya.DPoint(x, y) for x, y in zip(*coords)]
    del points_hull[-1]

    radius = r - w / 2
    arc_function = lambda t: np.array([radius * np.cos(t), radius * np.sin(t)])
    t, coords = sample_function(arc_function, [0, 2 * pi], tol=0.002 / radius)

    # create original waveguide poligon prior to clipping and rotation
    points_hole = [center + pya.DPoint(x, y) for x, y in zip(*coords)]
    del points_hole[-1]

    dpoly = pya.DPolygon(list(reversed(points_hull)))
    dpoly.insert_hole(points_hole)
    dpoly.compress(True)
    insert_shape(cell, layer, dpoly)
    return dpoly


def layout_circle(cell, layer, center, r):
    """
    function to produce the layout of a filled circle
    cell: layout cell to place the layout
    layer: which layer to use
    center: origin DPoint
    r: radius
    w: waveguide width
    theta_start, theta_end: angle in radians
    units in microns
    optimal sampling
    """

    arc_function = lambda t: np.array([center.x + r * np.cos(t), center.y + r * np.sin(t)])
    t, coords = sample_function(arc_function, [0, 2 * np.pi - 0.001], tol=0.002 / r)

    # dbu = cell.layout().dbu
    dpoly = pya.DSimplePolygon([pya.DPoint(x, y) for x, y in zip(*coords)])
    # cell.shapes(layer).insert(dpoly.to_itype(dbu))
    insert_shape(cell, layer, dpoly)
    return dpoly


layout_disk = layout_circle


def layout_donut(cell, layer, center, r1, r2):
    """Layout donut shape.
    cell: layout cell to place the layout
    layer: which layer to use
    center: origin DPoint (not affected by ex)
    r1: internal radius
    r2: external radius
    """

    assert r2 > r1

    arc_function = lambda t: np.array([center.x + r2 * np.cos(t), center.y + r2 * np.sin(t)])
    t, coords = sample_function(arc_function, [0, 2 * np.pi - 0.001], tol=0.002 / r2)

    external_points = [pya.DPoint(x, y) for x, y in zip(*coords)]

    arc_function = lambda t: np.array([center.x + r1 * np.cos(-t), center.y + r1 * np.sin(-t)])
    t, coords = sample_function(arc_function, [0, 2 * np.pi - 0.001], tol=0.002 / r1)

    internal_points = [pya.DPoint(x, y) for x, y in zip(*coords)]

    dpoly = pya.DPolygon(external_points)
    dpoly.insert_hole(internal_points)
    insert_shape(cell, layer, dpoly)
    return dpoly


def layout_section(
    cell,
    layer,
    center,
    r2,
    theta_start,
    theta_end,
    ex=None,
    x_bounds=(-np.inf, np.inf),
    y_bounds=(-np.inf, np.inf),
):
    """Layout section of a circle.
    cell: layout cell to place the layout
    layer: which layer to use
    center: origin DPoint (not affected by ex)
    r2: radius
    theta_start, theta_end: angle in radians
    x_bounds and y_bounds relative to the center, before rotation by ex.
    units in microns
    returns a dpolygon
    """

    assert r2 > 0

    # optimal sampling
    arc_function = lambda t: np.array([r2 * np.cos(t), r2 * np.sin(t)])
    t, coords = sample_function(arc_function, [theta_start, theta_end], tol=0.002 / r2)

    # # This yields a better polygon
    if theta_end < theta_start:
        theta_start, theta_end = theta_end, theta_start

    coords = np.insert(
        coords, 0, arc_function(theta_start - 0.001), axis=1
    )  # start the waveguide a little bit before
    coords = np.append(
        coords, np.atleast_2d(arc_function(theta_end + 0.001)).T, axis=1
    )  # finish the waveguide a little bit after

    # create original waveguide poligon prior to clipping and rotation
    dpoints_list = [pya.DPoint(x, y) for x, y in zip(*coords)]
    dpolygon = pya.DSimplePolygon(dpoints_list + [pya.DPoint(0, 0)])

    # clip dpolygon to bounds
    dpolygon.clip(x_bounds=x_bounds, y_bounds=y_bounds)
    # Transform points (translation + rotation)
    dpolygon.transform_and_rotate(center, ex)
    dpolygon.compress(True)
    dpolygon.layout(cell, layer)
    return dpolygon


def layout_arc(
    cell,
    layer,
    center,
    r,
    w,
    theta_start,
    theta_end,
    ex=None,
    x_bounds=(-np.inf, np.inf),
    y_bounds=(-np.inf, np.inf),
):
    """function to produce the layout of an arc
    cell: layout cell to place the layout
    layer: which layer to use
    center: origin DPoint (not affected by ex)
    r: radius
    w: waveguide width
    theta_start, theta_end: angle in radians
    x_bounds and y_bounds relative to the center, before rotation by ex.
    units in microns
    returns a dpolygon

    """
    # fetch the database parameters

    if r <= 0:
        raise RuntimeError(f"Please give me a positive radius. Bad r={r}")

    # optimal sampling
    if theta_end < theta_start:
        theta_start, theta_end = theta_end, theta_start

    arc_function = lambda t: np.array([r * np.cos(t), r * np.sin(t)])
    t, coords = sample_function(arc_function, [theta_start, theta_end], tol=0.002 / r)

    dt = 0.0001
    # # This yields a better polygon
    insert_at = np.argmax(theta_start + dt < t)
    t = np.insert(t, insert_at, theta_start + dt)
    coords = np.insert(
        coords, insert_at, arc_function(theta_start + dt), axis=1
    )  # start the second point a little bit after the first

    insert_at = np.argmax(theta_end - dt < t)
    t = np.insert(t, insert_at, theta_end - dt)
    coords = np.insert(
        coords, insert_at, arc_function(theta_end - dt), axis=1
    )  # start the second to last point a little bit before the final

    # create original waveguide poligon prior to clipping and rotation
    dpoints_list = [pya.DPoint(x, y) for x, y in zip(*coords)]
    from zeropdk.layout import waveguide_dpolygon

    dpolygon = waveguide_dpolygon(dpoints_list, w, cell.layout().dbu)

    # clip dpolygon to bounds
    dpolygon.clip(x_bounds=x_bounds, y_bounds=y_bounds)
    # Transform points (translation + rotation)
    dpolygon.transform_and_rotate(center, ex)
    dpolygon.compress(True)
    dpolygon.layout(cell, layer)
    return dpolygon


def layout_arc_degree(
    cell,
    layer,
    center,
    r,
    w,
    theta_start,
    theta_end,
    ex=None,
    x_bounds=(-np.inf, np.inf),
    y_bounds=(-np.inf, np.inf),
):
    """same as layout_arc, but with theta in degrees instead of radians"""

    theta_start *= np.pi / 180
    theta_end *= np.pi / 180
    return layout_arc(
        cell,
        layer,
        center,
        r,
        w,
        theta_start,
        theta_end,
        ex=ex,
        x_bounds=x_bounds,
        y_bounds=y_bounds,
    )


def layout_arc2(
    cell,
    layer,
    center,
    r1,
    r2,
    theta_start,
    theta_end,
    ex=None,
    x_bounds=(-np.inf, np.inf),
    y_bounds=(-np.inf, np.inf),
):
    """ modified layout_arc with r1 and r2, instead of r (radius) and w (width). """
    r1, r2 = min(r1, r2), max(r1, r2)

    r = (r1 + r2) / 2
    w = r2 - r1
    return layout_arc(
        cell,
        layer,
        center,
        r,
        w,
        theta_start,
        theta_end,
        ex=ex,
        x_bounds=x_bounds,
        y_bounds=y_bounds,
    )


def layout_arc_with_drc_exclude(
    cell, layer, drc_layer, center, r, w, theta_start, theta_end, ex=None, **kwargs
):
    """ Layout arc with drc exclude squares on sharp corners"""
    dpoly = layout_arc(cell, layer, center, r, w, theta_start, theta_end, ex, **kwargs)
    dpoly.layout_drc_exclude(cell, drc_layer, ex)
    return dpoly


def layout_arc2_with_drc_exclude(
    cell, layer, drc_layer, center, r1, r2, theta_start, theta_end, ex=None, **kwargs
):
    """ Layout arc2 with drc exclude squares on sharp corners"""
    dpoly = layout_arc2(cell, layer, center, r1, r2, theta_start, theta_end, ex, **kwargs)
    dpoly.layout_drc_exclude(cell, drc_layer, ex)
    return dpoly
