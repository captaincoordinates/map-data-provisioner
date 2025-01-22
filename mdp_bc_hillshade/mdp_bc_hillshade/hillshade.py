from logging import Logger, getLogger
from os import environ, makedirs, path
from re import IGNORECASE, search, sub
from typing import Final, List, Optional, cast
from zipfile import ZipFile

from osgeo import gdal, ogr
from requests import get

from mdp_common import nts_50000_grid_layer_name, nts_50000_grid_path
from mdp_common.bbox import BBOX

_logger: Final[Logger] = getLogger(__file__)

_cache_dir: Final[str] = environ.get(
    "HILLSHADE_CACHE_DIR", path.join(path.dirname(__file__), ".cache", "bc-hillshade")
)
_generated_dir: Final[str] = environ.get(
    "HILLSHADE_GENERATED_DIR", path.join(path.dirname(__file__), "generated-data")
)


# next step is to write clipped hillshade outputs to tmp dir - NOT CACHE DIR - and return those paths to caller

# need to also write BC TRIM clipped tiles to tmp as currently polluting cache

# should also see if can do some antialiasing on the hillshade cells


def paths_for_bbox(bbox: BBOX, ignore_cache: Optional[bool] = False) -> List[str]:
    makedirs(_cache_dir, exist_ok=True)
    makedirs(_generated_dir, exist_ok=True)
    driver = ogr.GetDriverByName("FlatGeobuf")
    grid_datasource = driver.Open(nts_50000_grid_path)
    grid_layer = grid_datasource.GetLayerByName(nts_50000_grid_layer_name)
    grid_layer.SetSpatialFilterRect(bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max)
    tif_paths: List[str] = []
    while grid_cell := grid_layer.GetNextFeature():
        cell_name = grid_cell.GetFieldAsString("NTS_SNRC")
        cell_parent = sub("^0", "", search(r"^\d{2,3}[a-z]", cell_name, IGNORECASE)[0])
        for cardinal in (
            "e",
            "w",
        ):
            dem_name = f"{cell_name.lower()}_{cardinal}.dem"
            hillshade_tif_path = path.join(_cache_dir, "{}.hs.tif".format(dem_name))
            if path.exists(hillshade_tif_path) and not ignore_cache:
                continue
            dem_cache_path = path.join(_cache_dir, dem_name)
            if not path.exists(dem_cache_path) or ignore_cache:
                zip_file_name = "{}.zip".format(dem_name)
                zip_cache_path = path.join(_cache_dir, zip_file_name)
                zip_url = "https://pub.data.gov.bc.ca/datasets/175624/{}/{}".format(
                    cell_parent, zip_file_name
                )
                _logger.info("fetching '{}' from {}".format(cell_name, zip_url))
                response = get(zip_url)
                assert response.ok, "failed to download {}".format(zip_url)
                with open(zip_cache_path, "wb") as f:
                    f.write(cast(bytes, response.content))
                if not path.exists(dem_cache_path) or ignore_cache:
                    try:
                        _logger.info("extracting {}".format(cell_name))
                        with ZipFile(zip_cache_path, "r") as zip_ref:
                            zip_ref.extract(
                                dem_name,
                                _cache_dir,
                            )
                    except Exception:
                        _logger.exception("failed during zip extraction")
                        raise
            _logger.info(
                "hillshading {} to {}".format(dem_cache_path, hillshade_tif_path)
            )
            gdal.DEMProcessing(
                hillshade_tif_path,
                dem_cache_path,
                "hillshade",
                format="GTiff",
                band=1,
                azimuth=225,
                altitude=45,
                scale=1,
                zFactor=1,
                computeEdges=True,
            )
            tif_paths.append(hillshade_tif_path)

    return tif_paths
