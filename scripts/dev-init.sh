#!/bin/bash

set -e

pushd $(dirname $0)/..

pip install -e mdp_common
pip install -e mdp_bc_hillshade
pip install -e mdp_bc_trim[dev]

pre-commit install
