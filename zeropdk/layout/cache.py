import klayout.db as pya
import os
from hashlib import sha256
import inspect
import pickle
from copy import deepcopy

layer_map_dict = dict()
debug = True
cache_dir = os.path.join(os.getcwd(), 'cache')


def produce_hash(self):
    from zeropdk.pcell import PCell

    # copy source code of class and all its ancestors
    source_code = "".join(
        [inspect.getsource(klass) for klass in self.__class__.__mro__ if issubclass(klass, PCell)])

    diff_params = dict(self.params)

    long_hash_pcell = sha256((source_code +
                              str(diff_params) +
                              self.name).encode()).hexdigest()
    short_hash_pcell = long_hash_pcell[0:7]
    return short_hash_pcell


def read_layout(layout, gds_filename):
    ''' Reads the layout in the gds file and imports all cells into
    layout without overwriting existing cells.'''
    global layer_map_dict
    load_options = pya.LoadLayoutOptions()
    load_options.text_enabled = True
    load_options.set_layer_map(layer_map_dict[layout], True)

    # store and take away the cell names of all cells read so far
    # (by setting the cell name to "" the cells basically become invisible for
    # the following read)
    # take out the pcells
    cell_list = [cell for cell in layout.each_cell()]
    cell_indices = {cell.name: cell.cell_index() for cell in cell_list}
    for i in cell_indices.values():
        layout.rename_cell(i, "")

    lmap = layout.read(gds_filename, load_options)
    # in the new layout, get all cells names
    cell_names2 = [(cell.cell_index(), cell.name)
                   for cell in layout.each_cell()]

    # make those cells point to older cells
    prune_cells_indices = []
    for i_duplicate, name_cached_cell in cell_names2:
        if name_cached_cell in cell_indices.keys():
            if name_cached_cell.startswith('cache_'):
                for parent_inst_array in layout.cell(i_duplicate).each_parent_inst():
                    cell_instance = parent_inst_array.child_inst()
                    cell_instance.cell = layout.cell(
                        cell_indices[name_cached_cell])
                prune_cells_indices.append(i_duplicate)
            else:
                # print('RENAME', name_cached_cell)
                k = 1
                while (name_cached_cell + f"_{k}") in cell_indices.keys():
                    k += 1
                layout.rename_cell(i_duplicate, name_cached_cell + f"_{k}")

    for i_pruned in prune_cells_indices:
        # print('deleting cell', layout.cell(i_pruned).name)
        layout.prune_cell(i_pruned, -1)

    # every conflict should have been caught above
    for name, i in cell_indices.items():
        layout.rename_cell(i, name)

    layer_map_dict[layout] = lmap
    return lmap


def cache_cell(cls, cache_dir=cache_dir):
    """ Caches results of pcell call to save build time.

    First, it computes a hash based on:
        1. the source code of the class and its bases.
        2. the non-default parameter with which the pcell method is called

    Second, it saves a cell with name cache_HASH in cache_HASH.gds inside
    the cache folder. The port list and position is also saved in cache_HASH.klayout.pkl,
    and it is a pickle of the ports dictionary.

    Third, if wraps the pcell method so it loads the cached cell and cached port
    positions instead of recalculating everything.

    Warnings:
        - The name of the cell is not in the hash, so multiple cells that use
        the same instantiation parameters but different names will have the
        same underlying cell instance in the layout.
        - If the cell contents depend on something other than the contents
        of the hash described above, for example an external .gds file, any
        external change will not be seen by the caching algorithm. You have
        to manually delete the corresponding cache file so it get updated
        in the mask.

    Use as a decorator:

        @cache_cell
        class MyCell(PCell):
            pass
    """

    activated = True
    if activated:
        # decorate draw
        def cache_decorator(draw):
            def wrapper_draw(self, cell):
                global layer_map_dict
                layout = cell.layout()
                try:
                    layer_map_dict[layout]
                except KeyError:
                    layer_map_dict[layout] = pya.LayerMap()

                short_hash_pcell = produce_hash(self)

                # cache paths
                cache_fname = f'cache_{self.__class__.__qualname__}_{short_hash_pcell}'
                cache_fname_gds = cache_fname + '.gds'
                cache_fname_pkl = cache_fname + '.klayout.pkl'

                os.makedirs(cache_dir, mode=0o775, exist_ok=True)

                cache_fpath_gds = os.path.join(cache_dir, cache_fname_gds)
                cache_fpath_pkl = os.path.join(cache_dir, cache_fname_pkl)

                if os.path.isfile(cache_fpath_gds) and os.path.isfile(cache_fpath_pkl):
                    with open(cache_fpath_pkl, 'rb') as file:
                        ports, read_short_hash_pcell, cellname = pickle.load(file)
                    if debug:
                        print(f"Reading from cache: {cache_fname}: {cellname}, {ports}")
                    else:
                        print('r', end='', flush=True)
                    if not layout.has_cell(cache_fname):
                        read_layout(layout, cache_fpath_gds)
                    retrieved_cell = layout.cell(cache_fname)
                    cell.insert(pya.DCellInstArray(retrieved_cell.cell_index(),
                                                   pya.DTrans(pya.DTrans.R0, pya.DPoint(0, 0))))
                    self.ports = ports
                    # cell.move_tree(retrieved_cell)
                else:
                    if layout.has_cell(cache_fname):
                        print(f"WARNING: {cache_fname_gds} does not exist but {cache_fname} is in layout.")

                    # populating .gds and .pkl
                    empty_layout = pya.Layout()
                    empty_cell = empty_layout.create_cell(cell.name)
                    filled_cell = draw(self, empty_cell)
                    ports = deepcopy(self.ports)

                    if debug:
                        print(f"Writing to cache: {cache_fname}: {filled_cell.name}, {ports}")
                    else:
                        print('w', end='', flush=True)

                    cellname, filled_cell.name = filled_cell.name, cache_fname
                    filled_cell.write(cache_fpath_gds)
                    with open(cache_fpath_pkl, 'wb') as file:
                        pickle.dump((ports, short_hash_pcell, cellname), file)

                    assert not layout.has_cell(cache_fname)

                    read_layout(layout, cache_fpath_gds)

                    retrieved_cell = layout.cell(cache_fname)
                    cell.insert(pya.DCellInstArray(retrieved_cell.cell_index(),
                                                   pya.DTrans(pya.DTrans.R0, pya.DPoint(0, 0))))

                return cell
            return wrapper_draw
        if hasattr(cls, 'draw') and cls.draw.__name__ != 'wrapper_draw':
            setattr(cls, 'draw', cache_decorator(cls.draw))
    return cls
