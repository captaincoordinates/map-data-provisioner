# Map Data Provisioner

Supports generation of map data products from source data.

## Usage

### BC TRIM 1:20,000

Provision BC TRIM 1:20,000 TIF data based on a bounding box.

```sh
# bounding box format x_min, y_min, x_max, y_max
scripts/bc-trim.sh -127.29412 54.72155 -127.09465 54.80167
# also provision a hillshade layer for the area
scripts/bc-trim.sh -127.29412 54.72155 -127.09465 54.80167 --hillshade
```

## Development

### Environment

To configure a local development environment:

> [!NOTE]
> Assumes a virtual environment with Python >= 3.12

> [!NOTE]
> Dependencies include GDAL, which requires native binaries installed in the development environment. This can be achieved with Docker or Conda to avoid polluting the system environment

```sh
scripts/dev-init.sh
```
