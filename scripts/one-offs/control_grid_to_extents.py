from os import environ, path
from typing import Final

from osgeo import ogr

ogr.UseExceptions()

grid_dir: Final[str] = environ.get(
    "CONTROL_GRID_DIR",
    path.join(
        path.dirname(__file__),
        "..",
        "..",
        "mdp_bc_trim",
        "mdp_bc_trim",
        "control-data",
    ),
)

driver_source = ogr.GetDriverByName("GPKG")
data_source = driver_source.Open(path.join(grid_dir, "grids.gpkg"))
driver_target = ogr.GetDriverByName("FlatGeobuf")
data_target = driver_target.CreateDataSource(path.join(grid_dir, "grid-extents.fgb"))
layer_source = data_source.GetLayerByName("BC-20000")
layer_target = data_target.CreateLayer(
    "bc-trim-20000",
    layer_source.GetSpatialRef(),
    layer_source.GetLayerDefn().GetGeomType(),
)
for i in range(layer_source.GetLayerDefn().GetFieldCount()):
    field_defn = layer_source.GetLayerDefn().GetFieldDefn(i)
    if field_defn.GetName() == "MAP_TILE":
        layer_target.CreateField(field_defn)
while (feature := layer_source.GetNextFeature()) is not None:
    geometry = feature.GetGeometryRef()
    x_min, x_max, y_min, y_max = geometry.GetEnvelope()
    bounds_wkt = f"POLYGON (({x_min} {y_min}, {x_max} {y_min}, {x_max} {y_max}, {x_min} {y_max}, {x_min} {y_min}))"
    bounds_geometry = ogr.CreateGeometryFromWkt(bounds_wkt)
    bounds_feature = feature.Clone()
    bounds_feature.SetGeometry(bounds_geometry)
    layer_target.CreateFeature(bounds_feature)

print("created {} extent features".format(layer_target.GetFeatureCount()))

data_source = None
data_target = None
