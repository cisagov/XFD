#!/usr/bin/python3
"""Script for the part of the ASM sync process that needs to happen on a local machine."""

# Standard Python Libraries
import datetime
import logging
import os

# subprocess.run() calls use static, trusted inputs
import subprocess  # nosec b404
import time

# Third-Party Libraries
from asm_sync_local_helpers import (
    cyhy_db_connect,
    encrypt_string,
    get_ssm_parameter,
    retrieve_all_cyhy_data,
    upload_all_cyhy_data,
)

# Setup Logging
os.makedirs("./asm_sync_local_logs", exist_ok=True)
logging.basicConfig(
    filename="./asm_sync_local_logs/asm_sync_logfile.log",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S",
    level="INFO",
)
LOGGER = logging.getLogger(__name__)


def run_asm_sync_local():
    """Run the ASM sync step that needs to occur locally."""
    # Load all required parameters from user input/SSM parameter store
    param_dict = {
        # CYHY DB
        "cyhy_db_host": "localhost",
        "cyhy_db_database": "/crossfeed/staging/CYHY_DB_NAME",
        "cyhy_db_user": "/crossfeed/staging/CYHY_DB_USERNAME",
        "cyhy_db_password": "/crossfeed/staging-cd/CYHY_DB_CONN_DB_PASS",
        "cyhy_db_port": "27017",
        # S3
        "pe_encrypt_phrase": "/crossfeed/staging/PE_DB_PASSWORD_KEY",
        "pe_s3_bucket": "/crossfeed/staging/PE_S3_BUCKET",
    }
    for param in param_dict.keys():
        curr_param_val = param_dict.get(param)
        # If SSM param, retrieve actual value from AWS
        if curr_param_val.startswith("/crossfeed/"):
            ssm_resp = get_ssm_parameter(curr_param_val)
            param_dict[param] = ssm_resp
        # Make var an env var for easy access
        os.environ[param.upper()] = param_dict[param]

    LOGGER.info("")
    main_start_time = time.time()
    LOGGER.info("=== *** ASM Sync Local Step Starting *** ===")
    # Connect to the CyHy database
    LOGGER.info(">>> Establishing connection to CyHy Database")
    cyhy_db_conn = cyhy_db_connect()
    LOGGER.info(">>> CyHy Database connection established")
    # Retrieve and process all neccessary data from the CyHy DB
    LOGGER.info(">>> CyHy DB Data Retrieval Starting")
    [
        cyhy_orgs_df,
        cyhy_assets_df,
        cyhy_contacts_df,
        cyhy_child_parent_df,
        cyhy_sectors_info_df,
        cyhy_sectors_df,
    ] = retrieve_all_cyhy_data(cyhy_db_conn)
    LOGGER.info(">>> CyHy DB Data Retrieval Complete")
    # Encrypt the password column
    encrypt_phrase = os.environ.get("PE_ENCRYPT_PHRASE")
    cyhy_orgs_df["password"] = cyhy_orgs_df["password"].apply(
        lambda value: encrypt_string(value, encrypt_phrase)
    )
    # Upload all processed CyHy data to S3 bucket (no PE DB access from local machine)
    LOGGER.info(">>> CyHy Data Upload to S3 Starting")
    upload_all_cyhy_data(
        cyhy_orgs_df,
        cyhy_assets_df,
        cyhy_contacts_df,
        cyhy_child_parent_df,
        cyhy_sectors_info_df,
        cyhy_sectors_df,
    )
    LOGGER.info(">>> CyHy Data Upload to S3 Complete")
    # Close connection to CyHy DB
    subprocess.run(  # nosec B603
        ["/usr/bin/killall", "SCREEN"],
        check=True,
        timeout=30,
    )
    main_end_time = time.time()
    LOGGER.info(
        f"Execution time for ASM sync local step: {str(datetime.timedelta(seconds=(main_end_time - main_start_time)))} (H:M:S)"
    )
    LOGGER.info("=== *** ASM Sync Local Step Complete *** ===")


def main():
    """Run local step of the ASM Sync process (must run on local machine)."""
    run_asm_sync_local()


if __name__ == "__main__":
    main()
