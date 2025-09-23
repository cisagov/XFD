"""xfd_django.helpers.log_helpers project‑wide logging helpers.

This module registers ``XfdLogger`` as the default logger class and
installs a factory that automatically prefixes every logger name with
“xfd.” so the central LOGGING configuration can target the entire
project with a single stanza.
"""
# Standard Python Libraries
import logging


class XfdLogger(logging.Logger):
    """Logger subclass whose children automatically live under ``xfd.``."""

    def getChild(self, suffix: str):
        """Return a child logger, making sure its name starts with ``xfd.``."""
        if suffix and not suffix.startswith("xfd."):
            suffix = "xfd.{}".format(suffix)
        return super().getChild(suffix)


def install_xfd_prefix():
    """
    Make ``logging.getLogger()`` return loggers in the ``xfd.`` hierarchy.

    Must be called **once**, early in ``settings.py`` *before* any project
    modules import ``logging``.
    """
    logging.setLoggerClass(XfdLogger)

    _orig_get_logger = logging.getLogger

    def prefixed_get_logger(name=None):
        if name and not name.startswith("xfd."):
            name = "xfd.{}".format(name)
        if name is None:
            name = "xfd"
        return _orig_get_logger(name)

    logging.getLogger = prefixed_get_logger
