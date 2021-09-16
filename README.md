# ZeroPDK

This is a pure-python PDK factory that enables klayout scripted layout. It assists in photonic integrated circuit layout, which relies on having specialized curved waveguides and non-square-corner shapes.

## Installation

This package is heavily based on python's [klayout package](https://github.com/klayout/klayout), still in beta version as of this writing (Jul 2019). 

Installation with pip (virtual environment is highly recommended):

```bash
pip install zeropdk
```

Installation from source:

```bash
python setup.py install
```

## Features

### KLayout extension

By importing zeropdk, klayout is patched with a few useful functionalities. For example:

```python
import klayout.db as kdb
import zeropdk

layout = kdb.Layout()
plogo = layout.read_cell(cell_name='princeton_logo', filepath='gdslibrary/princeton_logo_simple.gds')

# plogo is a cell in the current layout. It can be inserted in the top cell.
```

### Easy technology layers definition

Based on a KLayout's layout properties file (.lyp) containing layer definitions, it is easy to import and use all layers. For example:

```python

from zeropdk import Tech
lyp_path = "examples/EBeam.lyp"
EBeam = Tech.load_from_xml(lyp_path)
layerM1 = EBeam.layers["M1"]
print(layerM1, type(layerM1))  # M1 (41/0) <class 'klayout.dbcore.LayerInfo'>
```

The file above belongs to a project called [SiEPIC EBeam PDK](https://github.com/lukasc-ubc/SiEPIC_EBeam_PDK), used in passive silicon photonic foundries.

### Advanced PCell definition

PCells can be hierarchical, as described in [Sec. IV.C of this article](https://ieeexplore.ieee.org/abstract/document/8718393). One PCell can use another PCell in its definition, and the parent pcell should, in this case, inherit the child's parameters. an example taken from `zeropdk.default_library.io` is:

```python
class DCPadArray(DCPad):
    params = ParamContainer(pad_array_count, pad_array_pitch)

    def draw(self, cell):
        # ...
        for i in range(cp.pad_array_count):
            dcpad = DCPad(name=f"pad_{i}", params=cp)
        return cell, ports
```

In this case, `DCPadArray` simply places an array of `DCPad` Pcells, and contains parameters `pad_array_count` and also `pad_array_pitch`, but also the parameters belonging to `DCPad`, such as `layer_metal` and `layer_opening`.

In the EBeam PDK example, one can edit adapt a standard library of pcells to its own parameter sets. For example, EBeam PDK uses particular layers for its metal deposition and oxide etch steps. So the DCPadArray can be changed via the following:

```python

class DCPadArray(DCPadArray):
    params = ParamContainer(
        PCellParameter(
            name="layer_metal",
            type=TypeLayer,
            description="Metal Layer",
            default=EBeam.layers["M1"],
        ),
        PCellParameter(
            name="layer_opening",
            type=TypeLayer,
            description="Open Layer",
            default=EBeam.layers["13_MLopen"],
        ),
    )
```

TODO: adapt example provided [here](https://github.com/lightwave-lab/SiEPIC_EBeam_PDK/tree/scripted_layout/Examples/scripted_layout) to zeropdk.

### Photonics-inspired layout functions

Several assistive tools for handling photonic shapes. For example, it is desired, sometimes, to draw a waveguide with progressive widths (a taper). 

```python
from zeropdk.layout import layout_waveguide
wav_polygon = layout_waveguide(cell, layer, points_list, width)
```

## Developer notes

This project is still under development phase. See the [development notes](devnotes/README.md) for more information.

## Acknowledgements

This  material  is  based  in part upon  work  supported  by  the  National Science Foundation under Grant Number E2CDA-1740262. Any  opinions,  findings,  and  conclusions  or  recommendations expressed  in  this  material  are  those  of  the  author(s)  and  do  not necessarily reflect the views of the National Science Foundation.

