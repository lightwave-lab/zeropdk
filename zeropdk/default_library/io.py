from zeropdk.pcell import PCell, PCellParameter, \
    TypeDouble, TypeInt, TypeLayer, TypePoint, \
    Port, ParamContainer
from zeropdk.layout import insert_shape, Point
from zeropdk.layout.polygons import rectangle
from zeropdk.layout.geometry import rotate
from math import pi

pad_width = PCellParameter(
    name='pad_width',
    type=TypeDouble,
    description="Width of electrical pad.",
    default=120,
    unit='um'
)

pad_height = PCellParameter(
    name='pad_height',
    type=TypeDouble,
    description="Height of electrical pad.",
    default=120,
    unit='um'
)

port_width = PCellParameter(
    name='port_width',
    type=TypeDouble,
    description="Port width (same as trace width)",
    default=20,
    unit='um'
)

pad_array_count = PCellParameter(
    name='pad_array_count',
    type=TypeInt,
    description="Number of pads",
    default=10
)

pad_array_pitch = PCellParameter(
    name='pad_array_pitch',
    type=TypeDouble,
    description="Pad array pitch",
    default=150,
    unit='um'
)

origin = PCellParameter(
    name='origin',
    type=TypePoint,
    description="Origin",
    default=Point(0, 0),
)

angle_ex = PCellParameter(
    name='angle_ex',
    type=TypeDouble,
    description="Angle of ex",
    default=0,
    unit='deg'
)

angle_ey = PCellParameter(
    name='angle_ey',
    type=TypeDouble,
    description="Angle of ey",
    default=90,
    unit='deg'
)

mag_x = PCellParameter(
    name='mag_x',
    type=TypeDouble,
    description="Magnitude of ex",
    default=1
)

mag_y = PCellParameter(
    name='mag_y',
    type=TypeDouble,
    description="Magnitude of ey",
    default=1
)

layer_metal = PCellParameter(
    name='layer_metal',
    type=TypeLayer,
    description="Metal Layer",
)

layer_opening = PCellParameter(
    name='layer_opening',
    type=TypeLayer,
    description="Open Layer",
)


class OrientedCell(PCell):
    """ A standard cell that has the following parameters:
    - origin: Point
    - angle_ex: angle of ex
    - angle_ey: angle of ey
    - mag_x: double
    - mag_y: double
    """

    params = ParamContainer(origin,
                            angle_ex,
                            angle_ey,
                            mag_x,
                            mag_y)

    def origin_ex_ey(self):
        lt = self.backend
        origin = lt.Point(self.params['origin'])
        angle_ex_rad = self.params.angle_ex * pi / 180
        angle_ey_rad = self.params.angle_ey * pi / 180
        ex = rotate(lt.Vector(self.params['mag_x'], 0), angle_ex_rad)
        ey = rotate(lt.Vector(self.params['mag_y'], 0), angle_ey_rad)
        return origin, ex, ey


class DCPad(OrientedCell):
    """ A standard DC pad.

    Ports: el0
    """

    params = ParamContainer(pad_width,
                            pad_height,
                            port_width,
                            layer_metal,
                            layer_opening,
                            )

    def draw(self, cell):
        lt = self.backend
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
            pad_square = rectangle(lt, origin, pad_width, pad_height, ex, ey)
            make_shape_from_dpolygon(pad_square, 0, layout.dbu, cp.layer_metal)
            make_shape_from_dpolygon(pad_square, -2.5, layout.dbu, cp.layer_opening)

        make_pad(origin + cp.pad_height * ey / 2,
                 cp.pad_width, cp.pad_height, ex, ey)

        port = Port('el0', origin + cp.port_width *
                    ey / 2, -ey, 'el_dc', cp.port_width)

        self.add_port(port)

        return cell


class DCPadArray(DCPad):
    params = ParamContainer(pad_array_count,
                            pad_array_pitch)

    def draw(self, cell):
        lt = self.backend
        cp = self.params
        origin, ex, _ = self.origin_ex_ey()

        for i in range(cp.pad_array_count):
            dcpad = DCPad(name=f'pad_{i}', backend=lt, **cp)
            dc_ports = dcpad.place_cell(cell, origin + cp.pad_array_pitch * i * ex)
            self.add_port(dc_ports['el0'].rename(f'el_{i}'))

        return cell
