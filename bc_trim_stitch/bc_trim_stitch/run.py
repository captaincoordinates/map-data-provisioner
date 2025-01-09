from logging import Logger, getLogger
from os import environ, makedirs, path
from re import IGNORECASE, Match, search
from typing import Final, Optional, cast
from zipfile import ZipFile

from osgeo import gdal, ogr
from requests import get

from bc_trim_stitch.bbox import BBOX

_logger: Final[Logger] = getLogger(__file__)

_cache_dir: Final[str] = environ.get(
    "TRIM_CACHE_DIR", path.join(path.dirname(__file__), ".cache")
)
_control_source_path: Final[str] = path.join(
    path.dirname(__file__), "control-data", ".merged", "grid-extents.fgb"
)
_control_grid_layer_name: Final[str] = "bc-trim-20000"
_generated_dir: Final[str] = environ.get(
    "TRIM_GENERATED_DIR", path.join(path.dirname(__file__), "generated-data")
)


def execute(bbox: BBOX, ignore_cache: Optional[bool] = False) -> None:
    makedirs(_cache_dir, exist_ok=True)
    driver = ogr.GetDriverByName("FlatGeobuf")
    grid_datasource = driver.Open(_control_source_path)
    grid_layer = grid_datasource.GetLayerByName(_control_grid_layer_name)
    grid_layer.SetSpatialFilterRect(bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)
    while grid_cell := grid_layer.GetNextFeature():
        cell_name = grid_cell.GetFieldAsString("MAP_TILE")
        zip_cache_path = path.join(_cache_dir, "{}.zip".format(cell_name))
        tif_name = "{}.tif".format(cell_name)
        if not path.exists(zip_cache_path) or ignore_cache:
            cell_parent = cast(Match, search(r"^\d{2,3}[a-z]", cell_name, IGNORECASE))[
                0
            ]
            zip_url = f"https://pub.data.gov.bc.ca/datasets/177864/tif/bcalb/{cell_parent}/{cell_name}.zip"
            _logger.info("fetching '{}' from {}".format(cell_name, zip_url))
            response = get(zip_url)
            assert response.ok, "failed to download {}".format(zip_url)
            with open(zip_cache_path, "wb") as f:
                f.write(cast(bytes, response.content))
        tif_cache_path = path.join(_cache_dir, tif_name)
        if not path.exists(tif_cache_path) or ignore_cache:
            try:
                _logger.info("extracting {}".format(cell_name))
                with ZipFile(zip_cache_path, "r") as zip_ref:
                    zip_ref.extract(
                        tif_name,
                        _cache_dir,
                    )
            except Exception:
                _logger.exception("failed during zip extraction")
                raise
        try:
            gdal.Warp(
                path.join(_generated_dir, tif_name),
                tif_cache_path,
                cutlineDSName=_control_source_path,
                cutlineLayer=_control_grid_layer_name,
                cutlineWhere="MAP_TILE = '{}'".format(cell_name),
                cropToCutline=False,
                cutlineBlend=1,
                dstNodata=-1,
                # dstSRS=OUTPUT_CRS_CODE,
                resampleAlg="lanczos",
            )
        except Exception:
            _logger.exception("failed during GDAL warp")
            raise


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("min_x", type=float, help="Bounding box minimum x (longitude)")
    parser.add_argument("min_y", type=float, help="Bounding box minimum y (latitude)")
    parser.add_argument("max_x", type=float, help="Bounding box maximum x (longitude)")
    parser.add_argument("max_y", type=float, help="Bounding box maximum y (latitude)")
    args = parser.parse_args()
    execute(
        BBOX(
            min_x=args.min_x,
            min_y=args.min_y,
            max_x=args.max_x,
            max_y=args.max_y,
        )
    )
