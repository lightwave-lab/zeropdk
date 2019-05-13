from klayout.db import Layout


def layout_read_cell(layout, cell_name, filepath):
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
