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

grid_parent_dir="mdp_common/mdp_common/control-data"
grid_merged_path="$grid_parent_dir/.merged/grid-extents.fgb"
if [ ! -e "$grid_merged_path" ]; then
    echo "merging control grid parts on first run"
    cat $grid_parent_dir/grid-extents.fgb-part-* > "$grid_merged_path"
fi
