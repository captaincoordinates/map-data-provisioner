from os import path
from typing import Final

nts_50000_grid_file_name: Final[str] = "nts-50000-grid.fgb"
nts_50000_grid_path: Final[str] = path.join(
    path.dirname(__file__), "control-data", ".merged", nts_50000_grid_file_name
)
nts_50000_grid_layer_name: Final[str] = "nts-50000"
nts_50000_id_attribute_name: Final[str] = "NTS_SNRC"
tmp_dir: Final[str] = path.join(path.sep, "tmp")
