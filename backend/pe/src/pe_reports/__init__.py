"""The pe_reports library."""

# Standard Python Libraries
import logging
from logging.handlers import RotatingFileHandler

CENTRAL_LOGGING_FILE = "pe_reports_logging.log"
DEBUG = False

# Setup Rotating Logging
"""Set up logging and call the run_pe_script function."""
if DEBUG is True:
    level = "DEBUG"
else:
    level = "INFO"
# Logging will rotate at 2GB
logging.basicConfig(
    format="%(asctime)s - %(process)d %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=level,
    handlers=[
        RotatingFileHandler(CENTRAL_LOGGING_FILE, maxBytes=2000000, backupCount=15)
    ],
)
