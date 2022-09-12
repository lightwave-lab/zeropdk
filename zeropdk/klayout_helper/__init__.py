import klayout.db as kdb
from typing import Protocol


class PointProtocol(Protocol):
    x: float
    y: float

def as_point(p: PointProtocol) -> kdb.DPoint:
    return kdb.DPoint(p.x, p.y)

def as_vector(p: PointProtocol) -> kdb.DVector:
    return kdb.DVector(p.x, p.y)
