import pytest
from ..context import zeropdk  # noqa

import klayout.db as kdb
from zeropdk.layout.cache import CACHE_PROP_ID

def test_metadata():
    save_options = kdb.SaveLayoutOptions()
    save_options.gds2_write_file_properties = True
    save_options.gds2_write_cell_properties = True
    load_options = kdb.LoadLayoutOptions()
    load_options.properties_enabled = True
    layout = kdb.Layout()
    TOP = layout.create_cell("TOP")
    TOP.set_property("key", "test1")
    TOP.set_property(123, "test2")
    layout.write("tests/tmp/test_metadata.gds", save_options)
    layout2 = kdb.Layout()
    layout2.read("tests/tmp/test_metadata.gds", load_options)
    TOP = layout2.top_cell()
    assert TOP.property(123) == "test2"
    assert TOP.property("key") == "test1"

def test_cache_metadata():
    save_options = kdb.SaveLayoutOptions()
    save_options.gds2_write_file_properties = True
    layout = kdb.Layout()
    layout.set_property(CACHE_PROP_ID, "test1")
    layout.write("tests/tmp/test_cache_metadata.gds", save_options)
    layout2 = kdb.Layout()
    assert layout2.property(CACHE_PROP_ID) is None
    layout2.set_property(CACHE_PROP_ID, "test2")
    assert layout2.property(CACHE_PROP_ID) == "test2"
    layout2.read("tests/tmp/test_cache_metadata.gds")
    assert layout2.property(CACHE_PROP_ID) == "test1"