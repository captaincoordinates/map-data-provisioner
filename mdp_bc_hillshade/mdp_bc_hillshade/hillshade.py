from logging import Logger, getLogger
from os import environ, makedirs, path, remove
from re import IGNORECASE, Match, search, sub
from typing import Final, List, Optional, Tuple, cast
from zipfile import ZipFile

from osgeo import gdal, ogr
from requests import get

from mdp_common import nts_50000_grid_layer_name, nts_50000_grid_path, tmp_dir
from mdp_common.bbox import BBOX
from mdp_common.fs import make_path_compatible

_logger: Final[Logger] = getLogger(__file__)

_cache_dir: Final[str] = path.join(
    environ.get("CACHE_DIR", path.join(path.dirname(__file__), "..", "..", ".cache")),
    "bc-hillshade",
)


def paths_for_bbox(
    bbox: BBOX,
    ignore_cache: Optional[bool] = False,
    resampling: str = "cubic",
    output_crs: str = "EPSG:3005",
    target_resolution: Optional[Tuple[float, float]] = None,
) -> List[str]:
    makedirs(_cache_dir, exist_ok=True)
    driver = ogr.GetDriverByName("FlatGeobuf")
    grid_datasource = driver.Open(nts_50000_grid_path)
    grid_layer = grid_datasource.GetLayerByName(nts_50000_grid_layer_name)
    grid_layer.SetSpatialFilterRect(bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max)
    tif_paths: List[str] = []
    while grid_cell := grid_layer.GetNextFeature():
        cell_name = grid_cell.GetFieldAsString("NTS_SNRC")
        cell_parent = sub(
            "^0", "", cast(Match, search(r"^\d{2,3}[a-z]", cell_name, IGNORECASE))[0]
        )
        for cardinal in (
            "e",
            "w",
        ):
            dem_name = f"{cell_name.lower()}_{cardinal}.dem"
            hillshade_tif_path = path.join(_cache_dir, "{}.hs.tif".format(dem_name))
            final_tif_path = path.join(
                tmp_dir,
                "{}-{}-{}-{}.hs.tif".format(
                    dem_name,
                    bbox.as_path_part,
                    resampling,
                    make_path_compatible(output_crs),
                ),
            )
            tif_paths.append(final_tif_path)
            if not path.exists(hillshade_tif_path) or ignore_cache:
                dem_cache_path = path.join(_cache_dir, dem_name)
                if not path.exists(dem_cache_path) or ignore_cache:
                    zip_file_name = "{}.zip".format(dem_name)
                    zip_tmp_path = path.join(tmp_dir, zip_file_name)
                    zip_url = "https://pub.data.gov.bc.ca/datasets/175624/{}/{}".format(
                        cell_parent, zip_file_name
                    )
                    _logger.info("fetching '{}' from {}".format(cell_name, zip_url))
                    response = get(zip_url)
                    assert response.ok, "failed to download {}".format(zip_url)
                    with open(zip_tmp_path, "wb") as f:
                        f.write(cast(bytes, response.content))
                    try:
                        _logger.info("extracting {}".format(cell_name))
                        with ZipFile(zip_tmp_path, "r") as zip_ref:
                            zip_ref.extract(
                                dem_name,
                                _cache_dir,
                            )
                    except Exception:
                        _logger.exception("failed during zip extraction")
                        raise
                    remove(zip_tmp_path)
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
            _logger.info("clipping {} to {}".format(hillshade_tif_path, final_tif_path))
            gdal.Warp(
                final_tif_path,
                hillshade_tif_path,
                cutlineWKT=bbox.as_wkt,
                cutlineSRS=bbox.crs_code,
                resampleAlg=resampling,
                dstSRS=output_crs,
                xRes=target_resolution[0] if target_resolution else None,
                yRes=target_resolution[1] if target_resolution else None,
            )

    return tif_paths
