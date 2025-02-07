from setuptools import find_namespace_packages, setup

setup(
    name="mdp-bc-hillshade",
    version="0.1.0",
    python_requires=">=3.12",
    packages=find_namespace_packages(),
    install_requires=[],
    extras_require={
        "local_dependencies": [
            "mdp-common==0.10.0",
        ],
    },
)
