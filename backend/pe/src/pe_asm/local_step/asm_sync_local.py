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
    insert_all_cyhy_data,
    local_db_connect,
    pe_db_connect,
    retrieve_all_cyhy_data,
)
from asm_sync_local_query import (
    add_tables_default_uid,
    add_tables_uniq_constraint,
    identify_org_asset_changes,
    install_pgcrypto,
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


def run_asm_sync_local(local_db=True):
    """Run the ASM sync step that needs to occur locally."""
    # Load all required parameters from user input/SSM parameter store
    pe_db_pkey_loc = input(
        "Enter filepath to your private key for the PE DB (e.g. /Users/<user>/.ssh/<pkey>): "
    )
    pe_db_pkey_pass = input(
        "Enter the password to your private key for the PE DB (leave blank if no password): "
    )
    cyhy_db_pkey_loc = input(
        "Enter filepath to your private key for the CyHy DB (e.g. /Users/<user>/.ssh/<pkey>): "
    )
    cyhy_db_pkey_pass = input(
        "Enter the password to your private key for the CyHy DB (leave blank if no password): "
    )
    param_dict = {
        # EC2
        "pe_ec2_inst_id": "/crossfeed/staging-cd/PE_EC2_INST_ID",
        # PE DB
        "pe_db_host": "/crossfeed/staging-cd/PE_DB_CONN_HOST",
        "pe_db_database": "pe",
        "pe_db_user": "pe",
        "pe_db_password": "/crossfeed/staging-cd/PE_DB_CONN_DB_PASS",
        "pe_db_port": "5432",
        "pe_db_pkey_location": pe_db_pkey_loc,
        "pe_db_pkey_pass": pe_db_pkey_pass,
        "pe_db_password_key": "/crossfeed/staging-cd/PE_DB_CONN_PASS_KEY",
        # LOCAL DB
        "local_db_host": "localhost",
        "local_db_database": "pe",
        "local_db_user": "pe",
        "local_db_password": "password",  # TESTING
        "local_db_port": "5432",
        # CYHY DB
        "cyhy_db_host": "localhost",
        "cyhy_db_database": "cyhy",
        "cyhy_db_user": "cyhy_ops",
        "cyhy_db_password": "/crossfeed/staging-cd/CYHY_DB_CONN_DB_PASS",
        "cyhy_db_port": "27017",
        "cyhy_db_pkey_location": cyhy_db_pkey_loc,
        "cyhy_db_pkey_pass": cyhy_db_pkey_pass,
        # # WHOISXML
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
    # Connect to the P&E database
    main_log.info(">>> Establishing connection to the PE database")
    if not local_db:
        # PE DB connection
        main_log.warning("*** Real PE DB connection requested ***")
        time.sleep(5)  # time to cancel
        pe_db_conn = pe_db_connect()
    else:
        # Local DB connection
        main_log.info("*** Local DB connection requested ***")
        pe_db_conn = local_db_connect()
        install_pgcrypto(pe_db_conn)
        add_tables_uniq_constraint(pe_db_conn)
        add_tables_default_uid(pe_db_conn)
    main_log.info(">>> PE database connection established")

    # Connect to the CyHy database
    main_log.info(">>> Establishing connection to CyHy Database")
    cyhy_db_conn = cyhy_db_connect()
    main_log.info(">>> CyHy Database connection established")
    # Retrieve and process all neccessary data from the CyHy DB
    main_log.info(">>> CyHy DB Data Retrieval Starting")
    [
        assets_df,
        child_parent_dict,
        contacts_df,
        cyhy_agency_df,
        sector_info_list,
        sector_list,
    ] = retrieve_all_cyhy_data(cyhy_db_conn)
    main_log.info(">>> CyHy DB Data Retrieval Complete")
    # Insert/Update all processed CyHy data into the PE DB
    main_log.info(">>> Insertion of CyHy Data into PE DB Starting")
    insert_all_cyhy_data(
        pe_db_conn,
        assets_df,
        child_parent_dict,
        contacts_df,
        cyhy_agency_df,
        sector_info_list,
        sector_list,
    )
    main_log.info(">>> Insertion of CyHy Data into PE DB Complete")
    # Identify which assets in cyhy_db_asset are/aren't current
    main_log.info(">>> Identification of cyhy_db_asset Changes Starting")
    identify_org_asset_changes(pe_db_conn)
    main_log.info(">>> Identification of cyhy_db_asset Changes Complete")
    # End ASM Sync local step and clean up
    pe_db_conn.close()
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
    """Run local (macbook, not EC2) step of the ASM Sync process."""
    # False = Real P&E DB, True = Local DB
    run_asm_sync_local(True)


if __name__ == "__main__":
    main()
