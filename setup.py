#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


def touch(fname, times=None):
    with open(fname, "a"):
        os.utime(fname, times)


def main():
    with open("README.md") as f:
        readme = f.read()

    with open("LICENSE") as f:
        license_text = f.read()

    with open("version.py") as f:
        code = compile(f.read(), "version.py", "exec")
        version_dict = {}
        exec(code, {}, version_dict)  # pylint: disable=exec-used
        release = version_dict["release"]

    metadata = dict(
        name="zeropdk",
        version=release,
        description="Lightwave Lab instrumen",
        long_description=readme,
        license=license_text.split("\n")[0],
        python_requires=">=3.6",
        packages=find_packages(include=("zeropdk.*")),
        url="https://github.com/lightwave-lab/zeropdk",
        author="Thomas Ferreira de Lima <tlima@princeton.edu>",
        author_email="tlima@princeton.edu",
        include_package_data=True,
        classifiers=(
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Topic :: Scientific/Engineering",
            "Framework :: Jupyter",
        ),
        install_requires=["numpy", "klayout", "scipy"],
    )

    setup(**metadata)


if __name__ == "__main__":
    main()
