from setuptools import find_namespace_packages, setup

setup(
    name="mdp-common",
    version="0.1.0",
    python_requires=">=3.12",
    packages=find_namespace_packages(),
    install_requires=[
        "gdal~=3.10.0",
        "pyproj~=3.7.0",
        "requests~=2.32.3",
    ],
    extras_require={},
)
