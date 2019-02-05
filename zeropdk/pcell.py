import os
from typing import Dict, List, Tuple, Any, NewType

TypeDouble = NewType('TypeDouble', float)
TypeInt = NewType('TypeInt', int)


class PCellParameter:
    """
    Defines a parameter
      name         -> the short name of the parameter
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
            type=None,
            description="No description",
            default=None,
            unit=None,
            readonly=False,
            choices=None):
        self.type = type
        self.description: str = description
        self.default = default
        self.unit: str = unit
        self.readonly: bool = readonly
        self.choices: List[Tuple[str, Any]] = choices


class PCell:

    params: Dict[str, PCellParameter] = {}

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
            parent_params = dict()
            for klass in cls.__mro__:
                if issubclass(klass, PCell):
                    parent_params.update(klass.params)
            obj.params.update(parent_params)

        return obj

    def __init__(self, *, name: str, backend: str, **params):
        self.name = name
        self.backend = backend
        self.set_param(**params)

    def set_param(self, **params):
        for name, value in params.items():
            if name not in self.params:
                raise RuntimeError('{name} is an invalid param.'.format(name=name))
            self.params[name] = value


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

        def new_cell(self, layout):
            # Here, the hierarchy is duplicated
            cell = layout.create_cell(self.name)
            return self.draw(cell)

        def draw(self, cell, params=None):
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
