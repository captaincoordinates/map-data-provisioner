from os import environ, path
from typing import Optional

from osgeo import ogr

from mdp_common import (
    nts_50000_grid_file_name,
    nts_50000_grid_layer_name,
    nts_50000_id_attribute_name,
)

ogr.UseExceptions()


def _extract(
    source_path: str,
    source_layer_name: str,
    target_path: str,
    target_layer_name: str,
    id_attribute: str,
) -> None:
    driver_source = ogr.GetDriverByName("GPKG")
    data_source = driver_source.Open(source_path)
    driver_target = ogr.GetDriverByName("FlatGeobuf")
    data_target = driver_target.CreateDataSource(target_path)
    layer_source = data_source.GetLayerByName(source_layer_name)
    layer_target = data_target.CreateLayer(
        target_layer_name,
        layer_source.GetSpatialRef(),
        layer_source.GetLayerDefn().GetGeomType(),
    )
    for i in range(layer_source.GetLayerDefn().GetFieldCount()):
        field_defn = layer_source.GetLayerDefn().GetFieldDefn(i)
        if field_defn.GetName() == id_attribute:
            layer_target.CreateField(field_defn)
    while (feature := layer_source.GetNextFeature()) is not None:
        geometry = feature.GetGeometryRef()
        x_min, x_max, y_min, y_max = geometry.GetEnvelope()
        if layer_source.GetLayerDefn().GetGeomType() == ogr.wkbPolygon:
            bounds_wkt = f"POLYGON (({x_min} {y_min}, {x_max} {y_min}, {x_max} {y_max}, {x_min} {y_max}, {x_min} {y_min}))"
        elif layer_source.GetLayerDefn().GetGeomType() == ogr.wkbMultiPolygon:
            bounds_wkt = f"MULTIPOLYGON ((({x_min} {y_min}, {x_max} {y_min}, {x_max} {y_max}, {x_min} {y_max}, {x_min} {y_min})))"
        bounds_geometry = ogr.CreateGeometryFromWkt(bounds_wkt)
        bounds_feature = feature.Clone()
        bounds_feature.SetGeometry(bounds_geometry)
        layer_target.CreateFeature(bounds_feature)

    print(
        "created {} extent features at {}".format(
            layer_target.GetFeatureCount(), target_path
        )
    )

    data_source = None
    data_target = None


def extract_bc_trim() -> None:
    grid_dir = environ.get(
        "BC_TRIM_CONTROL_GRID_DIR",
        path.join(
            path.dirname(__file__),
            "..",
            "..",
            "mdp_bc_trim",
            "mdp_bc_trim",
            "control-data",
        ),
    )
    _extract(
        source_path=path.abspath(path.join(grid_dir, "grids.gpkg")),
        source_layer_name="BC-20000",
        target_path=path.abspath(path.join(grid_dir, "grid-extents-generated.fgb")),
        target_layer_name="bc-trim-20000",
        id_attribute="MAP_TILE",
    )


def extract_nts() -> None:
    grid_dir = environ.get(
        "NTS_CONTROL_GRID_DIR",
        path.join(
            path.dirname(__file__),
            "..",
            "..",
            "mdp_common",
            "mdp_common",
            "control-data",
        ),
    )
    _extract(
        source_path=path.abspath(path.join(grid_dir, "grids.gpkg")),
        source_layer_name="NTS-50000",
        target_path=path.abspath(path.join(grid_dir, nts_50000_grid_file_name)),
        target_layer_name=nts_50000_grid_layer_name,
        id_attribute=nts_50000_id_attribute_name,
    )


if __name__ == "__main__":
    from enum import Enum

    class GridTypes(str, Enum):
        BC = "bc"
        NTS = "nts"

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "grid_type",
        type=str,
        choices=(GridTypes.BC.value, GridTypes.NTS.value),
        help="Name of the grid to extract",
    )
    args = parser.parse_args()
    grid_type: Optional[GridTypes] = {entry.value: entry for entry in GridTypes}.get(
        args.grid_type
    )
    if grid_type is None:
        raise NotImplementedError("{} grid unsupported".format(args.grid_type))
    if args.grid_type == GridTypes.BC:
        extract_bc_trim()
    elif args.grid_type == GridTypes.NTS:
        extract_nts()
