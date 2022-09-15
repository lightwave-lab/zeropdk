from dataclasses import Field, field
from typing import Tuple
from zeropdk.pcell import (
    PCell,
    PCellParameter,
    TypeDouble,
    TypeInt,
    TypeLayer,
    TypePoint,
    Port,
    ParamContainer,
    TypeVector,
)
from zeropdk.layout import insert_shape
from zeropdk.layout.polygons import rectangle
from zeropdk.klayout_helper import as_vector, as_point
from klayout.db import DPoint, DVector

pad_width = PCellParameter(
    name="pad_width",
    type=TypeDouble,
    description="Width of electrical pad.",
    default=120,
    unit="um",
)

pad_height = PCellParameter(
    name="pad_height",
    type=TypeDouble,
    description="Height of electrical pad.",
    default=120,
    unit="um",
)

port_width = PCellParameter(
    name="port_width",
    type=TypeDouble,
    description="Port width (same as trace width)",
    default=20,
    unit="um",
)

pad_array_count = PCellParameter(
    name="pad_array_count", type=TypeInt, description="Number of pads", default=10
)

pad_array_pitch = PCellParameter(
    name="pad_array_pitch",
    type=TypeDouble,
    description="Pad array pitch",
    default=150,
    unit="um",
)

origin = PCellParameter(name="origin", type=TypePoint, description="Origin", default=DPoint(0, 0))

ex = PCellParameter(
    name="ex", type=TypeVector, description="x-axis unit vector", default=DVector(1, 0)
)

ey = PCellParameter(
    name="ey", type=TypeVector, description="y-axis unit vector", default=DVector(0, 1)
)
layer_metal = PCellParameter(name="layer_metal", type=TypeLayer, description="Metal Layer")

layer_opening = PCellParameter(name="layer_opening", type=TypeLayer, description="Open Layer")


class OrientedCell(PCell):
    """A standard cell that has the following parameters:
    - origin: Point
    - ex: unit vector of x axis
    - ey: unit vector of y axis
    """

    params = ParamContainer(origin, ex, ey)

    def origin_ex_ey(self) -> Tuple[DPoint, DVector, DVector]:
        origin = as_point(self.params["origin"])  # type: ignore
        ex = as_vector(self.params.ex)  # type: ignore
        ey = as_vector(self.params.ey)  # type: ignore
        return origin, ex, ey


class DCPad(OrientedCell):
    """A standard DC pad.

    Ports: el0
    """

    params = ParamContainer(pad_width, pad_height, port_width, layer_metal, layer_opening)

    def draw(self, cell):
        layout = cell.layout()
        origin, ex, ey = self.origin_ex_ey()
        cp = self.params

        def make_shape_from_dpolygon(dpoly, resize_dx, dbu, layer):
            dpoly.resize(resize_dx, dbu)
            # if resize_dx > dbu:
            #     dpoly.round_corners(resize_dx, 100)
            insert_shape(cell, layer, dpoly)
            return dpoly

        def make_pad(origin, pad_width, pad_height, ex, ey):
            pad_square = rectangle(origin, pad_width, pad_height, ex, ey)
            make_shape_from_dpolygon(pad_square, 0, layout.dbu, cp.layer_metal)
            make_shape_from_dpolygon(pad_square, -2.5, layout.dbu, cp.layer_opening)

        make_pad(origin + (cp.pad_height * ey) / 2, cp.pad_width, cp.pad_height, ex, ey)

        port = Port("el0", origin + cp.port_width * ey / 2, -ey, cp.port_width, "el_dc")

        return cell, {"el0": port}


class DCPadArray(DCPad):
    params = ParamContainer(pad_array_count, pad_array_pitch)

    def draw(self, cell):
        cp = self.params
        origin, ex, _ = self.origin_ex_ey()

        ports = {}

        for i in range(cp.pad_array_count):
            dcpad = DCPad(name=f"pad_{i}", params=cp)
            dc_ports = dcpad.place_cell(cell, origin + cp.pad_array_pitch * i * ex)
            ports[f"el_{i}"] = dc_ports["el0"].rename(f"el_{i}")
            # self.add_port(dc_ports["el0"].rename(f"el_{i}"))

        return cell, ports
