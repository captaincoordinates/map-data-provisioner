from setuptools import find_namespace_packages, setup

setup(
    name="bc-trim-stitch",
    version="0.1.0",
    python_requires=">=3.12",
    packages=find_namespace_packages(),
    install_requires=[
        "gdal~=3.10.0",
        "requests~=2.32.3",
    ],
    extras_require={
        "dev": [
            "pip-tools~=7.4.1",
            "pre-commit~=4.0.1",
        ],
        "test": [],
    },
)
