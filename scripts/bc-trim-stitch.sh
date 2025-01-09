#!/bin/bash

set -e

pushd $(dirname $0)/..

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 min_x min_y max_x max_y"
    exit 1
fi

min_x=$1
min_y=$2
max_x=$3
max_y=$4

grid_parent_dir="bc_trim_stitch/bc_trim_stitch/control-data"
grid_merged_path="$grid_parent_dir/.merged/grid-extents.fgb"
if [ ! -e "$grid_merged_path" ]; then
    echo "merging control grid parts on first run"
    cat $grid_parent_dir/grid-extents.fgb-part-* > "$grid_merged_path"
fi

image_name="captaincoordinates/bc-trim-stitch"
docker build \
    -t $image_name \
    .

docker run \
    --rm \
    -v $PWD/generated-data:/generated-data:rw \
    -v $PWD/.cache:/cache:rw \
    -v $PWD/bc_trim_stitch:/app:ro \
    -e TRIM_CACHE_DIR=/cache \
    -e TRIM_GENERATED_DIR=/generated-data \
    -w /app \
    $image_name \
    python -m bc_trim_stitch.run $min_x $min_y $max_x $max_y
