import numpy as np


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
