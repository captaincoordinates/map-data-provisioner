import re
import zipfile
from os import environ, path
from typing import Final, List

from app.common.get_datasource_from_bbox import (
    BBOX_LAYER_NAME,
    get_datasource_from_bbox,
)
from app.common.http_retriever import RetrievalRequest, retrieve
from app.common.util import (
    get_cache_path,
    get_data_path,
    get_run_data_path,
    remove_intermediaries,
    skip_file_creation,
    swallow_unimportant_warp_error,
)
from app.tilemill.ProjectLayerType import ProjectLayerType
from osgeo.gdal import DEMProcessing, Warp
from osgeo.ogr import GetDriverByName

from mdp_common import nts_50000_grid_path
from mdp_common.bbox import BBOX

_cache_dir: Final[str] = environ.get(
    "TRIM_CACHE_DIR", path.join(path.dirname(__file__), ".cache", "bc-hillshade")
)
_control_grid_layer_name: Final[str] = "nts-50000-grid"
_generated_dir: Final[str] = environ.get(
    "BC_HILLSHADE_GENERATED_DIR", path.join(path.dirname(__file__), "generated-data")
)


def provision(bbox: BBOX, run_id: str) -> List[str]:
    run_directory = get_run_data_path(run_id, (CACHE_DIR_NAME,))
    os.makedirs(run_directory)
    driver = GetDriverByName("GPKG")
    grid_datasource = driver.Open(get_data_path(("grids.gpkg",)))
    grid_layer = grid_datasource.GetLayerByName("Canada-50000")
    grid_layer.SetSpatialFilterRect(bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)
    bbox_cells = list()
    while grid_cell := grid_layer.GetNextFeature():
        cell_name = grid_cell.GetFieldAsString("NTS_SNRC")
        cell_parent = re.sub(
            "^0", "", re.search(r"^\d{2,3}[a-z]", cell_name, re.IGNORECASE)[0]
        )
        for cardinal in ("e", "w"):
            cell_part_name = f"{cell_name.lower()}_{cardinal}"
            zip_file_name = f"{cell_part_name}.dem.zip"
            bbox_cells.append(
                GenerationRequest(
                    url=f"https://pub.data.gov.bc.ca/datasets/175624/{cell_parent.lower()}/{zip_file_name}",
                    path=get_cache_path((CACHE_DIR_NAME, zip_file_name)),
                    expected_types=["application/zip"],
                    dem_path=get_cache_path((CACHE_DIR_NAME, f"{cell_part_name}.dem")),
                    prj_path=get_cache_path(
                        (CACHE_DIR_NAME, f"{cell_part_name}_prj.tif")
                    ),
                    hs_path=get_cache_path(
                        (CACHE_DIR_NAME, f"{cell_part_name}_hs.tif")
                    ),
                    run_path=os.path.join(run_directory, f"{cell_part_name}.tif"),
                )
            )

    to_generate = list(
        filter(
            lambda generation_request: not skip_file_creation(
                generation_request.hs_path
            ),
            bbox_cells,
        )
    )
    retrieve(to_generate, HTTP_RETRIEVAL_CONCURRENCY)

    for generation_request in to_generate:
        with zipfile.ZipFile(generation_request.path, "r") as zip_ref:
            zip_ref.extractall(get_cache_path((CACHE_DIR_NAME,)))
        Warp(
            generation_request.prj_path,
            generation_request.dem_path,
            srcSRS="EPSG:4269",
            dstSRS=OUTPUT_CRS_CODE,
            resampleAlg="cubic",
        )
        DEMProcessing(
            generation_request.hs_path,
            generation_request.prj_path,
            "hillshade",
            format="GTiff",
            band=1,
            azimuth=225,
            altitude=45,
            scale=1,
            zFactor=1,
            computeEdges=True,
        )
        if remove_intermediaries():
            os.remove(generation_request.path)
            os.remove(generation_request.dem_path)
            os.remove(generation_request.prj_path)

    for generation_request in bbox_cells:
        try:
            Warp(
                generation_request.run_path,
                generation_request.hs_path,
                cutlineDSName=get_datasource_from_bbox(
                    bbox, get_run_data_path(run_id, None)
                ),
                cutlineLayer=BBOX_LAYER_NAME,
                cropToCutline=False,
                cutlineBlend=1,
                dstNodata=-1,
            )
        except Exception as ex:
            swallow_unimportant_warp_error(ex)

    merged_output_path = os.path.join(run_directory, "merged.tif")
    Warp(
        merged_output_path,
        list(
            filter(
                lambda run_path: os.path.exists(run_path),
                map(lambda generation_request: generation_request.run_path, bbox_cells),
            )
        ),
    )

    return [merged_output_path]
