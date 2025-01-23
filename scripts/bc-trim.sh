#!/bin/bash

set -e

pushd $(dirname $0)/..

scripts/merge-grids.sh

# if [ "$#" -lt 4 ]; then
#     echo "Usage: $0 min_x min_y max_x max_y --hillshade"
#     exit 1
# fi

# min_x=$1
# min_y=$2
# max_x=$3
# max_y=$4

image_name="captaincoordinates/bc-trim"
docker build \
    -t $image_name \
    .

docker run \
    --rm \
    -v $PWD/generated-data:/generated-data:rw \
    -v $PWD/.cache/bc-trim:/cache/bc-trim:rw \
    -v $PWD/.cache/bc-hillshade:/cache/bc-hillshade:rw \
    -v $PWD/mdp_common:/mdp_common:ro \
    -v $PWD/mdp_bc_hillshade:/mdp_bc_hillshade:ro \
    -v $PWD/mdp_bc_trim:/mdp_bc_trim:ro \
    -e TRIM_CACHE_DIR=/cache/bc-trim \
    -e TRIM_GENERATED_DIR=/generated-data \
    -e HILLSHADE_CACHE_DIR=/cache/bc-hillshade \
    -e HILLSHADE_GENERATED_DIR=/generated-data \
    -w /mdp_bc_trim \
    $image_name \
    python -m mdp_bc_trim.run "$@"
