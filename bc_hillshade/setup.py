from setuptools import find_namespace_packages, setup

setup(
    name="bc-hillshade",
    version="0.1.0",
    python_requires=">=3.12",
    packages=find_namespace_packages(),
    install_requires=[
        "gdal~=3.10.0",
    ],
)
