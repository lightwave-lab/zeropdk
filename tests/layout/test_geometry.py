from ..context import zeropdk  # noqa
from math import isclose

import klayout.db as kdb
from zeropdk.layout.geometry import curve_length, rotate90


def test_curve_length():
    ex = kdb.DVector(1, 0)
    ey = rotate90(ex)
    origin = kdb.DPoint()
    t0, t1 = 0, 1

    def curve(t: float) -> kdb.DPoint:
        return origin + t * ey + t * ex

    assert isclose(curve_length(curve, t0, t1), 1.4142135623730956 * (t1 - t0))
