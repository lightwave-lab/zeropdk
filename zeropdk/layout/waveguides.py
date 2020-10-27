""" Layout helper functions.

Author: Thomas Ferreira de Lima @thomaslima

The following functions are useful for scripted layout, or making
PDK Pcells.

TODO: enhance documentation
TODO: make some of the functions in util use these.
"""

from itertools import repeat
import numpy as np
from numpy import cos, sin, pi, sqrt
from functools import reduce
from zeropdk.layout.geometry import curve_length, cross_prod, find_arc

import klayout.db as pya

debug = False


def waveguide_dpolygon(points_list, width, dbu, smooth=True):
    """Returns a polygon outlining a waveguide.

    This was updated over many iterations of failure. It can be used for both
    smooth optical waveguides or DC metal traces with corners. It is better
    than klayout's Path because it can have varying width.

    Args:
        points_list: list of pya.DPoint (at least 2 points)
        width (microns): constant or list. If list, then it has to have the same length as points
        dbu: dbu: typically 0.001, only used for accuracy calculations.
        smooth: tries to smooth final polygons to avoid very sharp edges (greater than 130 deg)
    Returns:
        polygon DPoints

    """
    if len(points_list) < 2:
        raise NotImplementedError("ERROR: points_list too short")
        return

    def norm(self):
        return sqrt(self.x ** 2 + self.y ** 2)

    # Prepares a joint point and width iterators
    try:
        if len(width) == len(points_list):
            width_iterator = iter(width)
        elif len(width) == 2:
            # assume width[0] is initial width and
            # width[1] is final width
            # interpolate with points_list
            L = curve_length(points_list)
            distance = 0
            widths_list = [width[0]]
            widths_func = lambda t: (1 - t) * width[0] + t * width[1]
            old_point = points_list[0]
            for point in points_list[1:]:
                distance += norm(point - old_point)
                old_point = point
                widths_list.append(widths_func(distance / L))
            width_iterator = iter(widths_list)
        else:
            width_iterator = repeat(width[0])
    except TypeError:
        width_iterator = repeat(width)
    finally:
        points_iterator = iter(points_list)

    points_low = list()
    points_high = list()

    def cos_angle(point1, point2):
        cos_angle = point1 * point2 / norm(point1) / norm(point2)

        # ensure it's between -1 and 1 (nontrivial numerically)
        if abs(cos_angle) > 1:
            return cos_angle / abs(cos_angle)
        else:
            return cos_angle

    def sin_angle(point1, point2):
        return np.abs(cross_prod(point1, point2)) / norm(point1) / norm(point2)

    point_width_list = list(zip(points_iterator, width_iterator))
    N = len(point_width_list)

    first_point, first_width = point_width_list[0]
    next_point, next_width = point_width_list[1]

    delta = next_point - first_point
    theta = np.arctan2(delta.y, delta.x)
    first_high_point = first_point + 0.5 * first_width * pya.DPoint(
        cos(theta + pi / 2), sin(theta + pi / 2)
    )
    first_low_point = first_point + 0.5 * first_width * pya.DPoint(
        cos(theta - pi / 2), sin(theta - pi / 2)
    )
    points_high.append(first_high_point)
    points_low.append(first_low_point)

    for i in range(1, N - 1):
        prev_point, prev_width = point_width_list[i - 1]
        point, width = point_width_list[i]
        next_point, next_width = point_width_list[i + 1]
        delta_prev = point - prev_point
        delta_next = next_point - point

        # based on these points, there are two algorithms available:
        # 1. arc algorithm. it detects you are trying to draw an arc
        # so it will compute the center and radius of that arc and
        # layout accordingly.
        # 2. linear trace algorithm. it is not an arc, and you want
        # straight lines with sharp corners.

        # to detect an arc, the points need to go in the same direction
        # and the width has to be bigger than the smallest distance between
        # two points.

        is_arc = cos_angle(delta_next, delta_prev) > cos(30 * pi / 180)
        is_arc = is_arc and (min(delta_next.norm(), delta_prev.norm()) < width)
        center_arc, radius = find_arc(prev_point, point, next_point)
        if is_arc and radius < np.inf:  # algorithm 1
            ray = point - center_arc
            ray /= ray.norm()
            # if orientation is positive, the arc is going counterclockwise
            orientation = (cross_prod(ray, delta_prev) > 0) * 2 - 1
            points_low.append(point + orientation * width * ray / 2)
            points_high.append(point - orientation * width * ray / 2)
        else:  # algorithm 2
            theta_prev = np.arctan2(delta_prev.y, delta_prev.x)
            theta_next = np.arctan2(delta_next.y, delta_next.x)

            next_point_high = next_point + 0.5 * next_width * pya.DPoint(
                cos(theta_next + pi / 2), sin(theta_next + pi / 2)
            )
            next_point_low = next_point + 0.5 * next_width * pya.DPoint(
                cos(theta_next - pi / 2), sin(theta_next - pi / 2)
            )

            forward_point_high = point + 0.5 * width * pya.DPoint(
                cos(theta_next + pi / 2), sin(theta_next + pi / 2)
            )
            forward_point_low = point + 0.5 * width * pya.DPoint(
                cos(theta_next - pi / 2), sin(theta_next - pi / 2)
            )

            prev_point_high = prev_point + 0.5 * prev_width * pya.DPoint(
                cos(theta_prev + pi / 2), sin(theta_prev + pi / 2)
            )
            prev_point_low = prev_point + 0.5 * prev_width * pya.DPoint(
                cos(theta_prev - pi / 2), sin(theta_prev - pi / 2)
            )

            backward_point_high = point + 0.5 * width * pya.DPoint(
                cos(theta_prev + pi / 2), sin(theta_prev + pi / 2)
            )
            backward_point_low = point + 0.5 * width * pya.DPoint(
                cos(theta_prev - pi / 2), sin(theta_prev - pi / 2)
            )

            fix_angle = lambda theta: ((theta + pi) % (2 * pi)) - pi

            # High point decision
            next_high_edge = pya.DEdge(forward_point_high, next_point_high)
            prev_high_edge = pya.DEdge(backward_point_high, prev_point_high)

            if next_high_edge.crossed_by(prev_high_edge):
                intersect_point = next_high_edge.crossing_point(prev_high_edge)
                points_high.append(intersect_point)
            else:
                cos_dd = cos_angle(delta_next, delta_prev)
                if width * (1 - cos_dd) > dbu and fix_angle(theta_next - theta_prev) < 0:
                    points_high.append(backward_point_high)
                    points_high.append(forward_point_high)
                else:
                    points_high.append((backward_point_high + forward_point_high) * 0.5)

            # Low point decision
            next_low_edge = pya.DEdge(forward_point_low, next_point_low)
            prev_low_edge = pya.DEdge(backward_point_low, prev_point_low)

            if next_low_edge.crossed_by(prev_low_edge):
                intersect_point = next_low_edge.crossing_point(prev_low_edge)
                points_low.append(intersect_point)
            else:
                cos_dd = cos_angle(delta_next, delta_prev)
                if width * (1 - cos_dd) > dbu and fix_angle(theta_next - theta_prev) > 0:
                    points_low.append(backward_point_low)
                    points_low.append(forward_point_low)
                else:
                    points_low.append((backward_point_low + forward_point_low) * 0.5)

    last_point, last_width = point_width_list[-1]
    point, width = point_width_list[-2]
    delta = last_point - point
    theta = np.arctan2(delta.y, delta.x)
    final_high_point = last_point + 0.5 * last_width * pya.DPoint(
        cos(theta + pi / 2), sin(theta + pi / 2)
    )
    final_low_point = last_point + 0.5 * last_width * pya.DPoint(
        cos(theta - pi / 2), sin(theta - pi / 2)
    )
    if (final_high_point - points_high[-1]) * delta > 0:
        points_high.append(final_high_point)
    if (final_low_point - points_low[-1]) * delta > 0:
        points_low.append(final_low_point)

    # Append point only if the area of the triangle built with
    # neighboring edges is above a certain threshold.
    # In addition, if smooth is true:
    # Append point only if change in direction is less than 130 degrees.

    def smooth_append(point_list, point):
        if len(point_list) < 1:
            point_list.append(point)
            return point_list
        elif len(point_list) < 2:
            curr_edge = point - point_list[-1]
            if norm(curr_edge) > 0:
                point_list.append(point)
                return point_list

        curr_edge = point - point_list[-1]
        if norm(curr_edge) > 0:
            prev_edge = point_list[-1] - point_list[-2]

            # Only add new point if the area of the triangle built with
            # current edge and previous edge is greater than dbu^2/2
            if abs(cross_prod(prev_edge, curr_edge)) > dbu ** 2 / 2:
                if smooth:
                    # avoid corners when smoothing
                    if cos_angle(curr_edge, prev_edge) > cos(130 / 180 * pi):
                        point_list.append(point)
                    else:
                        # edge case when there is prev_edge is small and
                        # needs to be deleted to get rid of the corner
                        if norm(curr_edge) > norm(prev_edge):
                            point_list[-1] = point
                else:
                    point_list.append(point)
            # avoid unnecessary points
            else:
                point_list[-1] = point
        return point_list

    if debug and False:
        print("Points to be smoothed:")
        for point, width in point_width_list:
            print(point, width)

    smooth_points_high = list(reduce(smooth_append, points_high, list()))
    smooth_points_low = list(reduce(smooth_append, points_low, list()))
    # smooth_points_low = points_low
    # polygon_dpoints = points_high + list(reversed(points_low))
    # polygon_dpoints = list(reduce(smooth_append, polygon_dpoints, list()))
    polygon_dpoints = smooth_points_high + list(reversed(smooth_points_low))
    return pya.DSimplePolygon(polygon_dpoints)


def layout_waveguide(cell, layer, points_list, width, smooth=False):
    """Lays out a waveguide (or trace) with a certain width along given points.

    This is very useful for laying out Bezier curves with or without adiabatic tapers.

    Args:
        cell: cell to place into
        layer: layer to place into. It is done with cell.shapes(layer).insert(pya.Polygon)
        points_list: list of pya.DPoint (at least 2 points)
        width (microns): constant or list. If list, then it has to have the same length as points
        smooth: tries to smooth final polygons to avoid very sharp edges (greater than 130 deg)

    """

    dbu = cell.layout().dbu

    dpolygon = waveguide_dpolygon(points_list, width, dbu, smooth=smooth)
    dpolygon.compress(True)
    dpolygon.layout(cell, layer)
    return dpolygon


def layout_waveguide_angle(cell, layer, points_list, width, angle):
    """Lays out a waveguide (or trace) with a certain width along
    given points and with fixed orientation at all points.

    This is very useful for laying out Bezier curves with or without adiabatic tapers.

    Args:
        cell: cell to place into
        layer: layer to place into. It is done with cell.shapes(layer).insert(pya.Polygon)
        points_list: list of pya.DPoint (at least 2 points)
        width (microns): constant or list. If list, then it has to have the same length as points
        angle (degrees)
    """
    return layout_waveguide_angle2(cell, layer, points_list, width, angle, angle)


def layout_waveguide_angle2(cell, layer, points_list, width, angle_from, angle_to):
    """Lays out a waveguide (or trace) with a certain width along
    given points and with fixed orientation at all points.

    This is very useful for laying out Bezier curves with or without adiabatic tapers.

    Args:
        cell: cell to place into
        layer: layer to place into. It is done with cell.shapes(layer).insert(pya.Polygon)
        points_list: list of pya.DPoint (at least 2 points)
        width (microns): constant or list. If list, then it has to have the same length as points
        angle_from (degrees): normal angle of the first waveguide point
        angle_to (degrees): normal angle of the last waveguide point

    """
    if len(points_list) < 2:
        raise NotImplemented("ERROR: points_list too short")
        return

    def norm(self):
        return sqrt(self.x ** 2 + self.y ** 2)

    try:
        if len(width) == len(points_list):
            width_iterator = iter(width)
        elif len(width) == 2:
            # assume width[0] is initial width and
            # width[1] is final width
            # interpolate with points_list
            L = curve_length(points_list)
            distance = 0
            widths_list = [width[0]]
            widths_func = lambda t: (1 - t) * width[0] + t * width[1]
            old_point = points_list[0]
            for point in points_list[1:]:
                distance += norm(point - old_point)
                old_point = point
                widths_list.append(widths_func(distance / L))
            width_iterator = iter(widths_list)
        else:
            width_iterator = repeat(width[0])
    except TypeError:
        width_iterator = repeat(width)
    finally:
        points_iterator = iter(points_list)

    points_low = list()
    points_high = list()

    point_width_list = list(zip(points_iterator, width_iterator))
    N = len(point_width_list)

    angle_list = list(np.linspace(angle_from, angle_to, N))

    for i in range(0, N):
        point, width = point_width_list[i]
        angle = angle_list[i]
        theta = angle * pi / 180

        point_high = point + 0.5 * width * pya.DPoint(cos(theta + pi / 2), sin(theta + pi / 2))
        points_high.append(point_high)
        point_low = point + 0.5 * width * pya.DPoint(cos(theta - pi / 2), sin(theta - pi / 2))
        points_low.append(point_low)

    polygon_points = points_high + list(reversed(points_low))

    poly = pya.DSimplePolygon(polygon_points)
    cell.shapes(layer).insert(poly)
    return poly
