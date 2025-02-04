#!/bin/bash

set -e

pushd $(dirname $0)/..

echo "NTS 50000 grid"
grid_parent_dir="mdp_common/mdp_common/control-data"
grid_merged_path="$grid_parent_dir/.merged/nts-50000-grid.fgb"
if [ ! -e "$grid_merged_path" ]; then
    echo "  merging control grid parts on first run"
    cat $grid_parent_dir/nts-50000-grid.fgb-part-* > "$grid_merged_path"
else
    echo "  already merged"
fi

echo "BC TRIM 20000 grid"
grid_parent_dir="mdp_bc_trim/mdp_bc_trim/control-data"
grid_merged_path="$grid_parent_dir/.merged/grid-extents.fgb"
if [ ! -e "$grid_merged_path" ]; then
    echo "  merging control grid parts on first run"
    cat $grid_parent_dir/grid-extents.fgb-part-* > "$grid_merged_path"
else
    echo "  already merged"
fi
