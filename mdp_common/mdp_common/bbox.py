from dataclasses import dataclass
from typing import Final

default_crs_code: Final[str] = "EPSG:4326"


@dataclass
class BBOX:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    crs_code: str = default_crs_code

    @property
    def as_wkt(self) -> str:
        return "POLYGON (({x_min} {y_min},{x_max} {y_min},{x_max} {y_max},{x_min} {y_max},{x_min} {y_min}))".format(
            x_min=self.x_min,
            y_min=self.y_min,
            x_max=self.x_max,
            y_max=self.y_max,
        )

    @property
    def as_path_part(self) -> str:
        return "{x_min}-{y_min}-{x_max}-{y_max}".format(
            x_min=self.x_min,
            y_min=self.y_min,
            x_max=self.x_max,
            y_max=self.y_max,
        )
