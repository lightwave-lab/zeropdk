from typing import Type
from klayout.db import Layout


def layout_read_cell(layout: Type[Layout], cell_name: str, filepath: str):
    """Imports a cell from a file into current layout.

    layout [pya.Layout]: layout to insert cell into
    cell_name [str]: cell name from the file in filepath
    filepath [str]: location of layout file you want to import

    If the name already exists in the current layout, klayout will
    create a new one based on its internal rules for naming
    collision: name$1, name$2, ...
    """

    # BUG loading this file twice segfaults klayout
    layout2 = Layout()
    layout2.read(filepath)
    gdscell2 = layout2.cell(cell_name)
    gdscell = layout.create_cell(cell_name)
    gdscell.copy_tree(gdscell2)
    del gdscell2
    del layout2
    return gdscell


Layout.read_cell = layout_read_cell
