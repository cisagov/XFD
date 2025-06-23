"""xfd_api.logger – centralised logging configuration for the backend.

This module is imported once during process start-up.  It:

1. Applies a single `logging.config.dictConfig` so every part of the
   backend shares the same handlers, levels, and format.
2. Exports `LOGGER`, a project-wide logger object obtained via
   `logging.getLogger("xfd")`.

All other modules should *only* use this logger (or a child created via
`LOGGER.getChild(...)`) instead of instantiating their own.
"""

# Standard Python Libraries
import logging
from logging.config import dictConfig

_DEFAULT_FMT = (
    "%(levelname)s %(asctime)s [%(name)s:%(lineno)d] " "%(request_id)s %(message)s"
)


def _configure_root_logger():
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
        "root": {  # <-- root logger
            "handlers": ["console"],
            "level": "INFO",
        },
    }

    dictConfig(config)


# run the configuration the first time this module is imported
_configure_root_logger()

# expose a project-wide logger symbol
LOGGER = logging.getLogger("xfd")
