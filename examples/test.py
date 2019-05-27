from dataclasses import dataclass, field

# see manual for dataclasses in https://docs.python.org/3/library/dataclasses.html
# dataclasses only exist in 3.7, with a possible backport for 3.6
# I am aware of this issue but at the time of implementation I am not
# caring much about it. If necessary, someone should refactor the code
# below. -- TFL


@dataclass
class Color:
    hue: int
    lightness: float
    saturation: float = 1.0


# dark_orange = Color(hue=23, saturation=1.00, lightness=0.5)
dark_orange = Color(hue=23, lightness=0.5)
print(dark_orange)
print(dark_orange.hue)

from zeropdk.pcell import Port
from typing import Dict, List
from klayout.db import DPoint


@dataclass
class PCellMetadata:
    stuff: List = None
    ports: Dict[str, Port] = field(default_factory=dict)


x = PCellMetadata(ports={"a": Port("a", DPoint(1, 2), DPoint(1, 0), 10)})
print(x)
