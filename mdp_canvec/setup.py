from setuptools import find_namespace_packages, setup

setup(
    name="mdp-canvec",
    version="0.1.0",
    python_requires=">=3.12",
    packages=find_namespace_packages(),
    install_requires=[],
    extras_require={
        "dev": [
            "pip-tools~=7.4.1",
            "pre-commit~=4.0.1",
        ],
        "test": [],
        "local_dependencies": [
            "mdp-common==0.10.0",
            "mdp-bc-hillshade==0.10.0",
        ],
    },
)
