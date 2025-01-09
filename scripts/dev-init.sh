#!/bin/bash

set -e

pushd $(dirname $0)/..

pip install -e bc_trim_stitch[dev]

pre-commit install
