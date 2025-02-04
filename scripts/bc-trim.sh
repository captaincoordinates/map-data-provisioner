#!/bin/bash

set -e

pushd $(dirname $0)/..

scripts/merge-grids.sh

image_name="captaincoordinates/mdp-bc-trim"
docker build \
    -t $image_name \
    .

docker run \
    --rm \
    -v $PWD/generated-data:/generated-data:rw \
    -v $PWD/.cache:/cache:rw \
    -v $PWD/.tmp:/tmp:rw \
    -e CACHE_DIR=/cache \
    -e GENERATED_DIR=/generated-data \
    -w /mdp_bc_trim \
    $image_name \
    python -m mdp_bc_trim.run "$@"
