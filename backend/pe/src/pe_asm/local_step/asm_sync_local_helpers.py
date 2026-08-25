"""All helper functions needed for the ASM Sync local process."""

# Standard Python Libraries
import datetime
import logging
import os
from pathlib import Path

# subprocess.run() calls use trusted inputs
import subprocess  # nosec B404
import time

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from pymongo import MongoClient

# Setup Logging
main_log = logging.getLogger(__name__)


def get_ssm_parameter(parameter_name):
    """Retrieve value from SSM parameter store."""
    # Initialize the Systems Manager client
    ssm_client = boto3.client("ssm")
    try:
        # Fetch the parameter
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True,
        )
        # Extract and return the value
        return response["Parameter"]["Value"]
    except ClientError as e:
        main_log.error(f"Error retrieving SSM parameter {parameter_name}: {e}")
        raise


def cyhy_db_connect():
    """Connect to CyHy Mongo database."""
    try:
        # Create screen to make SSH connection to CyHy env
        main_log.info("Creating screen to connect to CyHy DB")
        screen_connect_cyhy = (Path.home() / ".bin" / "screenConnectCyHy").resolve(
            strict=True
        )
        subprocess.run(  # nosec B603
            [str(screen_connect_cyhy)],
            check=True,
            timeout=30,
        )
        main_log.info("Screen to connect to CyHy DB has been created")
        time.sleep(3)
        # Make connection to CyHy DB
        main_log.info("Attempting connection to CyHy DB")
        host = os.environ.get("CYHY_DB_HOST")
        user = os.environ.get("CYHY_DB_USER")
        password = os.environ.get("CYHY_DB_PASSWORD")
        port = os.environ.get("CYHY_DB_PORT")
        dbname = os.environ.get("CYHY_DB_DATABASE")
        cyhy_conn_string = f"mongodb://{user}:{password}@{host}:{port}/{dbname}"
        mongo_client = MongoClient(cyhy_conn_string)
        main_log.info("CyHy DB connection successful")
        # Return cyhy database object
        return mongo_client["cyhy"]
    except Exception as e:
        main_log.error(e)
        main_log.error(
            "Failed connecting to the CyHy database. Make sure you have the ssh connection running"
        )


def retrieve_all_cyhy_data(cyhy_db):
    """Retrieve all data necessary for the ASM Sync from the CyHy database."""
    collection = cyhy_db["requests"]
    # Retrieve FCEB list CyHy DB
    fceb_query = {"_id": "EXECUTIVE"}
    fceb_doc = collection.find(fceb_query)
    for row in fceb_doc:
        fceb_list = row["children"]
    main_log.info("Retrieved FCEB list from CyHy DB")
    # Start retrieving organization data from CyHy DB
    cyhy_request_data = collection.find()
    # Create return variables
    assets = []
    child_parent_dict = {}
    contact_list = []
    cyhy_agencies = []
    sector_info_list = []
    sector_list = []
    # Loop through all CyHy agencies
    for cyhy_request in cyhy_request_data:
        # If the CyHy org has a type (and network?), proceed with data retrieval
        if cyhy_request["agency"].get("type"):
            # Get organization's general info
            agency = {
                "name": cyhy_request["agency"]["name"],
                "cyhy_db_name": cyhy_request["_id"],
                "password": cyhy_request["key"],
                "agency_type": cyhy_request["agency"].get("type"),
                "retired": cyhy_request.get("retired", False),
                "receives_cyhy_report": "CYHY" in cyhy_request["report_types"],
                "receives_bod_report": "BOD" in cyhy_request["report_types"],
                "receives_cybex_report": "CYBEX" in cyhy_request["report_types"],
                "is_parent": len(cyhy_request.get("children", [])) > 0,
                "fceb": cyhy_request["_id"] in fceb_list,
                "cyhy_period_start": cyhy_request.get("period_start"),
                # new fields
                "location_name": cyhy_request["agency"]
                .get("location", {})
                .get("name", None),
                "county": cyhy_request["agency"]
                .get("location", {})
                .get("county", None),
                "county_fips": cyhy_request["agency"]
                .get("location", {})
                .get("county_fips", None),
                "state_abbreviation": cyhy_request["agency"]
                .get("location", {})
                .get("state", None),
                "state_fips": cyhy_request["agency"]
                .get("location", {})
                .get("state_fips", None),
                "state_name": cyhy_request["agency"]
                .get("location", {})
                .get("state_name", None),
                "country": cyhy_request["agency"]
                .get("location", {})
                .get("country", None),
                "country_name": cyhy_request["agency"]
                .get("location", {})
                .get("country_name", None),
            }
            cyhy_agencies.append(agency)
            # Get organization's children/subsidiaries if it has any
            if cyhy_request.get("children"):
                for child in cyhy_request["children"]:
                    # Save child w/ the parent's cyhy_db_id
                    child_parent_dict[child] = cyhy_request["_id"]
            # Get organization's contact info
            for contact in cyhy_request["agency"]["contacts"]:
                if not contact.get("type"):
                    contact["type"] = "unspecified"
                contact_object = {
                    "org_id": cyhy_request["_id"],
                    "org_name": cyhy_request["agency"]["name"],
                    "phone": contact.get("phone"),
                    "contact_type": contact.get("type"),
                    "email": contact.get("email"),
                    "name": contact.get("name"),
                    "date_pulled": datetime.datetime.today().date(),
                }
                contact_list.append(contact_object)
            # Get organization's network/CIDR/IP info
            for network in cyhy_request["networks"]:
                cidr_dict = {
                    "org_id": cyhy_request["_id"],
                    "org_name": cyhy_request["agency"]["name"],
                    "contact": str(cyhy_request["agency"]["contacts"]),
                    "network": network,
                    "first_seen": datetime.datetime.today().date(),
                    "last_seen": datetime.datetime.today().date(),
                }
                if "/" in network:
                    cidr_dict["type"] = "cidr"
                else:
                    cidr_dict["type"] = "ip"
                assets.append(cidr_dict)
        # If the CyHy org doesn't have a type (and network?), it's actually a sector/category and will be put in a separate table
        else:
            # Add sector id to sector_list
            sector_list.append(cyhy_request["_id"])
            # Create a dictionary of sector data
            sector_dict = {
                "id": cyhy_request["_id"],
                "acronym": cyhy_request["agency"].get("acronym", ""),
                "name": cyhy_request["agency"].get("name", "No Name"),
                "children": cyhy_request.get("children", []),
                "password": cyhy_request.get("key", ""),
                "retired": cyhy_request.get("retired", False),
            }
            # If no contact is found save "None"
            if len(cyhy_request["agency"]["contacts"]) == 0:
                sector_dict["email"] = None
                sector_dict["contact_name"] = None
            # If only one contact is available save it to the dictionary
            elif len(cyhy_request["agency"]["contacts"]) == 1:
                sector_dict["email"] = cyhy_request["agency"]["contacts"][0]["email"]
                sector_dict["contact_name"] = cyhy_request["agency"]["contacts"][0][
                    "name"
                ]
            # If multiple contacts are identified save the DISTRO email to the dictionary
            elif len(cyhy_request["agency"]["contacts"]) > 1:
                distro_email = None
                distro_name = None
                # Look for distro contact
                for i in range(len(cyhy_request["agency"]["contacts"])):
                    if cyhy_request["agency"]["contacts"][i]["type"] == "DISTRO":
                        distro_email = cyhy_request["agency"]["contacts"][i]["email"]
                        distro_name = cyhy_request["agency"]["contacts"][i]["name"]
                # If none of the contacts were marked as distros, just use the first contact
                if distro_email is None:
                    distro_email = cyhy_request["agency"]["contacts"][0]["email"]
                    distro_name = cyhy_request["agency"]["contacts"][0]["name"]
                # Add distro info to sector dict
                sector_dict["email"] = distro_email
                sector_dict["contact_name"] = distro_name
            # Since ROOT and DOD are not sectors ignore them
            if sector_dict["acronym"] in ["ROOT", "DOD"]:
                continue
            else:
                # Otherwise, append dict for this sector to list
                sector_info_list.append(sector_dict)

    # Log stats
    main_log.info("Retrieved bulk data from CyHy DB")
    main_log.info(f"Total organizations retrieved from CyHyDB: {len(cyhy_agencies)}")
    main_log.info(f"Total organization assets retrieved from CyHy DB: {len(assets)}")
    main_log.info(f"Total sectors retrieved from CyHy DB: {len(sector_list)}")

    # Convert output to dataframes
    orgs_df = pd.DataFrame(cyhy_agencies)
    assets_df = pd.DataFrame(assets)
    contacts_df = pd.DataFrame(contact_list)
    child_parent_df = pd.DataFrame(
        child_parent_dict.items(), columns=["child", "parent"]
    )
    sectors_info_df = pd.DataFrame(sector_info_list)
    sectors_df = pd.DataFrame(sector_list, columns=["sectors"])

    # Return processed data
    return [
        orgs_df,
        assets_df,
        contacts_df,
        child_parent_df,
        sectors_info_df,
        sectors_df,
    ]


def upload_cyhy_data_to_s3(s3_client, bucket, current_date, local_file):
    """Upload CyHy DB data file to S3 under asm_sync_local_runs/<curent_date>/<file_name>."""
    try:
        filename = os.path.basename(local_file)
        s3_path = f"asm_sync_local_runs/{current_date}/{filename}"
        s3_client.upload_file(local_file, bucket, s3_path)
        main_log.info("Uploaded %s to s3://%s/%s", filename, bucket, s3_path)
    except Exception as e:
        main_log.error("Error uploading file to S3: %s", e)


def upload_all_cyhy_data(
    orgs_df,
    assets_df,
    contacts_df,
    child_parent_df,
    sectors_info_df,
    sectors_df,
):
    """Take all the ASM Sync data retrieved from the CyHy database and upload it to the S3 bucket."""
    # Create folder to save CyHy data from this run
    curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
    curr_file_dir = Path(__file__).resolve().parent
    local_save_folder = curr_file_dir / "asm_sync_local_runs" / curr_date
    local_save_folder.mkdir(parents=True, exist_ok=True)
    # Save dataframes as local files for uploading
    orgs_file = str(local_save_folder) + f"/cyhy_orgs_{curr_date}.csv"
    assets_file = str(local_save_folder) + f"/cyhy_assets_{curr_date}.csv"
    contacts_file = str(local_save_folder) + f"/cyhy_contacts_{curr_date}.csv"
    child_parent_file = str(local_save_folder) + f"/cyhy_child_parent_{curr_date}.csv"
    sectors_info_file = str(local_save_folder) + f"/cyhy_sectors_info_{curr_date}.csv"
    sectors_file = str(local_save_folder) + f"/cyhy_sectors_{curr_date}.csv"
    orgs_df.to_csv(orgs_file)
    assets_df.to_csv(assets_file)
    contacts_df.to_csv(contacts_file)
    child_parent_df.to_csv(child_parent_file)
    sectors_info_df.to_csv(sectors_info_file)
    sectors_df.to_csv(sectors_file)
    # Upload locally saved files to S3
    s3_client = boto3.client("s3")
    bucket = os.environ.get("PE_S3_BUCKET")
    local_files = [
        orgs_file,
        assets_file,
        contacts_file,
        child_parent_file,
        sectors_info_file,
        sectors_file,
    ]
    for local_file in local_files:
        upload_cyhy_data_to_s3(s3_client, bucket, curr_date, local_file)
