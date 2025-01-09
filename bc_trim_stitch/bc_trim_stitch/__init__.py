from logging import INFO, StreamHandler, basicConfig, getLevelName, getLevelNamesMapping
from os import environ
from sys import stdout
from typing import Final

from osgeo import gdal, ogr, osr

_default_log_level: Final[int] = INFO
_default_log_level_name: Final[str] = getLevelName(_default_log_level)


ogr.UseExceptions()
osr.UseExceptions()
gdal.UseExceptions()


def configure_logging() -> None:
    requested_log_level = environ.get("LOG_LEVEL", "info").upper()
    if requested_log_level not in getLevelNamesMapping():
        print(
            f"Invalid log level '{requested_log_level}', defaulting to '{_default_log_level_name}'"
        )
        requested_log_level = _default_log_level_name
    stdout_handler = StreamHandler(stream=stdout)
    handlers = [
        stdout_handler,
    ]
    log_level = getLevelNamesMapping()[requested_log_level]
    basicConfig(
        handlers=handlers,
        level=log_level,
        format="%(levelname)s %(asctime)s %(message)s",
        force=True,
    )


configure_logging()
