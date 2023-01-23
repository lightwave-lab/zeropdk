# type: ignore
"""
klayout.db.Point Extensions:
  - P * np/number
  - np/number * P
  - P * P
  - P / number
  - P.norm()
  - P.normalize() = P / P.norm()
"""
from contextlib import contextmanager
from numbers import Real
from klayout.db import Point, DPoint, DVector, Vector

try:
    import numpy as np

    MODULE_NUMPY = True
except ImportError:
    MODULE_NUMPY = False

# Point-like classes
KLayoutPoints = (Point, DPoint, DVector, Vector)


def pyaPoint__rmul__(self, factor):
    """This implements factor * P"""
    if isinstance(factor, Real):
        return self.__class__(self.x * factor, self.y * factor)
    elif MODULE_NUMPY and isinstance(factor, np.ndarray):  # ideally this is never called
        return factor.__mul__(self)
    else:
        return NotImplemented


def pyaPoint__mul__(self, factor):
    """This implements P * factor"""
    if isinstance(factor, Real):
        return self.__class__(self.x * factor, self.y * factor)
    elif MODULE_NUMPY and isinstance(factor, np.ndarray):  # Numpy can multiply any object
        return factor.__mul__(self)
    elif isinstance(factor, KLayoutPoints):
        return self.x * factor.x + self.y * factor.y
    else:
        return NotImplemented


def pyaPoint__truediv__(self, dividend):
    """This implements P / dividend"""
    return self.__class__(self.x / dividend, self.y / dividend)


def pyaPoint__deepcopy__(self, memo):
    return self.__class__(self.x, self.y)


def pyaPoint_norm(self):
    """This implements the L2 norm"""
    return self.abs()


def pyaPoint_normalize(self):
    return self / self.norm()


def pyaPoint__init__(self, *args):
    try:
        self.x, self.y = args
    except (TypeError, ValueError):
        if len(args) == 1:
            (p,) = args
            try:
                self.x = p.x
                self.y = p.y
            except:
                raise ValueError("Cannot understand {}".format(p))
    except Exception:
        raise ValueError("Unknown constructor")


def pyaPoint__getstate__(self):
    return (self.x, self.y)


def pyaPoint__setstate__(self, state):
    self.x, self.y = state


def pyaPoint__repr__(self):
    return f"{self.__class__.__name__}({self.x}, {self.y})"


@contextmanager
def make_points_picklable():
    old_methods = dict()
    for klass in KLayoutPoints:
        old_methods[(klass, "__getstate__")] = getattr(klass, "__getstate__", None)
        old_methods[(klass, "__setstate__")] = getattr(klass, "__setstate__", None)
        klass.__getstate__ = pyaPoint__getstate__
        klass.__setstate__ = pyaPoint__setstate__
    yield
    for klass in KLayoutPoints:
        klass.__getstate__ = old_methods[(klass, "__getstate__")]
        klass.__setstate__ = old_methods[(klass, "__setstate__")]


def patch_points():
    for klass in KLayoutPoints:
        klass.__getstate__ = pyaPoint__getstate__
        klass.__setstate__ = pyaPoint__setstate__
        klass.__init__ = pyaPoint__init__
        klass.__rmul__ = pyaPoint__rmul__
        klass.__mul__ = pyaPoint__mul__
        klass.__truediv__ = pyaPoint__truediv__
        klass.__deepcopy__ = pyaPoint__deepcopy__
        klass.__repr__ = pyaPoint__repr__
        klass.normalize = pyaPoint_normalize
        klass.norm = pyaPoint_norm
