""" Straight waveguide rounding algorithms"""
from functools import lru_cache
from math import atan2, tan, inf
import numpy as np
import klayout.db as kdb
from zeropdk.layout.geometry import rotate, fix_angle, cross_prod
from zeropdk.layout.algorithms.sampling import sample_function
from zeropdk.layout.waveguides import layout_waveguide


def angle_between(v1, v0):
    """Compute angle in radians between v1 and v0.
    Rotation angle from v0 to v1 counter-clockwise.
    """
    return fix_angle(atan2(v1.y, v1.x) - atan2(v0.y, v0.x))


def project(P, A, B):
    """Projects a point P into a line defined by A and B"""
    AB = B - A
    eAB = AB / AB.norm()

    Pproj = A + (P - A) * eAB * eAB
    return Pproj


def bisect(V1, V2):
    """Bisects two vectors V1 and V2. Returns a vector."""

    # from https://math.stackexchange.com/questions/2285965/how-to-find-the-vector-formula-for-the-bisector-of-given-two-vectors

    V = V1.norm() * V2 + V2.norm() * V1
    return V / V.norm()


def intersect(A, eA, B, eB):
    """Computes intersection between lines defined by points A/B and vectors eA/eB"""

    # from http://mathforum.org/library/drmath/view/62814.html

    assert abs(cross_prod(eA, eB)) > 0, "Vectors must not be parallel"

    a = cross_prod(B - A, eB) / cross_prod(eA, eB)
    return A + a * eA


@lru_cache(maxsize=5)
def _min_clearance(angle_rad, radius):
    """ Compute the minimum clearance for a tangent arc given an vertex angle."""
    try:
        return abs(radius / tan(angle_rad / 2))
    except ZeroDivisionError:
        return inf


def _solve_Z_angle(α1, α2, BC, R):
    from math import sin, cos, tan, atan, acos

    assert α1 * α2  # they should have the same sign
    sign = α1 / abs(α1)

    α1, α2 = abs(α1), abs(α2)

    αprime = atan(0.5 / tan(α1) + 0.5 / tan(α2))
    A = 2 / cos(αprime)
    γ = -αprime + acos(1 / A * (1 / sin(α1) + 1 / sin(α2) - BC / R))

    return γ * sign


class ClearanceRewind(Exception):
    pass


class ClearanceForward(Exception):
    pass


class _Arc:
    def __init__(self, P1, C, P2, ccw):
        from math import isclose

        assert isclose(
            (P2 - C).norm(), (P1 - C).norm(), abs_tol=1e-9
        ), "Invalid Arc"  # inconsistent radius
        self.P1 = P1  # first point
        self.C = C  # center
        self.P2 = P2  # second point
        self.ccw = ccw  # True if counter-clockwise

    def get_points(self):
        from math import atan2, pi

        P1, C, P2 = self.P1, self.C, self.P2

        r = (P2 - C).norm()

        theta_start = atan2((P1 - C).y, (P1 - C).x)
        theta_end = atan2((P2 - C).y, (P2 - C).x)
        if self.ccw:
            theta_end = (theta_end - theta_start) % (2 * pi) + theta_start
        else:
            theta_start = (theta_start - theta_end) % (2 * pi) + theta_end
            theta_start, theta_end = theta_end, theta_start

        arc_function = lambda t: np.array([r * np.cos(t), r * np.sin(t)])

        # in the function below, theta_start must be smaller than theta_end
        t, coords = sample_function(arc_function, [theta_start, theta_end], tol=0.002 / r)

        # This yields a better polygon
        # The idea is to place a point right after the first one, to
        # make sure the arc starts in the right direction
        insert_at = np.argmax(theta_start + 0.001 <= t)
        t = np.insert(t, insert_at, theta_start + 0.001)
        coords = np.insert(coords, insert_at, arc_function(theta_start + 0.001), axis=1)
        insert_at = np.argmax(theta_end - 0.001 <= t)
        coords = np.insert(
            coords, insert_at, arc_function(theta_end - 0.001), axis=1
        )  # finish the waveguide a little bit after

        # create original waveguide poligon prior to clipping and rotation
        dpoints_list = [C + kdb.DPoint(x, y) for x, y in zip(*coords)]
        if not self.ccw:
            dpoints_list = list(reversed(dpoints_list))
        return dpoints_list

    def __repr__(self):
        return "Arc({P1}, {C}, {P2}, {CCW})".format(P1=self.P1, C=self.C, P2=self.P2, CCW=self.ccw)


class _Line:
    def __init__(self, P1, P2):
        self.P1 = P1
        self.P2 = P2

    def get_points(self):
        return [self.P1, self.P2]

    def get_length(self):
        return (self.P2 - self.P1).norm()

    def __repr__(self):
        return "Line({P1}, {P2})".format(P1=self.P1, P2=self.P2)


def solve_Z(A, B, C, D, radius):
    from math import sin, pi, copysign

    AB = B - A
    BC = C - B
    CD = D - C

    α1 = angle_between(-BC, AB)
    α2 = angle_between(-BC, CD)

    # print("AB, BC, CD=", AB, BC, CD)
    # print("α1, α2=", degrees(α1), degrees(α2))

    γ = _solve_Z_angle(α1, α2, BC.norm(), radius)
    # print("γ=", degrees(γ))
    eX1X2 = rotate(-BC, -γ) / BC.norm()
    # print("eX1X2=", eX1X2)

    x = radius / BC.norm() * (1 - sin(abs(α1 - γ))) / sin(abs(α1))
    # print("x=", x)
    X = B + x * BC
    # print("X=", X)
    X1 = X - eX1X2 * radius
    X2 = X + eX1X2 * radius

    Aprime = X1 + rotate(X - X1, copysign(pi / 2, α1) + γ - α1)
    Dprime = X2 + rotate(X - X2, copysign(pi / 2, α2) + γ - α2)

    # print("line", A, Aprime)
    # print("arc2", Aprime, X1, X)
    # print("arc2", X, X2, Dprime)
    # print("line", Dprime, D)

    return (
        [_Line(A, Aprime), _Arc(Aprime, X1, X, α1 < 0), _Arc(X, X2, Dprime, α1 > 0)],
        [Dprime, D],
    )


def solve_U(A, B, C, D, radius):
    # TODO: known bug. This assumes that there is enough space between
    # A and B / C and D to perform the turn. Suggestion: if there isn't,
    # abort or move Eprime and Gprime accordingly.
    XB = bisect(A - B, C - B)
    XC = bisect(B - C, D - C)

    orientation = cross_prod(XB, XC) > 0  # positive if CCW waveguide turn

    X = intersect(B, XB, C, XC)

    XB, XC = B - X, C - X

    Fprime = project(X, B, C)

    h = (Fprime - X).norm()

    # if h is too close to R, we will have extra unnecessary arcs
    # use two solve_3 with h as a radius instead
    if h >= radius - 0.001:
        solution1, rest_points = solve_3(A, B, C, h)
        solution2, rest_points = solve_3(rest_points[0], C, D, h)
        return solution1 + solution2, rest_points

    # F = X + (Fprime - X) * radius / h

    # Bprime = X + XB * radius / h
    # Cprime = X + XC * radius / h

    eAB = B - A
    eAB /= eAB.norm()
    eDC = C - D
    eDC /= eDC.norm()

    Eprime = project(X, A, B)
    Gprime = project(X, D, C)

    E = X + (Eprime - X) * radius / h
    G = X + (Gprime - X) * radius / h

    def compute_A_prime(E, Eprime, eAB):
        from math import sqrt

        D = (E - Eprime).norm()
        L = sqrt(D * (4 * radius - D))
        Aprime = Eprime - eAB * L
        return Aprime

    Aprime = compute_A_prime(E, Eprime, eAB)
    Dprime = compute_A_prime(G, Gprime, eDC)

    Asec = Aprime + (E - X)
    Dsec = Dprime + (G - X)

    H = 0.5 * (Asec + X)
    II = 0.5 * (Dsec + X)

    return (
        [
            _Line(A, Aprime),
            _Arc(Aprime, Asec, H, not orientation),
            _Arc(H, X, II, orientation),
            _Arc(II, Dsec, Dprime, not orientation),
        ],
        [Dprime, D],
    )


def solve_2(A, B):
    return [_Line(A, B)], []


def solve_V(A, B, C, radius):
    XB = bisect(A - B, C - B)

    isCCW = cross_prod(C - B, A - B) > 0

    Aprime = project(A, B, XB + B)
    Cprime = project(C, B, XB + B)

    rA = (A - Aprime).norm()
    rC = (C - Cprime).norm()

    if rA > rC:
        Csec = project(Cprime, A, B)
        return [_Line(A, Csec), _Arc(Csec, Cprime, C, isCCW)], []
    else:
        Asec = project(Aprime, B, C)
        return [_Arc(A, Aprime, Asec, isCCW)], [Asec, C]


def solve_3(A, B, C, radius):
    from math import cos, pi

    p0, p1, p2 = A, B, C
    α = angle_between(p0 - p1, p2 - p1)

    if α % (2 * pi) == pi:
        # if points are collinear, just ignore middle point
        return ([], [p0, p2])

    # sometimes users pick len1 and len2 to be exactly 1 radius.
    # in that case, numerical errors might result in a ClearanceRewind
    # or ClearanceForward.
    # I am adding this 0.001 fix to correct that.
    clear = _min_clearance(α, radius - 0.001)

    len1 = (p1 - p0).norm()
    len2 = (p2 - p1).norm()

    if len1 < clear:
        raise ClearanceRewind()
    if len2 < clear:
        raise ClearanceForward()

    e1 = (p1 - p0) / len1
    e2 = (p2 - p1) / len2

    arc_center = p1 + 0.5 * (-e1 * clear + e2 * clear) / cos(α / 2) ** 2
    return (
        [
            _Line(p0, p1 - e1 * clear),
            _Arc(p1 - e1 * clear, arc_center, p1 + e2 * clear, α > 0),
        ],
        [p1 + e2 * clear, p2],
    )


def solve_4(A, B, C, D, radius):
    AB = B - A
    BC = C - B
    CD = D - C

    α1 = angle_between(-BC, AB)
    α2 = angle_between(-BC, CD)

    if α1 * α2 > 0:
        return solve_Z(A, B, C, D, radius)
    else:
        return solve_U(A, B, C, D, radius)


def compute_rounded_path(points, radius):
    """Transforms a list of points into sections of arcs and straight lines.
    Approach:
        - Go through the list of points in triplets (A, B, C).
        - Call solve3 in (A,B,C), which returns a rounded path plus (Bprime, C)
        - Continue.
        - If solve3 cannot solve because AB is too short, raise a ClearanceRewind error
        - Conversely, if solve3 cannot solve because BC is too short, raise a ClearanceForward error
        - In the case of ClearanceForward, call solve4 on (A,B,C,D)
        - In the case of ClearanceForward, call solve4 on (O,A,B,C), where O is the previous point
    Returns:
        - A list of _Line and _Arc objects
    """
    points_list = list(points)  # in case points_list is an iterator
    N = len(points_list)

    if N == 2:
        return [_Line(*points)]

    # Sanity checks
    assert N >= 3, "Insufficient number of points, N = {N} < 3".format(N=N)

    old_rounded_path = rounded_path = list()
    old_points_left = points_left = list(points)
    can_rewind = False

    while len(points_left) > 2:
        try:
            solution, rest_points = solve_3(*points_left[0:3], radius)
            old_points_left = points_left[:]
            points_left = rest_points + points_left[3:]
            can_rewind = True
        except ClearanceRewind:
            if not can_rewind:
                raise RuntimeError(
                    "Not enough space for enough turns: Cannot solve:", *points_left[0:3]
                )
            points_left = old_points_left
            rounded_path = old_rounded_path
            if len(points_left[0:4]) < 4:
                raise RuntimeError(
                    "Not enough space for enough turns: Cannot solve:", *points_left[0:4]
                )
            solution, rest_points = solve_4(*points_left[0:4], radius)
            old_points_left = points_left[:]
            points_left = rest_points + points_left[4:]
            can_rewind = False
        except ClearanceForward:
            if len(points_left[0:4]) < 4:
                raise RuntimeError(
                    "Not enough space for enough turns: Cannot solve:", *points_left[0:4]
                )
            solution, rest_points = solve_4(*points_left[0:4], radius)
            old_points_left = points_left[:]
            points_left = rest_points + points_left[4:]
            can_rewind = False

        old_rounded_path = rounded_path[:]
        rounded_path += solution

    # there should be 2 points left in points_left
    solution, rest_points = solve_2(*points_left[0:2])
    rounded_path += solution
    points_left = rest_points + points_left[2:]

    assert len(points_left) == 0

    return rounded_path


class _Path:
    """ Object holding path plus width information"""

    def __init__(self, points, widths):
        self.points = points

        # This can be a single width or a list of widths, just like in layout_waveguide()
        self.widths = widths

    def layout(self, cell, layer):
        layout_waveguide(cell, layer, self.points, self.widths, smooth=False)

    def __repr__(self):
        return "Path({point1}...{pointN}, {widths})".format(
            point1=self.points[0], pointN=self.points[-1], widths=self.widths
        )


class _Taper(_Path):
    def __init__(self, P1, P2, w1, w2):
        self.P1 = P1
        self.P2 = P2
        self.w1 = w1
        self.w2 = w2

        self.points = [P1, P2]
        self.widths = [w1, w2]

    def __repr__(self):
        return "Taper({P1}, {P2}, w1={w1}, w2={w2})".format(
            P1=self.P1, P2=self.P2, w1=self.w1, w2=self.w2
        )


def _compute_tapered_line(line, waveguide_width, taper_width, taper_length):
    """Takes a _Line object and computes two tapers with taper_width and taper_length"""

    minimum_length = 30 + 2 * taper_length  # don't bother tapering waveguides beyond this length

    P1, P2 = line.get_points()

    if line.get_length() < minimum_length:
        return [_Path([P1, P2], waveguide_width)]

    u = P2 - P1
    u /= u.norm()

    return [
        _Taper(P1, P1 + u * taper_length, waveguide_width, taper_width),
        _Path([P1 + u * taper_length, P2 - u * taper_length], taper_width),
        _Taper(P2 - u * taper_length, P2, taper_width, waveguide_width),
    ]


def compute_untapered_path(path, waveguide_width):
    return [_Path(element.get_points(), waveguide_width) for element in path]


def compute_tapered_path(path, waveguide_width, taper_width, taper_length):
    tapered_path = []
    for element in path:
        if isinstance(element, _Line):
            tapered_path += _compute_tapered_line(
                element, waveguide_width, taper_width, taper_length
            )
        elif isinstance(element, _Arc):
            tapered_path += [_Path(element.get_points(), waveguide_width)]

    return tapered_path


def unique_points(point_list):
    if len(point_list) < 2:
        return point_list

    unique_points = [point_list[0]]
    previous_point = point_list[0]
    for point in point_list[1:]:
        if (point - previous_point).norm() > 1e-4:
            unique_points.append(point)
            previous_point = point

    return unique_points


def layout_waveguide_from_points(
    cell, layer, points, width, radius, taper_width=None, taper_length=None
):

    assert radius > width / 2, "Please use a radius larger than the half-width"
    points = unique_points(points)

    if len(points) < 2:
        # Nothing to do
        return cell

    # First, get the list of lines and arcs
    try:
        rounded_path = compute_rounded_path(points, radius)
    except Exception as e:
        print("ERROR:", e)
        print("Continuing...")
        layout_waveguide(cell, layer, points, 0.1)
        return cell

    # Taper path if necessary
    if taper_width is not None and taper_length is not None:
        waveguide_path = compute_tapered_path(rounded_path, width, taper_width, taper_length)
    else:
        waveguide_path = compute_untapered_path(rounded_path, width)

    # creating a single path
    _draw_points = []
    _draw_widths = []
    for element in waveguide_path:
        points, width = element.points, element.widths
        n_points = len(points)
        try:
            if len(width) == n_points:
                _draw_points.extend(points)
                _draw_widths.extend(width)
            elif len(width) == 2:
                _draw_widths.extend(np.linspace(width[0], width[1], n_points))
                _draw_points.extend(points)
            else:
                raise RuntimeError("Internal error detected. Debug please.")
        except TypeError:
            _draw_points.extend(points)
            _draw_widths.extend(np.ones(n_points) * width)

    # deleting repeated points
    _cur_point = None
    _draw_points2 = []
    _draw_widths2 = []
    for p, w in zip(_draw_points, _draw_widths):
        if _cur_point and p == _cur_point:
            continue
        _draw_points2.append(p)
        _draw_widths2.append(w)
        _cur_point = p

    layout_waveguide(cell, layer, _draw_points2, _draw_widths2, smooth=False)

    return cell


def main():
    def trace_rounded_path(cell, layer, rounded_path, width):
        points = []
        for item in rounded_path:
            points.extend(item.get_points())

        dpath = kdb.DPath(points, width, 0, 0)

        cell.shapes(layer).insert(dpath)

    def trace_reference_path(cell, layer, points, width):
        dpath = kdb.DPath(points, width, 0, 0)
        cell.shapes(layer).insert(dpath)

    layout = kdb.Layout()
    TOP = layout.create_cell("TOP")
    layer = kdb.LayerInfo(10, 0)
    layerRec = kdb.LayerInfo(1001, 0)

    ex, ey = kdb.DPoint(1, 0), kdb.DPoint(0, 1)

    points = [0 * ex, 10 * ex, 10 * (ex + ey), 30 * ex]
    origin = 0 * ey
    points = [origin + point for point in points]
    x = compute_rounded_path(points, 3)
    trace_rounded_path(TOP, layer, x, 0.5)
    trace_reference_path(TOP, layerRec, points, 0.5)

    points = [0 * ex, 10 * ex, 5 * (ex - ey), 17 * ex, 30 * ex]
    origin = 30 * ey
    points = [origin + point for point in points]
    x = compute_rounded_path(points, 3)
    trace_rounded_path(TOP, layer, x, 0.5)
    trace_reference_path(TOP, layerRec, points, 0.5)

    radius = 3
    for ex2 in (ex, -ex):
        points = [2 * ex2]
        for d in np.arange(1, 10, 2.5):
            origin = points[-1]
            displacements = [
                4 * radius * ex2,
                4 * radius * ex2 + d * ey - 1 * d * ex2,
                d * ey,
                (d + 2 * radius) * ey,
            ]
            points += [origin + displacement for displacement in displacements]
        origin = 15 * ex + 40 * ey
        points = [origin + point for point in points]
        x = compute_rounded_path(points, radius)
        trace_rounded_path(TOP, layer, x, 0.5)
        trace_reference_path(TOP, layerRec, points, 0.5)

    # Layout tapered waveguide
    points = [
        0 * ex,
        100 * ex,
        100 * ex + 20 * ey,
        10 * ex + 5 * ey,
        10 * ex + 25 * ey,
        100 * ex + 30 * ey,
    ]

    # Untapered
    origin = 40 * ex
    points_ = [origin + point for point in points]
    layout_waveguide_from_points(TOP, layer, points_, 0.5, 5)

    # Tapered
    origin = 40 * ex + 40 * ey
    points_ = [origin + point for point in points]
    layout_waveguide_from_points(TOP, layer, points_, 0.5, 5, taper_width=3, taper_length=10)

    print("Wrote waveguide_rounding.gds")
    TOP.write("waveguide_rounding.gds")


if __name__ == "__main__":
    main()
