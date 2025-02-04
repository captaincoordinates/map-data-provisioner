from logging import Logger, getLogger
from os import environ, makedirs, path, remove
from re import IGNORECASE, Match, search
from typing import Final, List, Optional, cast
from zipfile import ZipFile

from osgeo import gdal, ogr
from requests import get

from mdp_bc_hillshade.hillshade import paths_for_bbox as hillshade_paths_for_bbox
from mdp_common import tmp_dir
from mdp_common.bbox import BBOX
from mdp_common.fs import make_path_compatible

_logger: Final[Logger] = getLogger(__file__)

_cache_dir: Final[str] = path.join(
    environ.get("CACHE_DIR", path.join(path.dirname(__file__), "..", "..", ".cache")),
    "bc-trim",
)
_control_source_path: Final[str] = path.join(
    path.dirname(__file__), "control-data", ".merged", "grid-extents.fgb"
)
_control_grid_layer_name: Final[str] = "bc-trim-20000"
_generated_dir: Final[str] = environ.get(
    "GENERATED_DIR", path.join(path.dirname(__file__), "..", "..", "generated-data")
)


def execute(
    bbox: BBOX,
    include_hillshade: bool = False,
    ignore_cache: Optional[bool] = False,
    output_crs: str = "EPSG:3005",
) -> List[str]:
    rgb_tif_name_no_suffix = "bc-trim-{}-{}".format(
        bbox.as_path_part, make_path_compatible(output_crs)
    )
    rgb_tif_path = path.join(_generated_dir, "{}.tif".format(rgb_tif_name_no_suffix))
    makedirs(_cache_dir, exist_ok=True)
    makedirs(_generated_dir, exist_ok=True)
    driver = ogr.GetDriverByName("FlatGeobuf")
    grid_datasource = driver.Open(_control_source_path)
    grid_layer = grid_datasource.GetLayerByName(_control_grid_layer_name)
    grid_layer.SetSpatialFilterRect(bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max)
    generated_tif_paths: List[str] = []
    while grid_cell := grid_layer.GetNextFeature():
        cell_name = grid_cell.GetFieldAsString("MAP_TILE")
        tif_output_path = path.join(
            tmp_dir, "{}-{}.tif".format(cell_name, make_path_compatible(output_crs))
        )
        generated_tif_paths.append(tif_output_path)
        if path.exists(tif_output_path) and not ignore_cache:
            _logger.info("{} already exists".format(tif_output_path))
            continue
        tif_cache_path = path.join(_cache_dir, "{}.tif".format(cell_name))
        if not path.exists(tif_cache_path) or ignore_cache:
            zip_tmp_path = path.join(tmp_dir, "{}.zip".format(cell_name))
            cell_parent = cast(Match, search(r"^\d{2,3}[a-z]", cell_name, IGNORECASE))[
                0
            ]
            zip_url = f"https://pub.data.gov.bc.ca/datasets/177864/tif/bcalb/{cell_parent}/{cell_name}.zip"
            _logger.info("fetching '{}' from {}".format(cell_name, zip_url))
            response = get(zip_url)
            assert response.ok, "failed to download {}".format(zip_url)
            with open(zip_tmp_path, "wb") as f:
                f.write(cast(bytes, response.content))
            try:
                _logger.info("extracting {}".format(cell_name))
                with ZipFile(zip_tmp_path, "r") as zip_ref:
                    zip_ref.extract(
                        "{}.tif".format(cell_name),
                        _cache_dir,
                    )
            except Exception:
                _logger.exception("failed during zip extraction")
                raise
            remove(zip_tmp_path)
        _logger.info("clipping {} to {}".format(tif_cache_path, tif_output_path))
        try:
            gdal.Warp(
                tif_output_path,
                tif_cache_path,
                cutlineDSName=_control_source_path,
                cutlineLayer=_control_grid_layer_name,
                cutlineWhere="MAP_TILE = '{}'".format(cell_name),
                cropToCutline=False,
                cutlineBlend=1,
                dstNodata=-1,
                dstSRS=output_crs,
                resampleAlg="lanczos",
            )
        except Exception:
            _logger.exception("failed during GDAL clipping warp")
            raise

    trim_vrt_path = path.join(tmp_dir, "{}.vrt".format(rgb_tif_name_no_suffix))
    _logger.info("generating VRT {}".format(trim_vrt_path))
    gdal.BuildVRT(trim_vrt_path, generated_tif_paths)
    _logger.info("generating {}".format(rgb_tif_path))
    gdal.Warp(
        rgb_tif_path,
        trim_vrt_path,
        cutlineWKT=bbox.as_wkt,
        cutlineSRS=bbox.crs_code,
        cropToCutline=True,
        cutlineBlend=1,
        dstNodata=-1,
        dstSRS=output_crs,
        resampleAlg="cubic",
    )
    output_paths = [rgb_tif_path]

    if include_hillshade:
        _logger.info("generating hillshade TIFs")
        hillshade_source_paths = hillshade_paths_for_bbox(
            bbox, ignore_cache=ignore_cache, output_crs=output_crs
        )
        hillshade_tif_name_no_suffix = "hillshade-{}-{}".format(
            bbox.as_path_part, make_path_compatible(output_crs)
        )
        hillshade_vrt_path = path.join(
            tmp_dir, "{}.vrt".format(hillshade_tif_name_no_suffix)
        )
        _logger.info("generating VRT {}".format(hillshade_vrt_path))
        gdal.BuildVRT(hillshade_vrt_path, hillshade_source_paths)
        hillshade_tif_path = path.join(
            _generated_dir, "{}.tif".format(hillshade_tif_name_no_suffix)
        )
        gdal.Warp(
            hillshade_tif_path,
            hillshade_vrt_path,
            cutlineWKT=bbox.as_wkt,
            cutlineSRS=bbox.crs_code,
            cropToCutline=True,
            cutlineBlend=1,
            dstNodata=-1,
            dstSRS=output_crs,
            resampleAlg="cubic",
        )
        output_paths.append(hillshade_tif_path)

    return output_paths


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("min_x", type=float, help="Bounding box minimum x (longitude)")
    parser.add_argument("min_y", type=float, help="Bounding box minimum y (latitude)")
    parser.add_argument("max_x", type=float, help="Bounding box maximum x (longitude)")
    parser.add_argument("max_y", type=float, help="Bounding box maximum y (latitude)")
    parser.add_argument(
        "--hillshade", action="store_true", help="Include hillshading effect"
    )
    args = parser.parse_args()
    execute(
        BBOX(
            x_min=args.min_x,
            y_min=args.min_y,
            x_max=args.max_x,
            y_max=args.max_y,
        ),
        include_hillshade=args.hillshade,
    )
