import os
from copy import copy
from typing import Dict, List, Tuple, Any, NewType
import logging
from collections.abc import Mapping

logger = logging.getLogger()

TypeDouble = NewType('TypeDouble', float)
TypeInt = NewType('TypeInt', int)
TypeList = NewType('TypeList', List)
TypePoint = NewType('TypePoint', Any)
TypeVector = NewType('TypeVector', Any)
TypeLayer = str

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
        except ValueError:
            raise TypeError(
                "Cannot set '{name}' to {value}".format(
                    name=self.name, value=repr(value)))


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
        values_dict = {p.name: p.value for p in self._container.values()}
        values_dict.update(self._current_values)
        return iter(values_dict)

    def __len__(self):
        return len(self._container)


class Port(object):
    """ Defines a port object """

    def __init__(self, name, position, direction, port_type, width=None):
        self.name: str = name
        self.position = position  # Point
        self.direction = direction  # Vector
        self.type: str = port_type
        self.width: float = width

    def rename(self, new_name):
        self.name = new_name
        return self

    def __repr__(self):
        return f"{self.name}, {self.position}"


class PCell:

    params: ParamContainer = ParamContainer()
    ports: Dict[str, Port] = {}

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

    def __init__(self, *, name: str, backend: str, **params):
        self.name = name
        self.backend = backend
        self.set_param(**params)

    def set_param(self, **params):
        for name, value in params.items():
            if name not in self.params:
                raise RuntimeError("'{name}' is an invalid param.".format(name=name))
            setattr(self.params, name, value)

    def new_cell(self, layout):
        # Here, the hierarchy is duplicated
        cell = layout.create_cell(self.name)
        return self.draw(cell)

    def draw(self, cell):
        raise NotImplementedError()

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


def GDSCell(backend, cell_name, filename, gds_dir):
    '''
        Args:
            backend: layout backend
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
            lt = self.backend
            layout = cell.layout()
            filepath = os.path.join(gds_dir, filename)

            # Attempt to read from cache first
            if (cell_name, filepath) in cell_cache:
                gdscell = cell_cache[(cell_name, filepath)]
            else:
                gdscell = layout.read_cell(cell_name, filepath)
            cell_cache[(cell_name, filepath)] = gdscell

            origin = lt.Point(0, 0)
            angle = 0

            cell.insert_cell(gdscell, origin, angle)
            return cell

    return GDS_cell_base
