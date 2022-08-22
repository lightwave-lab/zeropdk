from typing import Callable, Tuple
import warnings
import numpy as np
import pytest
from zeropdk.klayout_extend.layout import layout_read_cell

from zeropdk.layout.waveguide_rounding import compute_rounded_path, layout_waveguide_from_points
from ..context import zeropdk  # noqa
from zeropdk.layout.waveguides import waveguide_dpolygon
from zeropdk.layout import insert_shape

import klayout.db as kdb


@pytest.fixture
def top_cell():
    def _top_cell() -> Tuple[kdb.Cell, kdb.Layout]:
        layout = kdb.Layout()
        layout.dbu = 0.001
        TOP = layout.create_cell("TOP")
        return TOP, layout

    return _top_cell


def test_waveguide(top_cell: Callable[[], Tuple[kdb.Cell, kdb.Layout]]):
    t = np.linspace(-1, 1, 100)
    ex = kdb.DPoint(1, 0)
    ey = kdb.DPoint(0, 1)

    # list of points depicting a parabola
    points_list = 100 * t * ex + 100 * t ** 2 * ey
    dbu = 0.001
    width = 1

    wg = waveguide_dpolygon(points_list, width, dbu, smooth=True)

    # write to test_waveguide.gds (we should see a parabola)
    TOP, layout = top_cell()
    layer = "1/0"
    insert_shape(TOP, layer, wg)
    TOP.write("tests/tmp/test_waveguide.gds")


def test_waveguide_rounding(top_cell: Callable[[], Tuple[kdb.Cell, kdb.Layout]]):
    def trace_rounded_path(cell, layer, rounded_path, width):
        points = []
        for item in rounded_path:
            points.extend(item.get_points())

        dpath = kdb.DPath(points, width, 0, 0)

        cell.shapes(layer).insert(dpath)

    def trace_reference_path(cell, layer, points, width):
        dpath = kdb.DPath(points, width, 0, 0)
        cell.shapes(layer).insert(dpath)

    TOP, layout = top_cell()
    layer = kdb.LayerInfo(10, 0)
    layerRec = kdb.LayerInfo(1001, 0)

    ex, ey = kdb.DPoint(1, 0), kdb.DPoint(0, 1)

    # Begin tests

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


    # Stress test about ClearanceRewind when forward would work.
    origin = 40 * ex + 80 * ey
    points = [
        0 * ex,
        222 * ey,
        20 * ex + 222 * ey,
        20 * ex + 371 * ey,
    ]
    points_ = [origin + point for point in points]
    layout_waveguide_from_points(TOP, layer, points_, 5, 500)

    # Stress test on trying forward first after ClearanceRewind.

    origin = 60 * ex + 80 * ey
    points = [
        0 * ex,
        222 * ey,
        231 * ex + 222 * ey,
        231 * ex + 460 * ey,
    ]
    points_ = [origin + point for point in points]
    # breakpoint()
    layout_waveguide_from_points(TOP, layer, points_, 5, 230)

    origin = 80 * ex + 80 * ey
    points = [
        0 * ex,
        100 * ey,
        30 * ex + 100 * ey,
        30 * ex + 200 * ey,
    ]
    points_ = [origin + point for point in points]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        layout_waveguide_from_points(TOP, layer, points_, 5, 550)

    TOP_reference = layout_read_cell(layout, "TOP", "tests/test_waveguide_rounding_truth.gds")

    new_waveguides = kdb.Region(TOP.shapes(layer))
    ref_waveguides = kdb.Region(TOP_reference.shapes(layer))
    new_waveguides -= ref_waveguides
    assert new_waveguides.area() == 0

    TOP.write("tests/tmp/test_waveguide_rounding.gds")