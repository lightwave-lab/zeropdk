""" I noticed that _bezier_optimal takes about 50ms on average.
This function is called every time we need a bezier waveguide.
It is worth therefore saving a pre-computed interpolated function
computed across a wide variety of angles.

This generates the bezier_optimal.npz file
"""

from zeropdk.layout.geometry import _bezier_optimal

from scipy.interpolate import interp2d
import numpy as np
import os


def generate_npz():

    x = y = np.linspace(-170, 170, 351) * np.pi / 180

    xx, yy = np.meshgrid(x, y)
    z_a, z_b = np.frompyfunc(_bezier_optimal, 2, 2)(xx, yy)
    z_a = z_a.astype(np.float)
    z_b = z_b.astype(np.float)

    # need to store x, y, z_a and z_b
    # recall with interpolate(angles_0, angles_3, z_a, kind='cubic')
    np.savez("bezier_optimal.npz", x=x, y=y, z_a=z_a, z_b=z_b)


def memoized_bezier_optimal(angle0, angle3, file):
    npzfile = np.load(file)
    x = npzfile["x"]
    y = npzfile["y"]
    z_a = npzfile["z_a"]
    z_b = npzfile["z_b"]

    a = interp2d(x, y, z_a)(angle0, angle3)[0]
    b = interp2d(x, y, z_b)(angle0, angle3)[0]
    return a, b


if __name__ == "__main__":
    if not os.path.isfile("bezier_optimal.npz"):
        generate_npz()

    # testing
    x = y = np.linspace(-170, 170, 13) * np.pi / 180
    for x, y in zip(np.random.choice(x, 10), np.random.choice(y, 10)):
        print("trying (x,y) == ({}, {})".format(x, y))
        print(memoized_bezier_optimal(x, y, file="bezier_optimal.npz"))
        print(_bezier_optimal(x, y))
        print("---")
