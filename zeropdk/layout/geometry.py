import logging
import os
from functools import lru_cache, partial
from typing import Tuple
import numpy as np
from scipy.interpolate import interp2d
from zeropdk.layout.algorithms.sampling import sample_function

logger = logging.getLogger(__name__)


def rotate(point, angle_rad: float):
    """ Rotates point counter-clockwisely about its origin by an angle given in radians"""
    th = angle_rad
    x, y = point.x, point.y
    new_x = x * np.cos(th) - y * np.sin(th)
    new_y = y * np.cos(th) + x * np.sin(th)
    return point.__class__(new_x, new_y)


rotate90 = lambda point: rotate(point, np.pi / 2)


def cross_prod(p1, p2):
    return p1.x * p2.y - p1.y * p2.x


def find_arc(A, B, C):
    """Finds the arc of a circle containing points A, B, C.
    Returns the center of the circle, and the radius:
        (O[Point], R)
    If A,B,C falls on a line, the center is None and the radius is infinite.
    """

    # check if it is not a valid triangle
    AB = B - A
    BC = C - B
    area = cross_prod(AB, BC)

    if np.isclose(area, 0):
        return None, np.inf

    ex = AB / AB.norm()
    ey = rotate90(ex)

    D = (A + B) / 2
    E = (B + C) / 2

    LHS_sys = np.array([[BC * ex, BC * ey], [AB * ex, AB * ey]])
    RHS_sys = np.array([[E * BC], [D * AB]])

    sol = np.linalg.inv(LHS_sys).dot(RHS_sys)
    h, k = sol.flatten()

    O = h * ex + k * ey
    R = (A - O).norm()
    return O, R


def project(v, ex, ey=None):
    """ Compute a such that v = a * ex + b * ey """
    if ey is None:
        ey = rotate90(ex)

    if cross_prod(ex, ey) == 0:
        raise RuntimeError("ex={} and ey={} are not orthogonal.".format(repr(ex), repr(ey)))

    # Simple formula
    # https://math.stackexchange.com/questions/148199/equation-for-non-orthogonal-projection-of-a-point-onto-two-vectors-representing

    a = cross_prod(ey, v) / cross_prod(ey, ex)
    # b = cross_prod(ex, v) / cross_prod(ex, ey)

    # v == a * ex + b * ey
    return a


def curve_length(curve, t0=0, t1=1):
    """Computes the total length of a curve.

    Args:
        curve: list of Points, or
            parametric function of points, to be computed from t0 to t1.
    """
    # TODO possible bug: if the curve is a loop, it will return 0 (BAD)
    if isinstance(curve, list):
        # assuming curve is a list of points
        scale = (curve[-1] - curve[0]).norm()
        if scale > 0:
            coords = np.array([[point.x, point.y] for point in curve]).T
            dp = np.diff(coords, axis=-1)
            ds = np.sqrt((dp ** 2).sum(axis=0))
            return ds.sum()
        else:
            return 0
    else:
        # assuming curve is a function.
        curve_func = curve
        scale = (curve_func(t1) - curve_func(t0)).norm()
        if scale > 0:
            coords = lambda t: np.array([curve_func(t).x, curve_func(t).y])
            _, sampled_coords = sample_function(
                coords, [t0, t1], tol=0.0001 / scale, min_points=100
            )  # 1000 times more precise than the scale
            dp = np.diff(sampled_coords, axis=-1)
            ds = np.sqrt((dp ** 2).sum(axis=0))
            return ds.sum()
        else:
            return 0


def manhattan_intersection(vertical_point, horizontal_point, ex):
    """returns the point that intersects vertical_point's x coordinate
    and horizontal_point's y coordinate.

    Args: ex (Vector/Point): orientation of x axis.

    Caveat: this formula only works for orthogonal coordinate systems.
    """
    ey = rotate90(ex)
    return vertical_point * ex * ex + horizontal_point * ey * ey


def find_Z_orientation(P0, P1, ex):
    """Compute the orientation of Point P0 against Point P1
    P1 is assumed to be above P0.

    Args: ex (Vector/Point): orientation of x axis.

    Returns:
        0 for Z-oriented and 1 for S-oriented

    """
    if P1 * ex > P0 * ex:
        orient = 0  # Z-oriented
    else:
        orient = 1  # S-oriented
    return orient


def cluster_ports(ports_from, ports_to, ex):
    """Given two (equal length) port arrays, divide them into clusters
    based on the connection orientation. The idea is that each cluster
    can be routed independently with an array of Z or S traces that don't
    touch each other.

    Args:
        - ex (Vector/Point): orientation of the axis along with the
    ports are placed.

    TODO document more.

    Returns:
        an array of k 2-tuples (port_pair_list, orientation),
            where k is the number of clusters,
            port_pair list an array of (p0, p1),
            and orientation is 0 for Z and 1 for S
    """
    assert len(ports_from) == len(ports_to), "Port array must have the same length"
    if len(ports_from) == 0:
        return []

    orient_old = None
    port_cluster = []
    port_clusters = []
    # sort the arrays first
    proj_ex = lambda p: p.position * ex
    ports_from = sorted(ports_from, key=proj_ex)
    ports_to = sorted(ports_to, key=proj_ex)
    for port_from, port_to in zip(ports_from, ports_to):
        new_cluster = False
        orient_new = find_Z_orientation(port_from.position, port_to.position, ex)
        # first pair
        if orient_old is None:
            port_cluster.append((port_from, port_to))
        # the rest of the pairs
        elif orient_new == orient_old:
            # if the ports are too spaced apart, initiate new cluster
            right_port = min(port_from, port_to, key=proj_ex)
            left_port = max(port_cluster[-1], key=proj_ex)
            if proj_ex(right_port) - right_port.width > proj_ex(left_port) + left_port.width:
                new_cluster = True
            else:
                port_cluster.append((port_from, port_to))
        else:
            new_cluster = True

        if new_cluster:
            port_clusters.append((port_cluster, orient_old))
            port_cluster = []
            port_cluster.append((port_from, port_to))
        orient_old = orient_new
    port_clusters.append((port_cluster, orient_old))
    return port_clusters


def bezier_line(P0, P1, P2, P3):
    """Cubic Bézier formula

    Returns:
        Function of parameter t (1d array)

    Reference
        https://en.wikipedia.org/wiki/Bézier_curve"""

    curve_func = (
        lambda t: (1 - t) ** 3 * P0
        + 3 * (1 - t) ** 2 * t * P1
        + 3 * (1 - t) * t ** 2 * P2
        + t ** 3 * P3
    )
    return curve_func


def curvature_bezier(P0, P1, P2, P3):
    """Measures the curvature of the Bézier curve at every point t

    Returns:
        Function of parameter t (1d array)

    References:
        https://en.wikipedia.org/wiki/Radius_of_curvature
        https://en.wikipedia.org/wiki/Bézier_curve
    """
    b_prime = (
        lambda t: 3 * (1 - t) ** 2 * (P1 - P0)
        + 6 * (1 - t) * t * (P2 - P1)
        + 3 * t ** 2 * (P3 - P2)
    )
    b_second = lambda t: 6 * (1 - t) * (P2 - 2 * P1 + P0) + 6 * t * (P3 - 2 * P2 + P1)
    dx = lambda t: b_prime(t).x
    dy = lambda t: b_prime(t).y
    ddx = lambda t: b_second(t).x
    ddy = lambda t: b_second(t).y
    curv_func = lambda t: (dx(t) * ddy(t) - dy(t) * ddx(t)) / (dx(t) ** 2 + dy(t) ** 2) ** (3 / 2)
    return curv_func


from scipy.optimize import minimize


def max_curvature(P0, P1, P2, P3):
    """Gets the maximum curvature of Bezier curve"""
    t = np.linspace(0, 1, 300)
    curv = curvature_bezier(P0, P1, P2, P3)(t)
    max_curv = np.max(np.abs(curv.flatten()))
    return max_curv


def _curvature_penalty(P0, P1, P2, P3):
    """Penalty on the curvyness of Bezier curve"""
    t = np.linspace(0, 1, 300)

    curv = np.abs(curvature_bezier(P0, P1, P2, P3)(t).flatten())
    max_curv = np.max(curv)
    curv_initial = curv[0]
    curv_final = curv[-1]

    # this will cause the minimum curvature to be about 4 times lower
    # than at the origin and end points.
    penalty = max_curv + 2 * (curv_initial + curv_final)
    return penalty


def fix_angle(angle):
    """Returns the angle in the -pi to pi range"""
    return (angle + np.pi) % (2 * np.pi) - np.pi


def logistic_penalty(x, a):
    return 1 / (1 + np.exp(-x / a))


# #### The following classes (Point and Line) exist only to speed up
#      the code in bezier_optimal. klayout objects have a slower
#      interface


MAGIC_NUMBER = 15.0
from numpy import sqrt


class _Point(object):
    """ Defines a point with two coordinates. Mimics pya.Point"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        return self.__class__(x, y)

    def __sub__(self, other):
        x = self.x - other.x
        y = self.y - other.y
        return self.__class__(x, y)

    __array_priority__ = MAGIC_NUMBER  #: This allows rmul to be called first. See https://stackoverflow.com/questions/38229953/array-and-rmul-operator-in-python-numpy"""

    def __mul__(self, factor):
        """ This implements P * factor"""
        if isinstance(factor, np.ndarray):
            # Return a Line instead
            return _Line(self.x * factor, self.y * factor)
        elif isinstance(factor, _Point):
            return self.x * factor.x + self.y * factor.y
        return self.__class__(self.x * factor, self.y * factor)

    def __rmul__(self, factor):
        """ This implements factor * P """
        if isinstance(factor, np.ndarray):
            return self.__mul__(factor)
        return self.__class__(self.x * factor, self.y * factor)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __str__(self):
        return "Point({}, {})".format(self.x, self.y)

    def norm(self):
        return sqrt(self.x ** 2 + self.y ** 2)


class _Line(_Point):
    """ Defines a line """

    def __init__(self, x, y):
        self.x, self.y = np.asarray(x), np.asarray(y)
        assert np.shape(self.x) == np.shape(self.y)

    def __eq__(self, other):
        return np.all(self.x == other.x) and np.all(self.y == other.y)


@lru_cache(maxsize=128)
def _bezier_optimal(angle0: float, angle3: float) -> Tuple[float, float]:
    """This is a reduced problem of the bézier connection.

    Args:
        angle0: starting angle in radians
        angle3: ending angle in radians

    This assumes P0 = (0,0), P3 = (1,0).
    """

    angle0 = fix_angle(angle0)
    angle3 = fix_angle(angle3)

    # print(f"Solving for angles: {angle0}, {angle3}", end='...\t\t')

    def J(a, b, a_max, b_max, cross=False):
        """ Energy function for bezier optimization """
        P0 = _Point(0, 0)
        P3 = _Point(1, 0)
        P1 = P0 + a * _Point(np.cos(angle0), np.sin(angle0))
        P2 = P3 - b * _Point(np.cos(angle3), np.sin(angle3))

        main_penalty = _curvature_penalty(P0, P1, P2, P3)

        # Constraint penalty
        constraint_penalty = np.exp(-a / 0.05)
        constraint_penalty += np.exp(-b / 0.05)

        # Only for potentially crossing P0-P1, P1-P2 segments (prevents loops)
        if cross:
            constraint_penalty -= np.log(np.maximum(1e-3, np.minimum(a_max - a, b_max - b)))
        else:
            constraint_penalty += np.exp((a - a_max) / 0.05)
            constraint_penalty += np.exp((b - b_max) / 0.05)

        # print(f"{a:.2f}, {b:.2f}: {main_penalty}/{constraint_penalty}")
        return main_penalty + constraint_penalty

    MAX = 1.5

    # If these angles have opposite signs, then calculate the bounds
    # so that P1 and P2 do not *both* hit the intersection of the
    # initial tangents. This prevents loops.
    if angle0 * angle3 < 0 and np.abs(angle3 - angle0) < np.pi:  # potential cross
        # Initialize problem
        a = b = 0.05

        third_angle = np.pi - np.abs(angle3) - np.abs(angle0)
        a_bound = min(2 * np.abs(np.sin(angle3)) / np.sin(third_angle), MAX * 3)
        b_bound = min(2 * np.abs(np.sin(angle0)) / np.sin(third_angle), MAX * 3)

        initial_simplex = np.array([[a, b], [a * 1.1, b], [a, b * 1.1]])

        result = minimize(
            # lambda x: J(x[0], x[1], MAX * 3, MAX * 3),
            lambda x: J(x[0], x[1], a_bound, b_bound, cross=True),
            np.array([a, b]),
            method="Nelder-Mead",
            options=dict(initial_simplex=initial_simplex),
        )
    else:  # no potential cross
        # Initialize problem
        a = b = 0.3
        initial_simplex = np.array([[a, b], [a * 1.1, b], [a, b * 1.1]])
        a_bound = b_bound = MAX

        result = minimize(
            lambda x: J(x[0], x[1], a_bound, b_bound, cross=False),
            np.array([a, b]),
            method="Nelder-Mead",
            options=dict(initial_simplex=initial_simplex),
        )

    if result.success:
        a, b = result.x[0], result.x[1]
    else:
        if result.message == "Maximum number of function evaluations has been exceeded.":
            a, b = result.x[0], result.x[1]
        else:
            print(f"Could not optimize. Exited with message:{result.message}")
    # print("a={:.3f}<{:.3f} b={:.3f}<{:.3f}".format(a, a_bound, b, b_bound))
    return a, b


# STABLE MEMOIZATION

pwd = os.path.dirname(os.path.realpath(__file__))
bezier_optimal_fpath = os.path.join(pwd, "bezier_optimal.npz")
_original_bezier_optimal = _bezier_optimal


def memoized_bezier_optimal(angle0: float, angle3: float, file: str) -> Tuple[float, float]:
    try:
        npzfile = np.load(file)
        x = npzfile["x"]
        y = npzfile["y"]
        z_a = npzfile["z_a"]
        z_b = npzfile["z_b"]

        a = interp2d(x, y, z_a)(angle0, angle3)[0]
        b = interp2d(x, y, z_b)(angle0, angle3)[0]
        return a, b
    except:
        logger.error(f"Optimal Bezier interpolation has failed for angles({angle0}, {angle3}).")
        return _original_bezier_optimal(angle0, angle3)


if os.path.isfile(bezier_optimal_fpath):
    _bezier_optimal = partial(memoized_bezier_optimal, file=bezier_optimal_fpath)


def bezier_optimal(P0, P3, angle0: float, angle3: float):
    """Computes the optimal bezier curve from P0 to P3 with angles 0 and 3

    Args:
        P0, P3: Point
        Angles in degrees
    """

    angle0 = angle0 * np.pi / 180
    angle3 = angle3 * np.pi / 180

    vector = P3 - P0
    angle_m = np.arctan2(vector.y, vector.x)
    a, b = _bezier_optimal(angle0 - angle_m, angle3 - angle_m)

    scaling = vector.norm()
    if scaling > 0:
        P1 = a * scaling * _Point(np.cos(angle0), np.sin(angle0)) + P0
        P2 = P3 - b * scaling * _Point(np.cos(angle3), np.sin(angle3))
        curve_func = bezier_line(P0, P1, P2, P3)
        with np.errstate(divide="ignore"):
            # warn if minimum radius is smaller than 3um
            min_radius = np.true_divide(1, max_curvature(P0, P1, P2, P3))
            if min_radius < 3:
                print(
                    "Warning! Min radius: {:.2f} um".format(
                        np.true_divide(1, max_curvature(P0, P1, P2, P3))
                    )
                )
            # print("Total length: {:.3f} um".format(curve_length(curve_func, 0, 1)))
        return curve_func
    else:
        raise RuntimeError(f"Error: calling bezier between two identical points: {P0}, {P3}")


# Allow us to use these functions directly with pya.DPoints

try:
    import klayout.db as pya

    _bezier_optimal_pure = bezier_optimal

    def bezier_optimal(P0, P3, *args, **kwargs):
        """If inside KLayout, return computed list of KLayout points."""
        P0 = _Point(P0.x, P0.y)
        P3 = _Point(P3.x, P3.y)
        scale = (P3 - P0).norm()  # rough length.
        # if scale > 1000:  # if in nanometers, convert to microns
        #     scale /= 1000
        # This function returns a np.array of Points.
        # We need to convert to array of Point coordinates
        new_bezier_line = _bezier_optimal_pure(P0, P3, *args, **kwargs)
        bezier_point_coordinates = lambda t: np.array([new_bezier_line(t).x, new_bezier_line(t).y])

        t_sampled, bezier_point_coordinates_sampled = sample_function(
            bezier_point_coordinates, [0, 1], tol=0.005 / scale
        )  # tol about 5 nm

        # The following adds two points right after the first and before the last point
        # to guarantee that the first edge of the path goes out in the direction
        # of the 'port'.

        insert_at = np.argmax(0.001 / scale < t_sampled)
        t_sampled = np.insert(t_sampled, insert_at, 0.001 / scale)
        bezier_point_coordinates_sampled = np.insert(
            bezier_point_coordinates_sampled,
            insert_at,
            bezier_point_coordinates(0.001 / scale),
            axis=1,
        )  # add a point right after the first one
        insert_at = np.argmax(1 - 0.001 / scale < t_sampled)
        # t_sampled = np.insert(t_sampled, insert_at, 1 - 0.001 / scale)
        bezier_point_coordinates_sampled = np.insert(
            bezier_point_coordinates_sampled,
            insert_at,
            bezier_point_coordinates(1 - 0.001 / scale),
            axis=1,
        )  # add a point right before the last one
        # bezier_point_coordinates_sampled = \
        #     np.append(bezier_point_coordinates_sampled, np.atleast_2d(bezier_point_coordinates(1 + .001 / scale)).T,
        #               axis=1)  # finish the waveguide a little bit after

        return [pya.DPoint(x, y) for (x, y) in zip(*(bezier_point_coordinates_sampled))]


except ImportError:
    logger.error("klayout not detected. It is a requirement of zeropdk for now.")
    raise
