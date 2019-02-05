Notes from Thomas.
2019-02-04

# Motivation

I want to make a PDK factory so that it is easy to layout chips for new foundry runs if they do not have a proper python-compatible PDK.

The first necessary component is a proper way of defining layers specific to a foundry. I will use a "technology" container for this kind of information.

Secondly, we need a way to define PCell, useful for routing purposes (and for sharing). It has to have the same hierarchy ability as in normal cells, but it needs to be regenerated solely based on its parameters. The simplest "PCell" must be just a minimal extension over a cell stored in .gds format and loaded from the library.

Thirdly, it would be good to have some layout algorithms in hand to ease parametric layout. This includes waveguide creation, bus routing etc. This stuff was already partially included in SiEPIC-tools, but SiEPIC-tools is (at the time of this writing) not suitable for pure python packages.

Other features can include PDK management such as IP blocks and licensing, and some DRC/verification functionality, but I will not develop them yet.

# Technology

Today, technology serves basically to store useful information about layers. SiEPIC also uses it as a connection to Lumerical simulators. The SOEN PDK makes available information about properties of conductors, vias, and waveguides in XML format. KLayout uses a xml-like file (.lyt) to configure reader and writer options, and a (.lyp) file to configure how layers should be displayed on the GUI, but no metadata about them, which is unhelpful.

Because of this complex behavior, I will choose a class as data structure to store all the information above. Static methods can be used to interact with XML, and PDKs can be free to subclass it as much as they need.

## Layers

In my experience, I found that a few sets of layers should exist in every photonic technology: silicon waveguide, metals (routing and/or heating), vias, text/documentation (display only), and port documentation (display only). As a result, I will make them standard and available for simple methods such as waveguide route, Manhattan routing with vias, ports display etc.

## Other information

Let's consider a waveguide, for example. Different technologies offer multiple ways of creating a waveguide: rib, ridge, slot etc. Each of them will use a set of layers and some default parameters. A PDK traditionally offers specifications on each of these types of waveguide. SiEPIC-Tools already has figured out a way to standardize them by using a list of (layer, width, offset) tuples. This is useful to make standard.

# PCell

A PCell is the most important concept to get right. It is hard to change once people adopt it and it is also the most important feature of procedurally generated layout.

With my experience, here are some useful properties of a PCell:

- Reusability across different technologies. One should be able to copy-paste a PCell, say a MRR, between different techs, e.g. Passive/Active Si, SiN, etc.
- Inheritability. One should be able to augment a PCell. E.g. take a MRR cell made only with passive elements, and add a heater or PN junction to it. Very useful for users. This can be done by using Python's class inheritance scheme, where the most complex PCells inherit from the simpler ones. One can also combine different PCells into one larger one. There are caveats to this approach. Some control flow structures (e.g. if-else) must be avoided.
- Interactive. To my understanding, we can only know geometric properties after it is instantiated and its parameters are known. For example, we can only know the positions of MRR pins after setting its radius. We should be able to get port positions, boundary box and other geometric properties of the cell.
- Extra: Layout-tool independence. While I am biased to using KLayout, we can also have a tool-independent layout API. To allow for that, I am going to use klayout.db as my default layout tool and will be sure to pass it as parameter. An advantage of this is that we can have a very lightweight layout tool that only knows points and vectors as default, so that an entire pcell tree can be coded and built without any layout, and only at the end we can trigger the actual layout (polygon creation, cell making) mechanism.

## Ports

As mentioned above, we need to define ports. These can be electrical, or optical, and they should be compatible with certain types of waveguides. They should have their own class because I foresee they being upgraded at a later point.


# Layout tool API

Imagine importing your favorite layout tool as lt in python. Then you can call lt.Box(coordinates) for a rectangle box, or lt.Cell for a new cell. The user has the freedom to pick whatever lt they prefer, whether klayout or other. lt can be also passed as parameter to the layout method of the PCell class. I have always viewed lt to be a module, instead of a class. The path of least friction tells me to keep it that way, because we have a lot of classes defined within a module, such as lt.Cell and lt.Layout. Bear in mind: if a layout module is passed as parameter to a pcell, changing it should trigger redrawing all the pcell hierarchy.


# Collection of layout algorithms

Here's an example of an import statement in one of our masks:

``` python
from layout_algorithms import layout_ring, layout_path, layout_path_with_ends, box_dpolygon, \
    layout_waveguide, layout_circle, layout_square, insert_shape, \
    append_relative, layout_arc_with_drc_exclude, layout_arc, layout_arc2, layout_section, \
    layout_connect_ports, layout_waveguide_angle, layout_disk, layout_rectangle, \
    layout_connect_ports_angle, layout_box
```

These are all functions that take a cell, a layer and some arguments and draws a structure using a layout tool of choice. If we restrict to using a set of API methods, these algorithms should be portable to other tools.
