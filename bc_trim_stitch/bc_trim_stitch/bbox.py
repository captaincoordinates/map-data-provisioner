from dataclasses import dataclass
from typing import Final

default_crs_code: Final[str] = "EPSG:4326"


@dataclass
class BBOX:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    crs_code: str = default_crs_code
