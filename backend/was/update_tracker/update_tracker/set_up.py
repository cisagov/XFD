import qualysapi
import logging
import traceback
from configparser import ConfigParser
from pathlib import Path
from os import environ
from was_reports.utils.env import load_env_file
from was_reports.utils.qualys_config import ensure_qualys_config_file

load_env_file()

WAS_CONFIG_PATH = ensure_qualys_config_file(
    Path(environ.get(
        "WAS_CONFIG_PATH",
        str(Path(__file__).resolve().parents[2] / 'was_config.txt'),
    ))
)

config = ConfigParser()
config.read(WAS_CONFIG_PATH)

LOGFILE_PATH = config.get('was_files', 'dailywaslog')

# Set up Qualys API connection
qgc = qualysapi.connect(WAS_CONFIG_PATH)


# set up logging
logging.basicConfig(filename=LOGFILE_PATH, level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def log_exception(exc, **kwargs):
    """
    log details of an exception and additional context to dailywas.log

    Parameters
    ----------
    exc : Exception
        the exception object to be logged
    **kwargs
        Additional key-value pairs providing variable values and context
    """
    # log the exception
    logging.error(f"Exception occured: {str(exc)}")
    # log values of any additional variables
    for name, value in kwargs.items():
        logging.info(f"{name} = {value}")
    # log current stack frame details
    current_frame = traceback.extract_stack()[-3]
    logging.info(f"Frame details: {current_frame}")
