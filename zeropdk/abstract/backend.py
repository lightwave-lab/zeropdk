from abc import ABC


class Point(ABC):

    x = None
    y = None

    def __init__(self, *args):
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


class Vector(Point):
    pass


class Trans(ABC):
    pass


class Cell(ABC):
    pass


class LayerInfo(ABC):
    pass
