from typing import Callable, Tuple
import warnings
import numpy as np
import numpy.typing as npt
import pytest
from zeropdk.klayout_helper.layout import layout_read_cell

from zeropdk.layout.waveguide_rounding import compute_rounded_path, layout_waveguide_from_points
from ..context import zeropdk  # noqa
from zeropdk.layout.waveguides import waveguide_dpolygon
from zeropdk.layout import insert_shape
from zeropdk.klayout_helper import as_point

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
    ex = kdb.DVector(1, 0)
    ey = kdb.DVector(0, 1)
    origin = kdb.DPoint(0, 0)
    # list of points depicting a parabola
    points_list: npt.NDArray[np.object_] = origin + 100 * t * ex + 100 * t**2 * ey  # type: ignore
    dbu = 0.001
    width = 1
    assert isinstance(points_list, np.ndarray)
    assert isinstance(points_list[0], kdb.DPoint)
    assert points_list.shape == (100,)
    wg = waveguide_dpolygon(points_list, width, dbu, smooth=True)  # type: ignore

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
        insert_shape(cell, layer, dpath)

    def trace_reference_path(cell, layer, points, width):
        dpath = kdb.DPath(points, width, 0, 0)
        insert_shape(cell, layer, dpath)

    TOP, layout = top_cell()
    layer = kdb.LayerInfo(10, 0)
    layerRec = kdb.LayerInfo(1001, 0)

    ex, ey = kdb.DVector(1, 0), kdb.DVector(0, 1)

    # Begin tests

    points = [0 * ex, 10 * ex, 10 * (ex + ey), 30 * ex]
    origin = as_point(0 * ey)
    points = [origin + point for point in points]
    x = compute_rounded_path(points, 3)
    trace_rounded_path(TOP, layer, x, 0.5)
    trace_reference_path(TOP, layerRec, points, 0.5)

    points = [0 * ex, 10 * ex, 5 * (ex - ey), 17 * ex, 30 * ex]
    origin = as_point(30 * ey)
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
        origin = as_point(15 * ex + 40 * ey)
        points = [origin + point for point in points]
        x = compute_rounded_path(points, radius)
        trace_rounded_path(TOP, layer, x, 0.5)
        trace_reference_path(TOP, layerRec, points, 0.5)

    # Layout tapered waveguide
    vectors = [
        0 * ex,
        100 * ex,
        100 * ex + 20 * ey,
        10 * ex + 5 * ey,
        10 * ex + 25 * ey,
        100 * ex + 30 * ey,
    ]

    # Untapered
    origin = as_point(40 * ex)
    points_ = [origin + v for v in vectors]
    layout_waveguide_from_points(TOP, layer, points_, 0.5, 5)

    # Tapered
    origin = as_point(40 * ex + 40 * ey)
    points_ = [origin + vector for vector in vectors]
    layout_waveguide_from_points(TOP, layer, points_, 0.5, 5, taper_width=3, taper_length=10)

    # Stress test about ClearanceRewind when forward would work.
    origin = as_point(40 * ex + 80 * ey)
    points = [
        0 * ex,
        222 * ey,
        20 * ex + 222 * ey,
        20 * ex + 371 * ey,
    ]
    points_ = [origin + point for point in points]
    layout_waveguide_from_points(TOP, layer, points_, 5, 500)

    # Stress test on trying forward first after ClearanceRewind.

    origin = as_point(60 * ex + 80 * ey)
    points = [
        0 * ex,
        222 * ey,
        231 * ex + 222 * ey,
        231 * ex + 460 * ey,
    ]
    points_ = [origin + point for point in points]
    # breakpoint()
    layout_waveguide_from_points(TOP, layer, points_, 5, 230)

    origin = as_point(80 * ex + 80 * ey)
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
    layer_index = layout.layer(layer)
    new_waveguides = kdb.Region(TOP.shapes(layer_index))
    ref_waveguides = kdb.Region(TOP_reference.shapes(layer_index))
    assert (new_waveguides ^ ref_waveguides).area() == 0  # XOR operation

    TOP.write("tests/tmp/test_waveguide_rounding.gds")
