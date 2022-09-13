from functools import wraps
from typing import Type
import klayout.db as kdb

from . import point, cell, layout, polygon  # noqa

cell.patch_cell()
layout.patch_layout()
point.patch_points()
polygon.patch_polygon()
