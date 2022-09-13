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
        description="PDK factory for klayout",
        long_description=readme,
        long_description_content_type="text/markdown",
        license=license_text.split("\n")[0],
        python_requires=">=3.7",
        packages=find_packages(include=("zeropdk.*")),
        package_data={"zeropdk": ["py.typed"]},
        url="https://github.com/lightwave-lab/zeropdk",
        author="Thomas Ferreira de Lima <zeropdk@tlima.me>",
        author_email="zeropdk@tlima.me",
        include_package_data=True,
        classifiers=(
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Topic :: Scientific/Engineering",
        ),
        install_requires=["numpy", "klayout", "scipy"],
    )

    setup(**metadata)


if __name__ == "__main__":
    main()
