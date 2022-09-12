from typing import Union
import klayout.db as kdb

GeneralLayer = Union[kdb.LayerInfo, str, int]
PointLike = Union[kdb.DVector, kdb.DPoint]
