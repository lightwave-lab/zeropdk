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
