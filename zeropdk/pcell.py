"""PCell definitions that improve upon Klayout pcells."""

import os
from copy import copy, deepcopy
from typing import Dict, List, Tuple, Any, Type, Optional
import logging
from collections.abc import Mapping, MutableMapping

import klayout.db as kdb
from zeropdk.layout.geometry import rotate90

logger = logging.getLogger(__name__)

TypeDouble = float
TypeInt = int
TypeBoolean = bool
TypeString = str
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

    def __init__(
        self,
        *,
        name,
        type=None,
        description="No description",
        default=None,
        unit=None,
        readonly=False,
        choices=None,
    ):
        self.name: str = name
        if type is None and default is not None:
            self.type = python_type(default)
        elif type is not None:
            self.type = type
        else:
            raise RuntimeError("Unkown parameter type, cannot determine from default.")

        self.description: str = description
        self.default = default
        self.unit: str = unit
        self.readonly: bool = readonly
        self.choices: List[Tuple[str, Any]] = choices

    def __repr__(self):
        return '<"{name}", type={type}, default={default}>'.format(
            name=self.name, type=self.type.__qualname__, default=str(self.default)
        )

    def __str__(self):
        return repr(self)

    def parse(self, value):
        """ Makes sure that the value is of a certain type"""
        if self.type is None:
            new_type = type(value)
            self.type = new_type
            logger.warning(
                "'{name}' type is unknown. Setting to '{typename}'".format(
                    name=self.name, typename=new_type.__qualname__
                )
            )
            return value

        elif isinstance(value, self.type):
            return value

        try:
            return self.type(value)
        except (TypeError, ValueError) as parse_exception:
            raise TypeError(
                "Cannot set '{name}' to {value}. "
                "Expected {etype}, got {type}.".format(
                    name=self.name,
                    value=repr(value),
                    etype=repr(self.type.__qualname__),
                    type=repr(type(value).__qualname__),
                )
            ) from parse_exception


class objectview(MutableMapping):
    """Basically allows us to access dictionary values as dict.x
    rather than dict['x']

    The fact that it is a MutableMapping means that it is essentially
    a writable dictionary. We recommend you only use it as read-only.

    """

    def __init__(self, d):
        self.orig_d = d

    def __getattr__(self, name):
        return self.orig_d[name]

    def __setattr__(self, name, value):
        if name in ("orig_d"):
            return super().__setattr__(name, value)
        self.orig_d[name] = value

    def __setitem__(self, name, value):
        self.orig_d[name] = value

    def __delitem__(self, name):
        del self.orig_d[name]

    def __getitem__(self, item):
        return self.orig_d[item]

    def __iter__(self):
        return self.orig_d.__iter__()

    def __len__(self):
        return self.orig_d.__len__()

    def __add__(self, other):
        new_dict = copy(self.orig_d)
        new_dict.update(other)
        return objectview(new_dict)

    def __radd__(self, other):
        return self.__add__(other)

    def __repr__(self):
        return "objectview({})".format(repr(self.orig_d))


# https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict
# Mapping is an abstract class which implements a read-only dict
class ParamContainer(Mapping):
    """Holds a dictionary-like set of parameters.
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

    _container: Dict[str, Type[PCellParameter]]
    _current_values: Dict[str, Type[PCellParameter]]

    def __init__(self, *args):
        """Two ways of initializing:
        1. ParamContainer(pc_obj), where pc_obj is another param_container
        2. ParamContainer(param1, param2, param3, ...), where param is of type
            PCellParameter
        """
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

    def add_param(self, param: Type[PCellParameter]):
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
        """ Set a parameter instead of an instance attribute."""

        protected_list = ("_container", "_current_values")
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
        self.position: Type[kdb.DPoint] = position  # Point
        self.direction: Type[kdb.DVector] = direction  # Vector
        self.type: str = port_type
        self.width: float = width

    def rename(self, new_name: str):
        self.name = new_name
        return self

    def __repr__(self):
        return f"({self.name}, {self.position})"

    def flip(self):
        # TODO refactor after introducing port type
        if self.name.startswith("el"):
            pin_length = self.width
            self.position += self.direction * pin_length

        self.direction = -self.direction

        return self

    def rotate(self, angle_deg):
        from zeropdk.layout.geometry import rotate
        from math import pi

        self.direction = rotate(self.direction, angle_deg * pi / 180)
        return self

    def draw(self, cell, layer):
        """ Draws this port on cell's layer using klayout.db"""
        if self.name.startswith("el"):
            pin_length = self.width
        else:
            # port is optical
            pin_length = min(2, self.width / 10)

        ex = self.direction

        # Place a Path around the port pointing towards its exit
        port_path = kdb.DPath(
            [
                self.position - 0.5 * pin_length * ex,
                self.position + 0.5 * pin_length * ex,
            ],
            self.width,
        )
        cell.shapes(layer).insert(port_path)

        # Place a small arrow around the tip of the port

        ey = rotate90(ex)
        port_tip = kdb.DSimplePolygon(
            [
                self.position + 0.5 * pin_length * ex,
                self.position + 0.4 * pin_length * ex + 0.1 * pin_length * ey,
                self.position + 0.4 * pin_length * ex - 0.1 * pin_length * ey,
            ]
        )
        cell.shapes(layer).insert(port_tip)
        # pin_rectangle = rectangle(self.position, self.width,
        #                           pin_length, ex, ey)
        # cell.shapes(layer).insert(pin_rectangle)

        # Place a text object annotating the name of the port
        cell.shapes(layer).insert(
            kdb.DText(
                self.name,
                kdb.DTrans(kdb.DTrans.R0, self.position.x, self.position.y),
                min(pin_length, 2),
                0,
            )
        )

        return self


def place_cell(
    parent_cell: Type[kdb.Cell],
    pcell: Type[kdb.Cell],
    ports_dict: Dict[str, Type[Port]],
    placement_origin: Type[kdb.DPoint],
    relative_to: Optional[str] = None,
    transform_into: bool = False,
):
    """Places an pya cell and return ports with updated positions
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

    ports = ports_dict
    cell = pcell

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


class PCell:
    """Programmable Cell whose layout is computed depending on given parameters."""

    # It is useful to define params and ports during class definition.
    # This way, inherited classes can inherit (and merge) these
    # properties. The logic for this can be found in __new__ method
    # below
    params: ParamContainer = ParamContainer()
    _cell: Type[kdb.Cell]

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

            # traverse the MRO of this class in reverse order,
            # since the newest class has the most up-to-date parameters
            for klass in reversed(cls.__mro__):
                if issubclass(klass, PCell):
                    new_params = new_params.merge(klass.params)
            new_params = new_params.merge(cls.params)
            obj.params = new_params

        return obj

    def __init__(self, name: str, params=None):
        self.name = name
        if params is not None:
            self.set_param(**params)

    def set_param(self, **params):
        for name, p_value in params.items():
            if name in self.params._container:
                setattr(self.params, name, p_value)
            else:
                logger.debug(
                    "Ignoring '{name}' parameter in {klass}.".format(
                        name=name, klass=self.__class__.__qualname__
                    )
                )

    def get_cell_params(self):
        """returns a *copy* of the parameter dictionary

        Returns:
            object: objectview of full parameter structure
            access with cp.name instead of cp['name']
        """
        cell_params = dict(self.params)
        return objectview(cell_params)

    def new_cell(self, layout):
        new_cell = layout.create_cell(self.name)

        return self.draw(new_cell)

    def place_cell(
        self,
        parent_cell: Type[kdb.Cell],
        placement_origin: Type[kdb.DPoint],
        relative_to: Optional[str] = None,
        transform_into: bool = False,
    ):
        """Places this pcell into parent_cell and return ports with
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

        cell, ports = self.new_cell(layout)

        return place_cell(
            parent_cell,
            cell,
            ports,
            placement_origin,
            relative_to=relative_to,
            transform_into=transform_into,
        )


def GDSCell(cell_name: str, filename: str, gds_dir: str):
    """
    Args:
        cell_name: cell within that file.
        filename: is the gds file name.
        gds_dir: where to look for file

    Returns:
        (class) a GDS_cell_base class that can be inherited
    """

    assert gds_dir is not None

    class GDS_cell_base(PCell):
        """ Imports a gds file and places it."""

        _cell_cache = {}

        def __init__(self, name=cell_name, params=None):
            PCell.__init__(self, name=name, params=params)

        def get_gds_cell(self, layout):
            filepath = os.path.join(gds_dir, filename)

            # Attempt to read from cache first
            if (cell_name, filepath, layout) in self._cell_cache:
                gdscell = self._cell_cache[(cell_name, filepath, layout)]
            else:
                gdscell = layout.read_cell(cell_name, filepath)
            self._cell_cache[(cell_name, filepath, layout)] = gdscell
            return gdscell

        def draw_gds_cell(self, cell):
            logger.warning("Using default draw_gds_cell method in %s.", self.name)
            layout = cell.layout()
            gdscell = self.get_gds_cell(layout)

            origin = kdb.DPoint(0, 0)
            cell.insert_cell(gdscell, origin, 0)
            return cell

        def draw(self, cell):
            # Providing default implementation here,
            # But recommend you override it in child classes.
            logger.warning("Using default draw method in %s.", self.name)
            return self.draw_gds_cell(cell), {}
            # raise NotImplementedError()

    return GDS_cell_base


def port_to_pin_helper(
    ports_list: List[Type[Port]], cell: Type[kdb.Cell], layerPinRec: Type[kdb.LayerInfo]
):
    """ Draws port shapes for visual help in KLayout. """
    # Create the pins, as short paths:
    # from siepic_tools.config import PIN_LENGTH
    PIN_LENGTH = 100
    dbu = cell.layout().dbu

    for port in ports_list:
        if port.name.startswith("el"):
            pin_length = port.width
        else:
            pin_length = PIN_LENGTH * dbu

        port_position_i = port.position.to_itype(dbu)
        cell.shapes(layerPinRec).insert(
            kdb.DPath(
                [
                    port.position - 0.5 * pin_length * port.direction,
                    port.position + 0.5 * pin_length * port.direction,
                ],
                port.width,
            ).to_itype(dbu)
        )
        cell.shapes(layerPinRec).insert(
            kdb.Text(port.name, kdb.Trans(kdb.Trans.R0, port_position_i.x, port_position_i.y))
        ).text_size = (2 / dbu)
