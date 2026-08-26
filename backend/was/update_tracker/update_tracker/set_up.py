import qualysapi
from openpyxl import load_workbook
import logging
import traceback
from configparser import ConfigParser
from pathlib import Path
from was_dynamodb.dynamodb import DynamoDB
from os import environ

WAS_CONFIG_PATH = Path(__file__).resolve().parents[2] / 'was_config.txt'

config = ConfigParser()
config.read(WAS_CONFIG_PATH)

LOGFILE_PATH = config.get('was_files', 'dailywaslog')

# POWERA_FOLDER = config.get('was_files', 'powerAutomateTriggers')

# get excel file paths
dailyReportsFilePath = config.get('was_files', 'dailyReportsFilePath')
# customerDataFilePath = config.get('was_files', 'customerDataFilePath')

# Set up Qualys API connection
qgc = qualysapi.connect(WAS_CONFIG_PATH)

# estbalish database connection
CUSTOMER_DATA = DynamoDB(
    environ.get("STAKEHOLDERS_TABLE_NAME"), environ.get("PROD_PROFILE")
)

# load workbooks
dailyReportsTracker = load_workbook(dailyReportsFilePath)
DAILY_REPORTS = dailyReportsTracker.active

specialCasesFilePath = config.get('was_files', 'specialCasesFilePath')


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
