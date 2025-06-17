
# backend/src/xfd_django/xfd_api/logger.py
import logging
from logging.config import dictConfig

_DEFAULT_FMT = (
    "%(levelname)s %(asctime)s [%(name)s:%(lineno)d] "
    "%(request_id)s %(message)s"
)

def _configure_root_logger() -> None:
    """
    Configure the root logger once, at import time.
    Other modules should only ever `import LOGGER`.
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": _DEFAULT_FMT,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
        },
        "root": {                # <-- root logger
                "handlers": ["console"],
                "level": "INFO",
        },
    }

    dictConfig(config)

# run the configuration the first time this module is imported
_configure_root_logger()

# expose a project-wide logger symbol
LOGGER = logging.getLogger("xfd")
