from dataclasses import dataclass
from logging import Logger, getLogger
from math import ceil, floor
from os import makedirs, path
from re import IGNORECASE, sub
from typing import Final, List, Tuple

from osgeo import gdal
from pyproj import CRS, Transformer
from requests import get

from mdp_common import tmp_dir
from mdp_common.bbox import BBOX
from mdp_common.fs import make_path_compatible

_default_wms_version: Final[str] = "1.1.1"
_default_dpi: Final[int] = 96
_metres_in_one_inch: Final[float] = 0.0254
_logger: Final[Logger] = getLogger(__file__)


@dataclass
class WmsProperties:
    max_width: int
    max_height: int


@dataclass
class _TileAxisInterval:
    start: float
    end: float


@dataclass
class _CacheFriendlyImageProperties:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    scale: int
    width: int
    height: int


@dataclass
class _ImageRequestProperties:
    image_properties: _CacheFriendlyImageProperties
    wms_url: str
    response_save_path: str
    tif_path: str


def provision(
    label: str,
    bbox: BBOX,
    base_url: str,
    wms_properties: WmsProperties,
    wms_crs_code: str,
    layers: Tuple[str, ...],
    styles: Tuple[str, ...],
    scale: int,
    image_format: str,
    cache_dir: str,
    output_dir: str,
    ignore_cache: bool = False,
) -> str:
    makedirs(cache_dir, exist_ok=True)
    source_image_properties = _build_source_image_properties_for_bbox(
        bbox, wms_crs_code, scale, wms_properties
    )
    image_request_properties = _build_image_request_properties(
        base_url,
        source_image_properties,
        layers,
        styles,
        wms_crs_code,
        image_format,
        cache_dir,
    )
    for entry in [
        entry
        for entry in image_request_properties
        if not path.exists(entry.tif_path) or ignore_cache
    ]:
        response = get(entry.wms_url)
        if not response.ok:
            raise Exception(
                "unexpected WMS response statux {} for '{}'".format(
                    response.status_code, entry.wms_url
                )
            )
        response_type = response.headers.get("Content-Type", "")
        if response_type != f"image/{image_format}":
            raise Exception(
                "unexpected WMS response type '{}' for '{}'".format(
                    response_type, entry.wms_url
                )
            )
        with open(entry.response_save_path, "wb") as f:
            f.write(response.content)
        _convert_response_to_tif(entry, wms_crs_code)

    output_file_name_template = "{}-{}-{}-{}".format(
        label,
        scale,
        bbox.as_path_part,
        make_path_compatible(wms_crs_code),
    )
    vrt_path = path.join(tmp_dir, "{}.vrt".format(output_file_name_template))
    _logger.info("generating {}".format(vrt_path))
    gdal.BuildVRT(vrt_path, [entry.tif_path for entry in image_request_properties])
    tif_path = path.join(output_dir, "{}.tif".format(output_file_name_template))
    _logger.info("generating {}".format(tif_path))
    gdal.Warp(
        tif_path,
        vrt_path,
        cutlineWKT=bbox.as_wkt,
        cutlineSRS=bbox.crs_code,
        cropToCutline=True,
        cutlineBlend=1,
        dstNodata=-1,
        dstSRS=wms_crs_code,
        resampleAlg="cubic",
    )
    return tif_path


def _build_source_image_properties_for_bbox(
    bbox: BBOX, wms_crs_code: str, scale: int, wms_properties: WmsProperties
) -> List[_CacheFriendlyImageProperties]:
    wms_crs = CRS(wms_crs_code)
    transformer = Transformer.from_crs(bbox.crs_code, wms_crs, always_xy=True)
    llx, lly = list(
        map(lambda ord: floor(ord), transformer.transform(bbox.x_min, bbox.y_min))
    )
    urx, ury = list(
        map(lambda ord: ceil(ord), transformer.transform(bbox.x_max, bbox.y_max))
    )
    crs_origin_x, crs_origin_y = transformer.transform(
        wms_crs.area_of_use.west, wms_crs.area_of_use.south
    )
    max_image_pixel_width, max_image_pixel_height = (
        wms_properties.max_width,
        wms_properties.max_height,
    )
    cache_friendly_image_parameters_list = list()

    def build_intervals(
        origin: float, interval_size: float, bbox_min: float, bbox_max: float
    ) -> List[_TileAxisInterval]:
        intervals = list()
        start = origin
        while start + interval_size <= bbox_min:
            start += interval_size
        intervals.append(start)
        end = start
        while end < bbox_max:
            end += interval_size
            intervals.append(end)
        return [
            _TileAxisInterval(start=interval, end=intervals[i + 1])
            for i, interval in enumerate(intervals[0:-1])
        ]

    max_image_map_unit_width, max_image_map_unit_height = (
        _pixels_to_map_units(max_image_pixel_width, scale, wms_crs),
        _pixels_to_map_units(max_image_pixel_height, scale, wms_crs),
    )
    # grid_aligned logic introduced to promote reuse of previously-downloaded tiles
    # without grid-alignment we only request exactly what is required to cover the BBOX, however this means
    # existing files that already partially or completely cover the BBOX are very unlikely to be reused, meaning
    # new files are downloaded for the same area and saved with different filenames
    x_intervals = build_intervals(crs_origin_x, max_image_map_unit_width, llx, urx)
    y_intervals = build_intervals(crs_origin_y, max_image_map_unit_height, lly, ury)
    for x_interval in x_intervals:
        for y_interval in y_intervals:
            cache_friendly_image_parameters_list.append(
                _CacheFriendlyImageProperties(
                    x_min=x_interval.start,
                    y_min=y_interval.start,
                    x_max=x_interval.end,
                    y_max=y_interval.end,
                    scale=scale,
                    width=max_image_pixel_width,
                    height=max_image_pixel_height,
                )
            )
    return cache_friendly_image_parameters_list


def _build_image_request_properties(
    base_url: str,
    source_image_properties: List[_CacheFriendlyImageProperties],
    layers: Tuple[str, ...],
    styles: Tuple[str, ...],
    wms_crs_code: str,
    image_format: str,
    cache_directory: str,
    transparent: bool = False,
) -> List[_ImageRequestProperties]:
    def define_url_and_paths(
        image_properties: _CacheFriendlyImageProperties,
    ) -> _ImageRequestProperties:
        wms_url = "?".join(
            [
                base_url,
                "&".join(
                    [
                        f"{key}={value}"
                        for key, value in {
                            "SERVICE": "WMS",
                            "VERSION": _default_wms_version,
                            "REQUEST": "GetMap",
                            "BBOX": f"{image_properties.x_min},{image_properties.y_min},{image_properties.x_max},{image_properties.y_max}",
                            "SRS": wms_crs_code,
                            "WIDTH": str(image_properties.width),
                            "HEIGHT": str(image_properties.height),
                            "LAYERS": ",".join(layers),
                            "STYLES": ",".join(styles),
                            "FORMAT": f"image/{image_format}",
                            "DPI": str(_default_dpi),
                            "MAP_RESOLUTION": str(_default_dpi),
                            "FORMAT_OPTIONS": f"dpi:{_default_dpi}",
                            "TRANSPARENT": str(transparent),
                        }.items()
                    ]
                ),
            ]
        )
        file_name = f"{image_properties.scale}_{_default_dpi}_{sub('[^0-9a-z]', '_', wms_crs_code, flags=IGNORECASE)}_{image_properties.x_min}_{image_properties.y_min}"
        cache_path_base = path.join(cache_directory, file_name)
        response_save_path = f"{cache_path_base}.{image_format}"
        tif_path = f"{cache_path_base}.tif"
        return _ImageRequestProperties(
            image_properties=image_properties,
            wms_url=wms_url,
            response_save_path=response_save_path,
            tif_path=tif_path,
        )

    return list(map(lambda tile: define_url_and_paths(tile), source_image_properties))


def _convert_response_to_tif(
    image_request: _ImageRequestProperties,
    wms_crs_code: str,
) -> None:
    if path.exists(image_request.response_save_path):
        _logger.info(
            "converting '{}' to '{}'".format(
                image_request.response_save_path, image_request.tif_path
            )
        )
        src_file = gdal.Open(image_request.response_save_path, gdal.GA_ReadOnly)
        gdal.Translate(
            image_request.tif_path,
            src_file,
            format="GTiff",
            noData=None,
            outputSRS=wms_crs_code,
            # Translate expects bounds in format ulX, ulY, lrX, lrY so flip minY and maxY
            outputBounds=(
                image_request.image_properties.x_min,
                image_request.image_properties.y_max,
                image_request.image_properties.x_max,
                image_request.image_properties.y_min,
            ),
        )
    else:
        raise Exception(
            "expected file {} does not exist".format(image_request.response_save_path)
        )


def _pixels_to_map_units(pixels: float, scale: int, map_crs: CRS) -> float:
    return ((pixels * scale) / _default_dpi) * _get_map_units_in_one_inch(map_crs)


def _get_map_units_in_one_inch(map_crs: CRS) -> float:
    return _metres_in_one_inch * map_crs.axis_info[0].unit_conversion_factor
