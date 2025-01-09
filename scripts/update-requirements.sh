#!/bin/bash

set -e

# Extract pypi requirements from various setup.py files to speed up container image builds.
# If we simply `RUN pip install -e package/path` in a Dockerfile then all of the package's pypi dependencies will be installed.
# However, any change to application code within that package will invalidate that image cache layer,
# requiring that all dependencies are installed again. This can take a long time and depends on pypi being accessible.
# If we extract pypi requirements to generated requirements.txt files then those requirements.txt files can be installed
# in an earlier stage of the Dockerfile, meaning their cache layer is not invalidated by an application code change.
# Ultimately this means that pypi dependency cache layers in the container image are invalidated less often and pypi
# dependencies do not need to be installed so frequently.

# The cost of implementing this approach is that dependencies are now maintained in multiple places.

# This script updates generated requirements.txt files and should be run after any change in pypi dependncies in setup.py files.
# If pypi dependencies are updated in setup.py and this script is not run the application should still work. Additional pypi
# dependencies will be installed alongside the package rather that at an earlier stage. This will make the build less efficient
# as those additional dependencies will not be cached as persistently as dependencies installed via requirements.txt.

pushd $(dirname $0)/..

pip-compile -q --no-annotate --no-strip-extras --output-file bc_trim_stitch/requirements-generated.txt bc_trim_stitch/setup.py &
pid1=$!

wait $pid1
