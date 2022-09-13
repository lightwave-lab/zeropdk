""" Minimal PDK for EBeam constructed with ZeroPDK. """

import os
import logging
from collections import abc
from zeropdk import Tech
from zeropdk.pcell import PCell

logger = logging.getLogger()


lyp_path = os.path.join(os.path.dirname(__file__), "EBeam.lyp")


# Technology file
EBeam = Tech.load_from_xml(lyp_path)


# Helper functions


def draw_ports(cell, ports):
    """Draws ports in the Pin Recognition layer (SiEPIC)"""

    if isinstance(ports, abc.Mapping):  # dictionary
        for port in ports.values():
            port.draw(cell, EBeam.layers["PinRec"])
    elif isinstance(ports, abc.Sequence):  # list
        for port in ports:
            port.draw(cell, EBeam.layers["PinRec"])
    else:
        raise RuntimeError("Give a list or dict of Ports")


# PCells

from zeropdk.default_library.io import DCPad, DCPadArray
from zeropdk.pcell import PCellParameter, TypeLayer, ParamContainer

# Overriding default layers


class DCPad(DCPad):
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
