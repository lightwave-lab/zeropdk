'''
klayout.db.Point Extensions:
  - P * np/number
  - np/number * P
  - P * P
  - P / number
  - P.norm()
'''
from numbers import Number
from math import sqrt
from klayout.db import Point, DPoint, DVector, Vector

try:
    import numpy as np
    MODULE_NUMPY = True
except ImportError:
    MODULE_NUMPY = False

# Point-like classes
PointLike = (Point, DPoint, DVector, Vector)


def pyaPoint__rmul__(self, factor):
    """ This implements factor * P """
    if isinstance(factor, Number):
        return self.__class__(self.x * factor, self.y * factor)
    elif MODULE_NUMPY and isinstance(factor, np.ndarray):  # ideally this is never called
        return factor.__mul__(self)
    else:
        return NotImplemented


def pyaPoint__mul__(self, factor):
    """ This implements P * factor """
    if isinstance(factor, Number):
        return self.__class__(self.x * factor, self.y * factor)
    elif MODULE_NUMPY and isinstance(factor, np.ndarray):  # Numpy can multiply any object
        return factor.__mul__(self)
    elif isinstance(factor, PointLike):
        return self.x * factor.x + self.y * factor.y
    else:
        return NotImplemented


def pyaPoint__truediv__(self, dividend):
    """ This implements P / dividend """
    return self.__class__(self.x / dividend, self.y / dividend)


def pyaPoint__deepcopy__(self, memo):
    new_point = self.__class__(self.x, self.y)
    return new_point


def pyaPoint_norm(self):
    """ This implements the L2 norm """
    return sqrt(self.x ** 2 + self.y ** 2)


def pyaPoint_normalize(self):
    return self / self.norm()


def pyaPoint__init__(self, *args):
    if len(args) == 1:
        p, = args
        try:
            self.x = p.x
            self.y = p.y
        except:
            raise ValueError('Cannot understand {}'.format(p))
    elif len(args) == 2:
        self.x, self.y = args
    else:
        raise ValueError('Unknown constructor')


for klass in PointLike:
    klass.__init__ = pyaPoint__init__
    klass.__rmul__ = pyaPoint__rmul__
    klass.__mul__ = pyaPoint__mul__
    klass.__truediv__ = pyaPoint__truediv__
    klass.__deepcopy__ = pyaPoint__deepcopy__
    klass.normalize = pyaPoint_normalize
    klass.norm = pyaPoint_norm

import sys
if sys.version_info[0] > 2:
    assert DPoint(1, 2) / 1.0 == DPoint(1, 2)
    assert 0.5 * DPoint(1, 2) == DPoint(0.5, 1)