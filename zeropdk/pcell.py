import os
from copy import copy, deepcopy
from typing import Dict, List, Tuple, Any
import logging
from collections.abc import Mapping

import klayout.db as kdb

logger = logging.getLogger()

TypeDouble = float
TypeInt = int
TypeList = list
TypePoint = kdb.DPoint
TypeVector = kdb.DVector
TypeLayer = kdb.LayerInfo

# I like using 'type' as argument names, but that conflicts with
# python's keyword type
python_type = type


class PCellParameter:
    """
    Defines a parameter
      name         -> the short name of the parameter (required)
      type         -> the type of the parameter
      description  -> the description text
    named parameters
      hidden      -> (boolean) true, if the parameter is not shown in the dialog
      readonly    -> (boolean) true, if the parameter cannot be edited
      unit        -> the unit string
      default     -> the default value
      choices     -> ([ [ d, v ], ...) choice descriptions/value for choice type
    """
    def __init__(self, *,
            name,
            type=None,
            description="No description",
            default=None,
            unit=None,
            readonly=False,
            choices=None):
        self.name: str = name
        if type is None and default is not None:
            self.type = python_type(default)
        else:
            self.type = type
        self.description: str = description
        self.default = default
        self.unit: str = unit
        self.readonly: bool = readonly
        self.choices: List[Tuple[str, Any]] = choices

    def parse(self, value):
        ''' Makes sure that the value is of a certain type'''
        if self.type is None:
            new_type = type(value)
            self.type = new_type
            logger.warning(
                "'{name}' type is unknown. Setting to '{typename}'".format(
                    name=self.name, typename=new_type.__qualname__))
            return value

        elif isinstance(value, self.type):
            return value

        try:
            return self.type(value)
        except (TypeError, ValueError):
            raise TypeError(
                "Cannot set '{name}' to {value}. "
                "Expected {etype}, got {type}.".format(
                    name=self.name, value=repr(value),
                    etype=repr(self.type.__qualname__),
                    type=repr(type(value).__qualname__)))


# https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict
# Mapping is an abstract class which implements a read-only dict
class ParamContainer(Mapping):
    """ Holds a dictionary-like set of parameters.
    The idea is to use them as such:

    >>> pc = ParamContainer()
    >>> pc.add_param(PCellParameter(name='orange', default=1))
    >>> print(pc.orange)
    1
    >>> pc.orange = 2
    >>> print(pc.orange)
    2
    >>> pc.orange = 'blah'
    TypeError: Cannot set orange to string
    """

    _container = None
    _current_values = None

    def __init__(self, *args):
        self._container = dict()
        self._current_values = dict()

        if len(args) == 1 and isinstance(args[0], ParamContainer):
            param_container = args[0]
            self._container = copy(param_container._container)
            self._current_values = copy(param_container._current_values)
        elif len(args) > 0:
            for arg in args:
                param = arg  # TODO: check type
                self.add_param(param)

    def add_param(self, param: PCellParameter):
        self._container[param.name] = param

        # delete from current values if overwriting parameter
        if param.name in self._current_values:
            del self._current_values[param.name]
        return param

    def __getattr__(self, name):
        try:
            value = self._current_values[name]
        except KeyError:
            value = self._container[name].default
            self._current_values[name] = value

        return value

    def __setattr__(self, name, new_value):
        ''' Set a parameter instead of an instance attribute.'''

        protected_list = ('_container', '_current_values')
        if name in protected_list:
            return super().__setattr__(name, new_value)
        else:
            param_def = self._container[name]
            try:
                parsed_value = param_def.parse(new_value)
            except TypeError:
                raise
            self._current_values[name] = parsed_value

    def merge(self, other):
        if not isinstance(other, ParamContainer):
            raise TypeError("Object must be a ParamContainer")

        # Make a copy of self
        new_params = ParamContainer(self)
        # Merge parameters, favoring other's values
        for p in other._container.values():
            new_params.add_param(p)
        new_params._current_values.update(other._current_values)
        return new_params

    # Methods necessary to override a read-only dict():
    def __getitem__(self, key):
        return self.__getattr__(key)

    def __iter__(self):
        values_dict = {p.name: p.default for p in self._container.values()}
        values_dict.update(self._current_values)
        return iter(values_dict)

    def __len__(self):
        return len(self._container)


class Port(object):
    """ Defines a port object """

    def __init__(self, name, position, direction, width, port_type=None):
        self.name: str = name
        self.position = position  # Point
        self.direction = direction  # Vector
        self.type: str = port_type
        self.width: float = width

    def rename(self, new_name):
        self.name = new_name
        return self

    def __repr__(self):
        return f"({self.name}, {self.position})"

    def draw(self, cell, layer):
        ''' Draws this port on cell's layer using klayout.db'''
        if self.name.startswith("el"):
            pin_length = self.width
        else:
            # port is optical
            pin_length = max(2, self.width / 10)

        ex = self.direction

        # Place a Path around the port pointing towards its exit
        port_path = kdb.DPath([self.position - 0.5 * pin_length * ex,
                       self.position + 0.5 * pin_length * ex], self.width)
        cell.shapes(layer).insert(port_path)
        # pin_rectangle = rectangle(self.position, self.width,
        #                           pin_length, ex, ey)
        # cell.shapes(layer).insert(pin_rectangle)

        # Place a text object annotating the name of the port
        cell.shapes(layer).insert(kdb.DText(self.name, kdb.DTrans(
            kdb.DTrans.R0, self.position.x, self.position.y), min(pin_length, 20), 0))

        return self


class PCell:

    params: ParamContainer = ParamContainer()
    ports: Dict[str, Port] = {}
    _cell: kdb.Cell = None

    def draw(self, cell):
        raise NotImplementedError()

    def __new__(cls, *args, **kwargs):
        # The purpose of this method is to make sure that the parameters
        # dictionary of the class is merged with the parameter dicts
        # of the classes from which this inherits.
        # For now, accept conflicts. Be cafeful!

        obj = super().__new__(cls)

        # only consider subclasses
        if cls != PCell and issubclass(cls, PCell):
            # First, collect all parent params, assuming they are
            # all disjoint
            new_params = ParamContainer()
            for klass in cls.__mro__:
                if issubclass(klass, PCell):
                    new_params = new_params.merge(klass.params)
            new_params = new_params.merge(cls.params)
            obj.params = new_params
            obj.ports = copy(cls.ports)

        return obj

    def __init__(self, *, name: str, **params):
        self.name = name
        self.set_param(**params)

    def set_param(self, **params):
        for name, p_value in params.items():
            if name in self.params:
                setattr(self.params, name, p_value)
            else:
                logger.debug("Ignoring '{name}' parameter in {klass}."
                    .format(name=name, klass=self.__class__.__qualname__))

    def new_cell(self, layout):
        # A cell is only created once per instance.
        if self._cell is not None:
            return self._cell

        self._cell = layout.create_cell(self.name)
        return self.draw(self._cell)

    def add_port(self, port: Port):
        self.ports[port.name] = port

    @property
    def cp(self):
        ''' Alias for self.params

            Rationale:
                - type pcell.cp instead of pcell.params
                - access with cp.name instead of cp['name']
        '''
        return self.params

    def place_cell(self, parent_cell, placement_origin, params=None,
                   relative_to=None, transform_into=False):
        """ Places this pcell into parent_cell and return ports with
            updated position and orientation.
        Args:
            parent_cell: cell to place into
            placement_origin: pya.Point object to be used as origin
            relative_to: port name
                the cell is placed so that the port is located at placement_origin
            transform_into:
                if used with relative_into, transform the cell's coordinate system
                so that its origin is in the given port.

        Returns:
            ports(dict):
                key:port.name,
                value: geometry.Port with positions relative to parent_cell's origin
        """
        layout = parent_cell.layout()
        cell = self.new_cell(layout)
        ports = self.ports

        # Compute new placement origin and port_offset

        # offset = kdb.DVector(0, 0)
        port_offset = placement_origin
        if relative_to is not None:
            offset = ports[relative_to].position
            port_offset = placement_origin - offset
            if transform_into:
                # print(type(pcell))
                offset_transform = kdb.DTrans(kdb.DTrans.R0, -offset)
                for instance in cell.each_inst():
                    instance.transform(offset_transform)
                cell.transform_into(offset_transform)
            else:
                placement_origin = placement_origin - offset

        parent_cell.insert_cell(cell, placement_origin, 0)

        new_ports = deepcopy(ports)
        for port in new_ports.values():
            port.position += port_offset

        return new_ports


def GDSCell(cell_name, filename, gds_dir):
    '''
        Args:
            cell_name: cell within that file.
            filename: is the gds file name.
            gds_dir: where to look for file

        Returns:
            (class) a GDS_cell_base class that can be inherited
    '''

    assert gds_dir is not None

    cell_cache = {}

    class GDS_cell_base(PCell):
        """ Imports a gds file and places it."""

        def __init__(self, name=cell_name, **params):
            super().__init__(name=name, **params)

        def draw(self, cell):
            layout = cell.layout()
            filepath = os.path.join(gds_dir, filename)

            # Attempt to read from cache first
            if (cell_name, filepath) in cell_cache:
                gdscell = cell_cache[(cell_name, filepath)]
            else:
                gdscell = layout.read_cell(cell_name, filepath)
            cell_cache[(cell_name, filepath)] = gdscell

            origin = kdb.DPoint(0, 0)
            angle = 0

            cell.insert_cell(gdscell, origin, angle)
            return cell

    return GDS_cell_base


from zeropdk.layout.geometry import rotate, rotate90
from math import pi


class CellWithPosition(PCell):
    ''' handles the angle_ex parameter '''

    params = ParamContainer(PCellParameter(name="angle_ex",
                                           type=TypeDouble,
                                           description="Placement Angle (0, 90, ..)",
                                           default=0))

    # def initialize_default_params(self):
    #     self.define_param("angle_ex", self.TypeDouble,
    #                       "Placement Angle (0, 90, ..)", default=0)

    def origin_ex_ey(self, params=None, multiple_of_90=False):  # pylint: disable=unused-argument
        EX = kdb.DVector(1, 0)
        cp = self.parse_param_args(params)
        origin = kdb.DPoint(0, 0)
        if multiple_of_90:
            if cp.angle_ex % 90 != 0:
                raise RuntimeError("Specify an angle multiple of 90 degrees")
        ex = rotate(EX, cp.angle_ex * pi / 180)
        ey = rotate90(ex)
        return origin, ex, ey


def place_cell(parent_cell, pcell, ports_dict, placement_origin, relative_to=None, transform_into=False):
    """ Places an pya cell and return ports with updated positions
    Args:
        parent_cell: cell to place into
        pcell, ports_dict: result of KLayoutPCell.pcell call
        placement_origin: pya.Point object to be used as origin
        relative_to: port name
            the cell is placed so that the port is located at placement_origin
        transform_into:
            if used with relative_into, transform the cell's coordinate system
            so that its origin is in the given port.

    Returns:
        ports(dict): key:port.name, value: geometry.Port with positions relative to parent_cell's origin
    """
    offset = kdb.DVector(0, 0)
    port_offset = placement_origin
    if relative_to is not None:
        offset = ports_dict[relative_to].position
        port_offset = placement_origin - offset
        if transform_into:
            # print(type(pcell))
            offset_transform = kdb.DTrans(kdb.DTrans.R0, -offset)
            for instance in pcell.each_inst():
                instance.transform(offset_transform)
            pcell.transform_into(offset_transform)
        else:
            placement_origin = placement_origin - offset

    transformation = kdb.DTrans(kdb.Trans.R0, placement_origin)
    instance = kdb.DCellInstArray(pcell.cell_index(), transformation)
    parent_cell.insert(instance)
    for port in ports_dict.values():
        port.position += port_offset

    return ports_dict


def port_to_pin_helper(ports_list, cell, layerPinRec):
    ''' Draws port shapes for visual help in KLayout. '''
    # Create the pins, as short paths:
    from siepic_tools.config import PIN_LENGTH
    dbu = cell.layout().dbu

    for port in ports_list:
        if port.name.startswith("el"):
            pin_length = port.width
        else:
            pin_length = PIN_LENGTH * dbu

        port_position_i = port.position.to_itype(dbu)
        cell.shapes(layerPinRec).insert(
            kdb.DPath([port.position - 0.5 * pin_length * port.direction,
                       port.position + 0.5 * pin_length * port.direction], port.width).to_itype(dbu))
        cell.shapes(layerPinRec).insert(kdb.Text(port.name, kdb.Trans(
            kdb.Trans.R0, port_position_i.x, port_position_i.y))).text_size = 2 / dbu
