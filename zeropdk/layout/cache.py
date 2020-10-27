"""Caching algorithms for pcells."""
import os
import inspect
import pickle
import logging
from hashlib import sha256
from functools import partial, wraps
from typing import Type, Any, Union, Callable, Dict

import klayout.db as pya
from zeropdk.pcell import PCell

logger = logging.getLogger(__name__)
layer_map_dict: Dict[Type[pya.Layout], Type[pya.LayerMap]] = dict()
CACHE_ACTIVATED = os.environ.get("ZEROPDK_CACHE_ACTIVATED", "true") == "true"
CACHE_DIR = os.environ.get("ZEROPDK_CACHE_DIR", os.path.join(os.getcwd(), "cache"))


def produce_hash(self: Type[PCell], extra: Any = None) -> str:
    """Produces a hash of a PCell instance based on:
    1. the source code of the class and its bases.
    2. the non-default parameter with which the pcell method is called
    3. the name of the pcell
    """
    # copy source code of class and all its ancestors
    source_code = "".join(
        [inspect.getsource(klass) for klass in self.__class__.__mro__ if issubclass(klass, PCell)]
    )

    diff_params = dict(self.params)
    # str(diff_params) calls __repr__ in inner values, instead of __str__ ()
    # therefore it would fail for instances without readable __repr__ methods
    str_diff_params = "{%s}" % ", ".join("%r: %s" % p for p in diff_params.items())

    long_hash_pcell = sha256(
        (source_code + str_diff_params + self.name + str(extra)).encode()
    ).hexdigest()
    short_hash_pcell = long_hash_pcell[0:7]
    return short_hash_pcell


def read_layout(layout: Type[pya.Layout], gds_filename: str, disambiguation_name: str = ""):
    """Reads the layout in the gds file and imports all cells into
    layout without overwriting existing cells.
    """
    load_options = pya.LoadLayoutOptions()
    load_options.text_enabled = True
    load_options.set_layer_map(layer_map_dict[layout], True)

    # store and take away the cell names of all cells read so far
    # (by setting the cell name to "" the cells basically become invisible for
    # the following read)
    # take out the pcells
    cell_list = [cell for cell in layout.each_cell()]
    cell_indices = {cell.name: cell.cell_index() for cell in cell_list}

    # this assumes that there are no duplicate names, which is true in gds (let's assert)
    assert len(cell_list) == len(
        cell_indices
    ), "There is a duplicate cell name in the current layout"
    for i in cell_indices.values():
        layout.rename_cell(i, "")

    # Read the new gds_filename
    lmap = layout.read(gds_filename, load_options)

    # in the new layout, get all cell names, assuming, again, that there are no duplicates
    cell_names2 = [(cell.cell_index(), cell.name) for cell in layout.each_cell()]

    # make those cells point to older cells if they are duplicate:
    # - if it is a cached cell, reuse the cell in the layout
    # - if it is not, then disambiguate by using the disambiguation_name
    # - if there is a duplicate even with the disambiguated name, add a counter

    if disambiguation_name != "":
        disambiguation_name = (
            "_" + disambiguation_name
        )  # new cell name will be duplicate_name_disambiguation_name

    prune_cells_indices = []
    used_cell_names = list(cell_indices.keys())
    for i_duplicate, name_cached_cell in cell_names2:
        if name_cached_cell in cell_indices.keys():
            if name_cached_cell.startswith("cache_"):
                for parent_inst_array in layout.cell(i_duplicate).each_parent_inst():
                    cell_instance = parent_inst_array.child_inst()
                    cell_instance.cell = layout.cell(cell_indices[name_cached_cell])
                prune_cells_indices.append(i_duplicate)
            elif name_cached_cell + disambiguation_name not in used_cell_names:
                layout.rename_cell(i_duplicate, name_cached_cell + disambiguation_name)
                used_cell_names.append(name_cached_cell + disambiguation_name)
            else:
                k = 1
                while (name_cached_cell + disambiguation_name + f"_{k}") in used_cell_names:
                    k += 1
                layout.rename_cell(i_duplicate, name_cached_cell + disambiguation_name + f"_{k}")
                used_cell_names.append(name_cached_cell + disambiguation_name + f"_{k}")

    for i_pruned in prune_cells_indices:
        logger.debug("deleting cell " + layout.cell(i_pruned).name)
        layout.prune_cell(i_pruned, -1)

    # every conflict should have been caught above
    for name, cell_index in cell_indices.items():
        layout.rename_cell(cell_index, name)

    layer_map_dict[layout] = lmap
    return lmap


def cache_cell(
    cls: Type[PCell] = None, *, extra_hash: Any = None, cache_dir: str = CACHE_DIR
) -> Union[Type[PCell], Callable]:
    """Caches results of pcell call to save build time.

    First, it computes a hash based on:
        1. the source code of the class and its bases.
        2. the non-default parameter with which the pcell method is called
        3. the name of the pcell

    Second, it saves a cell with name cache_HASH in cache_HASH.gds inside
    the cache folder. The port list and position is also saved in cache_HASH.klayout.pkl,
    and it is a pickle of the ports dictionary.

    Third, if wraps the pcell method so it loads the cached cell and cached port
    positions instead of recalculating everything.

    Warnings:
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

    if cls is None:
        # tip taken from https://pybit.es/decorator-optional-argument.html
        return partial(cache_cell, extra_hash=extra_hash, cache_dir=cache_dir)

    if not CACHE_ACTIVATED:
        return cls

    # decorate draw
    def cache_decorator(draw):
        @wraps(draw)
        def wrapper_draw(self, cell):
            layout = cell.layout()
            try:
                layer_map_dict[layout]
            except KeyError:
                layer_map_dict[layout] = pya.LayerMap()

            # Adding the dbu of the layout in the hash (bit us in the butt last time)
            short_hash_pcell = produce_hash(self, extra=(layout.dbu, extra_hash))

            # cache paths
            cache_fname = f"cache_{self.__class__.__qualname__}_{short_hash_pcell}"
            cache_fname_gds = cache_fname + ".gds"
            cache_fname_pkl = cache_fname + ".klayout.pkl"

            os.makedirs(cache_dir, mode=0o775, exist_ok=True)

            cache_fpath_gds = os.path.join(cache_dir, cache_fname_gds)
            cache_fpath_pkl = os.path.join(cache_dir, cache_fname_pkl)

            if os.path.isfile(cache_fpath_gds) and os.path.isfile(cache_fpath_pkl):
                with open(cache_fpath_pkl, "rb") as file:
                    ports, read_short_hash_pcell, cellname = pickle.load(
                        file
                    )  # pylint: disable=unused-variable

                logger.debug(f"Reading from cache: {cache_fname}: {cellname}, {ports}")
                print("r", end="", flush=True)
                if not layout.has_cell(cache_fname):
                    read_layout(layout, cache_fpath_gds, disambiguation_name=cellname)
                retrieved_cell = layout.cell(cache_fname)
                cell.insert(
                    pya.DCellInstArray(
                        retrieved_cell.cell_index(),
                        pya.DTrans(pya.DTrans.R0, pya.DPoint(0, 0)),
                    )
                )
                # cell.move_tree(retrieved_cell)
            else:
                if layout.has_cell(cache_fname):
                    logger.warning(
                        f"WARNING: {cache_fname_gds} does not exist but {cache_fname} is in layout."
                    )

                # populating .gds and .pkl
                empty_layout = pya.Layout()
                empty_layout.dbu = layout.dbu
                empty_cell = empty_layout.create_cell(cell.name)
                filled_cell, ports = draw(self, empty_cell)

                logger.debug(f"Writing to cache: {cache_fname}: {filled_cell.name}, {ports}")
                print("w", end="", flush=True)

                cellname, filled_cell.name = filled_cell.name, cache_fname
                # There can be duplicate cell names in subcells here.
                filled_cell.write(cache_fpath_gds)
                with open(cache_fpath_pkl, "wb") as file:
                    pickle.dump((ports, short_hash_pcell, cellname), file)

                # Make sure we delete the empty_layout to not grow
                # helps debug
                layer_map_dict.pop(empty_layout, None)
                del empty_layout
                assert not layout.has_cell(cache_fname)

                read_layout(layout, cache_fpath_gds, disambiguation_name=cellname)
                retrieved_cell = layout.cell(cache_fname)
                cell.insert(
                    pya.DCellInstArray(
                        retrieved_cell.cell_index(),
                        pya.DTrans(pya.DTrans.R0, pya.DPoint(0, 0)),
                    )
                )

            return cell, ports

        return wrapper_draw

    if hasattr(cls, "draw") and cls.draw.__name__ != "wrapper_draw":
        setattr(cls, "draw", cache_decorator(cls.draw))

    return cls
