import numpy as np
from zeropdk.layout.algorithms.sampling import sample_function


def rotate(point, angle_rad):
    ''' Rotates point counter-clockwisely about its origin by an angle given in radians'''
    th = angle_rad
    x, y = point.x, point.y
    new_x = x * np.cos(th) - y * np.sin(th)
    new_y = y * np.cos(th) + x * np.sin(th)
    return point.__class__(new_x, new_y)


rotate90 = lambda point: rotate(point, np.pi / 2)


def cross_prod(p1, p2):
    return p1.x * p2.y - p1.y * p2.x


def project(v, ex, ey=None):
    ''' Compute a such that v = a * ex + b * ey '''
    if ey is None:
        ey = rotate90(ex)

    assert cross_prod(ex, ey) != 0

    # Simple formula
    # https://math.stackexchange.com/questions/148199/equation-for-non-orthogonal-projection-of-a-point-onto-two-vectors-representing

    a = cross_prod(ey, v) / cross_prod(ey, ex)
    # b = cross_prod(ex, v) / cross_prod(ex, ey)

    # v == a * ex + b * ey
    return a


def curve_length(curve, t0=0, t1=1):
    ''' Computes the total length of a curve.

    Args:
        curve: list of Points, or
            parametric function of points, to be computed from t0 to t1.
    '''
    # TODO possible bug: if the curve is a loop, it will return 0 (BAD)
    if isinstance(curve, list):
        # assuming curve is a list of points
        scale = (curve[-1] - curve[0]).norm()
        if scale > 0:
            coords = np.array([[point.x, point.y] for point in curve]).T
            dp = np.diff(coords, axis=-1)
            ds = np.sqrt((dp**2).sum(axis=0))
            return ds.sum()
        else:
            return 0
    else:
        # assuming curve is a function.
        curve_func = curve
        scale = (curve_func(t1) - curve_func(t0)).norm()
        if scale > 0:
            coords = lambda t: np.array([curve_func(t).x, curve_func(t).y])
            _, sampled_coords = sample_function(coords, [t0, t1], tol=0.0001 / scale, min_points=100)  # 1000 times more precise than the scale
            dp = np.diff(sampled_coords, axis=-1)
            ds = np.sqrt((dp**2).sum(axis=0))
            return ds.sum()
        else:
            return 0
