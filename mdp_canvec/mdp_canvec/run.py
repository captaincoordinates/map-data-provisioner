from logging import Logger, getLogger
from os import environ, path
from typing import Final, List, Optional

from osgeo import gdal

from mdp_bc_hillshade.hillshade import paths_for_bbox as hillshade_paths_for_bbox
from mdp_common import tmp_dir
from mdp_common.bbox import BBOX
from mdp_common.fs import make_path_compatible
from mdp_common.wms import WmsProperties
from mdp_common.wms import provision as provision_wms

_logger: Final[Logger] = getLogger(__file__)

_cache_dir: Final[str] = path.join(
    environ.get("CACHE_DIR", path.join(path.dirname(__file__), "..", "..", ".cache")),
    "canvec",
)
_generated_dir: Final[str] = environ.get(
    "GENERATED_DIR", path.join(path.dirname(__file__), "..", "..", "generated-data")
)


def execute(
    bbox: BBOX,
    include_hillshade: bool = False,
    ignore_cache: Optional[bool] = False,
    output_crs: str = "EPSG:3857",
) -> List[str]:
    output_paths = [
        provision_wms(
            label="canvec",
            bbox=bbox,
            base_url="https://maps.geogratis.gc.ca/wms/canvec_en",
            wms_properties=WmsProperties(max_width=4096, max_height=4096),
            wms_crs_code=output_crs,
            layers=(
                "land",
                "hydro",
                "man_made",
                "resource_management",
                "transport",
                "administrative",
                "toponymy",
            ),
            styles=tuple(),
            scale=35000,
            image_format="png",
            cache_dir=_cache_dir,
            output_dir=_generated_dir,
            ignore_cache=ignore_cache,
        )
    ]

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
