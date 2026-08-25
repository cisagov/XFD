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
main_log = logging.getLogger(__name__)


def run_asm_sync_local():
    """Run the ASM sync step that needs to occur locally."""
    # Load all required parameters from user input/SSM parameter store
    cyhy_db_pkey_loc = input(
        "Enter filepath to your private key for the CyHy DB (e.g. /Users/<user>/.ssh/<pkey>): "
    )
    cyhy_db_pkey_pass = input(
        "Enter the password to your private key for the CyHy DB (leave blank if no password): "
    )
    pe_s3_bucket = input("Enter the name of P&E's S3 bucket: ")
    param_dict = {
        # CYHY DB
        "cyhy_db_host": "localhost",
        "cyhy_db_database": "cyhy",
        "cyhy_db_user": "cyhy_ops",
        "cyhy_db_password": "/crossfeed/staging-cd/CYHY_DB_CONN_DB_PASS",
        "cyhy_db_port": "27017",
        "cyhy_db_pkey_location": cyhy_db_pkey_loc,
        "cyhy_db_pkey_pass": cyhy_db_pkey_pass,
        "pe_s3_bucket": pe_s3_bucket,
        # WHOISXML
        "whoisxml_key": "/crossfeed/staging/WHOIS_XML_KEY",
    }
    for param in param_dict.keys():
        curr_param_val = param_dict.get(param)
        # If SSM param, retrieve actual value from AWS
        if curr_param_val.startswith("/crossfeed/"):
            ssm_resp = get_ssm_parameter(curr_param_val)
            param_dict[param] = ssm_resp
        # Make var an env var for easy access
        os.environ[param.upper()] = param_dict[param]

    main_log.info("")
    main_start_time = time.time()
    main_log.info("=== *** ASM Sync Local Step Starting *** ===")

    # Connect to the CyHy database
    main_log.info(">>> Establishing connection to CyHy Database")
    cyhy_db_conn = cyhy_db_connect()
    main_log.info(">>> CyHy Database connection established")
    # Retrieve and process all neccessary data from the CyHy DB
    main_log.info(">>> CyHy DB Data Retrieval Starting")
    [
        cyhy_orgs_df,
        cyhy_assets_df,
        cyhy_contacts_df,
        cyhy_child_parent_df,
        cyhy_sectors_info_df,
        cyhy_sectors_df,
    ] = retrieve_all_cyhy_data(cyhy_db_conn)
    main_log.info(">>> CyHy DB Data Retrieval Complete")

    # Upload all processed CyHy data to S3 bucket (no PE DB access from local machine)
    main_log.info(">>> CyHy Data Upload to S3 Starting")
    upload_all_cyhy_data(
        cyhy_orgs_df,
        cyhy_assets_df,
        cyhy_contacts_df,
        cyhy_child_parent_df,
        cyhy_sectors_info_df,
        cyhy_sectors_df,
    )
    main_log.info(">>> CyHy Data Upload to S3 Complete")

    subprocess.run(  # nosec B603
        ["/usr/bin/killall", "SCREEN"],
        check=True,
        timeout=30,
    )
    main_end_time = time.time()
    main_log.info(
        f"Execution time for ASM sync local step: {str(datetime.timedelta(seconds=(main_end_time - main_start_time)))} (H:M:S)"
    )
    main_log.info("=== *** ASM Sync Local Step Complete *** ===")


def main():
    """Run local step of the ASM Sync process (must run on local machine)."""
    run_asm_sync_local()


if __name__ == "__main__":
    main()
