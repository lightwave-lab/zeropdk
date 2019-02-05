import numpy as np


def rotate(point, angle_rad):
    ''' Rotates point counter-clockwisely about its origin by an angle given in radians'''
    th = angle_rad
    x, y = point.x, point.y
    new_x = x * np.cos(th) - y * np.sin(th)
    new_y = y * np.cos(th) + x * np.sin(th)
    return point.__class__(new_x, new_y)


rotate90 = lambda point: rotate(point, np.pi / 2)
