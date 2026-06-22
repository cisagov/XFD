"""Shared PE reporting utilities."""

# Standard Python Libraries
import logging
from logging.handlers import RotatingFileHandler

CENTRAL_LOGGING_FILE = "pe_reports_logging.log"
DEBUG = False

level = "DEBUG" if DEBUG else "INFO"
logging.basicConfig(
    format="%(asctime)s - %(process)d %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=level,
    handlers=[
        RotatingFileHandler(CENTRAL_LOGGING_FILE, maxBytes=2000000, backupCount=15)
    ],
)
