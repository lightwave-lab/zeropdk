import klayout.db as pya

# import zeropdk's tech

from zeropdk.layout.geometry import bezier_optimal
from zeropdk.layout.waveguides import layout_waveguide

import numpy as np


def bezier_curve(origin, angle0, angle3, ex, ey):
    P0 = origin
    P3 = origin + 100 * ex

    curve = bezier_optimal(P0, P3, angle0, angle3)
    return curve


def main():
    layout = pya.Layout()
    TOP = layout.create_cell("TOP")

    layer = pya.LayerInfo(1, 0)  # First layer

    origin = pya.DPoint(0, 0)
    ex = pya.DVector(1, 0)
    ey = pya.DVector(0, 1)

    angles = np.linspace(-170, 170, 13)

    for i, angle_0 in enumerate(angles):
        for j, angle_3 in enumerate(angles):
            print("Bezier({:>2d}, {:>2d})".format(i, j))
            curve = bezier_curve(origin + ey * i * 150 + ex * j * 150, angle_0, angle_3, ex, ey)
            layout_waveguide(TOP, layer, curve, width=0.5)

    layout.write("bezier_waveguides.gds")


if __name__ == "__main__":
    main()
