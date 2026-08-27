"""Retrieve the latest CyHy DB data from S3 and upsert it into the PE DB."""

# Standard Python Libraries
import ast
import base64
import datetime
import hashlib
from io import StringIO
import logging
import os
from pathlib import Path

# Third-Party Libraries
import boto3
from cryptography.fernet import Fernet, InvalidToken
import pandas as pd
from pe_asm.remote_step.asm_sync_remote_query import (
    add_sector_hierachy,
    connect,
    identify_org_asset_changes,
    insert_assets,
    insert_contacts,
    insert_cyhy_agencies,
    insert_dotgov_domains,
    insert_sector_org_relationship,
    insert_sectors,
    query_pe_orgs,
    query_pe_sectors,
    update_child_parent_orgs,
    update_fceb_child_status,
    update_scan_status,
)
import requests

# Setup logging
LOGGER = logging.getLogger(__name__)


def download_cyhy_data_from_s3(s3_client, bucket, s3_file_path, local_folder):
    """Download the specified CyHy DB data file from S3 bucket."""
    try:
        filename = os.path.basename(s3_file_path)
        local_file_path = os.path.join(local_folder, filename)
        s3_client.download_file(bucket, s3_file_path, local_file_path)
        LOGGER.info(
            "Downloaded s3://%s/%s to %s", bucket, s3_file_path, local_file_path
        )
    except Exception as e:
        LOGGER.error("Error downloading file from S3: %s", e)


def decrypt_string(encrypted_value: str, passphrase: str) -> str:
    """Decrypt a string using the passphrase used during encryption."""
    key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode("utf-8")).digest())
    try:
        decrypted_value = Fernet(key).decrypt(encrypted_value.encode("utf-8"))
    except InvalidToken as exception:
        raise ValueError(
            "Decryption failed because the passphrase is incorrect or encrypted value was modified."
        ) from exception

    return decrypted_value.decode("utf-8")


def dotgov_domains():
    """Get list of dotgov domains from the GitHub repository."""
    dotgov_url = (
        "https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-federal.csv"
    )
    response = requests.get(dotgov_url, timeout=60)
    response.raise_for_status()
    dataframe = pd.read_csv(StringIO(response.text))
    dataframe = dataframe.rename(
        columns={
            "Domain name": "domain_name",
            "Domain type": "domain_type",
            "Organization name": "agency",
            "Suborganization name": "organization",
            "City": "city",
            "State": "state",
            "Security contact email": "security_contact_email",
        }
    )
    return dataframe


def insert_all_cyhy_data(
    pe_db_conn,
    assets_df,
    child_parent_dict,
    contacts_df,
    cyhy_agency_df,
    sector_info_list,
    sector_list,
):
    """Take all the ASM Sync data retrieved from the CyHy database and insert/update it into the PE database."""
    db_pass = os.environ.get("PE_DB_PASSWORD_KEY")
    # Insert all CyHy DB sector data into the PE DB
    insert_sectors(pe_db_conn, db_pass, sector_info_list)
    # Query all PE sectors
    pe_sectors = query_pe_sectors(pe_db_conn)
    # Create a list of sector ids where run_scorecards = True
    pe_sectors["run_scorecards"] = pe_sectors["run_scorecards"].fillna(False)
    scorecard_sectors = pe_sectors.loc[pe_sectors["run_scorecards"], "id"].tolist()

    # Create a list of all orgs belonging to sectors that are flagged to run_scorecards
    scorecard_orgs = []
    for sector in sector_info_list:
        if sector["id"] in scorecard_sectors:
            scorecard_orgs += sector["children"]
    # Add column marking scorecard orgs
    cyhy_agency_df["scorecard"] = cyhy_agency_df["cyhy_db_name"].isin(scorecard_orgs)
    # Insert CyHy DB asset data into the PE DB
    insert_assets(pe_db_conn, assets_df)
    # Deduplicate cyhy contact data
    contacts_df.drop_duplicates(
        subset=["org_id", "name", "contact_type", "email"],
        inplace=True,
        ignore_index=True,
    )
    # Insert CyHy DB contact data into PE DB
    insert_contacts(pe_db_conn, contacts_df)
    # Insert CyHy DB organziation data into the PE DB
    insert_cyhy_agencies(pe_db_conn, db_pass, cyhy_agency_df)
    # Query all PE organizations
    pe_orgs = query_pe_orgs(pe_db_conn)
    # Build sector child and sub-sector lists
    sector_child_list = []
    sub_sector_list = []
    for sec in sector_info_list:
        # save uid of the current sector
        sector_uid = pe_sectors.loc[
            pe_sectors["acronym"] == sec["acronym"], "sector_uid"
        ].item()
        # loop through this sector's children, they can be orgs or sectors
        for child_agency in sec["children"]:
            # If child is a sector
            if child_agency in sector_list:
                # ignore child if DOD
                if child_agency == "DOD":
                    continue
                # append sector-sector relationship
                sub_sector_list.append(
                    (
                        pe_sectors.loc[
                            pe_sectors["acronym"] == child_agency, "sector_uid"
                        ].item(),
                        sector_uid,
                    )
                )
            # if the child is an org
            else:
                # skip if no org_uid available ***
                if (
                    len(
                        pe_orgs.loc[
                            pe_orgs["cyhy_db_name"] == child_agency, "organizations_uid"
                        ].index
                    )
                    == 0
                ):
                    continue
                # grab the org_uid
                child_uid = pe_orgs.loc[
                    pe_orgs["cyhy_db_name"] == child_agency, "organizations_uid"
                ].item()
                # append to child_sector relationship list
                if child_uid and sector_uid:
                    sector_child_list.append(
                        (
                            sector_uid,
                            child_uid,
                            datetime.datetime.today().date(),
                            datetime.datetime.today().date(),
                        )
                    )
    # Insert sector-org relationships into the PE DB
    insert_sector_org_relationship(pe_db_conn, sector_child_list)
    # Add relationship between sectors to the PE DB, not allowing duplicate parents
    child_list = []
    for relationship in sub_sector_list:
        if relationship[0] not in child_list:
            add_sector_hierachy(pe_db_conn, relationship[0], relationship[1])
            child_list.append(relationship[0])
    LOGGER.info(
        "Parent_sector_uid fields updated successfully using add_sector_hierarchy()"
    )
    # For each parent/child relationship,
    # add the parent's org_uid to the child org
    child_parent_ct = 0
    scan_status_ct = 0
    fceb_child_ct = 0
    for child_name, parent_name in child_parent_dict.items():
        # Get parent uid
        parent_uid = pe_orgs.loc[
            pe_orgs["cyhy_db_name"] == parent_name, "organizations_uid"
        ].item()
        # add parent uid to child org's record
        update_child_parent_orgs(pe_db_conn, parent_uid, child_name)
        child_parent_ct += 1
        # Check if parent org is reported on
        parent_report_on = pe_orgs.loc[
            pe_orgs["cyhy_db_name"] == parent_name, "report_on"
        ].item()
        # Check if parent org is FCEB
        parent_fceb = pe_orgs.loc[pe_orgs["cyhy_db_name"] == parent_name, "fceb"].item()
        # Update child's run_scans field
        if parent_report_on:
            update_scan_status(pe_db_conn, child_name)
            scan_status_ct += 1
        # Update child's fceb_child field
        if parent_fceb:
            update_fceb_child_status(pe_db_conn, child_name)
            fceb_child_ct += 1

    LOGGER.info(
        f"{child_parent_ct} child-parent relationships updated successfully using update_child_parent_orgs()"
    )
    LOGGER.info(
        f"{scan_status_ct} scan statuses updated successfully using update_scan_status()"
    )
    LOGGER.info(
        f"{fceb_child_ct} FCEB child statuses updated successfully using update_fceb_child_status()"
    )

    # Scrape dot gov domains and insert into P&E database
    dotgov_df = dotgov_domains()
    insert_dotgov_domains(pe_db_conn, dotgov_df)


def import_cyhy_from_s3():
    """Downlaod the latest CyHy DB data from S3 and upsert it into the PE DB."""
    # Create folder to save S3 data to
    curr_file_dir = Path(__file__).resolve().parent
    local_save_folder = curr_file_dir / "asm_sync_s3_data"
    local_save_folder.mkdir(parents=True, exist_ok=True)
    # Download the latest CyHy DB data from S3
    curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
    s3_path = "asm_sync_local_runs/%s" % curr_date
    orgs_file = s3_path + f"/cyhy_orgs_{curr_date}.csv"
    assets_file = s3_path + f"/cyhy_assets_{curr_date}.csv"
    contacts_file = s3_path + f"/cyhy_contacts_{curr_date}.csv"
    child_parent_file = s3_path + f"/cyhy_child_parent_{curr_date}.csv"
    sectors_info_file = s3_path + f"/cyhy_sectors_info_{curr_date}.csv"
    sectors_file = s3_path + f"/cyhy_sectors_{curr_date}.csv"
    s3_file_paths = [
        orgs_file,
        assets_file,
        contacts_file,
        child_parent_file,
        sectors_info_file,
        sectors_file,
    ]
    s3_client = boto3.client("s3")
    bucket = os.environ.get("PE_S3_BUCKET")
    for s3_file_path in s3_file_paths:
        download_cyhy_data_from_s3(s3_client, bucket, s3_file_path, local_save_folder)
    # Read data files that were downloaded from S3
    orgs_df = pd.read_csv(
        str(local_save_folder) + f"/cyhy_orgs_{curr_date}.csv", index_col=0
    )
    assets_df = pd.read_csv(
        str(local_save_folder) + f"/cyhy_assets_{curr_date}.csv", index_col=0
    )
    contacts_df = pd.read_csv(
        str(local_save_folder) + f"/cyhy_contacts_{curr_date}.csv", index_col=0
    )
    child_parent_df = pd.read_csv(
        str(local_save_folder) + f"/cyhy_child_parent_{curr_date}.csv", index_col=0
    )
    sectors_info_df = pd.read_csv(
        str(local_save_folder) + f"/cyhy_sectors_info_{curr_date}.csv", index_col=0
    )
    sectors_df = pd.read_csv(
        str(local_save_folder) + f"/cyhy_sectors_{curr_date}.csv", index_col=0
    )
    # Additional formatting
    orgs_df["county_fips"] = orgs_df["county_fips"].fillna("")
    decrypt_phrase = os.environ.get("PE_DB_PASSWORD_KEY")
    orgs_df["password"] = orgs_df["password"].apply(
        lambda value: decrypt_string(value, decrypt_phrase)
    )
    child_parent_dict = dict(zip(child_parent_df["child"], child_parent_df["parent"]))
    sectors_info_df["children"] = sectors_info_df["children"].apply(
        lambda value: ast.literal_eval(value) if pd.notna(value) else []
    )
    sectors_info_df["password"] = sectors_info_df["password"].astype("string")
    sector_info_list = sectors_info_df.to_dict(orient="records")
    sector_list = list(sectors_df["sectors"])
    # Insert all CyHy data into PE DB
    pe_db_conn = connect()
    insert_all_cyhy_data(
        pe_db_conn,
        assets_df,
        child_parent_dict,
        contacts_df,
        orgs_df,
        sector_info_list,
        sector_list,
    )
    # Identify which assets in cyhy_db_asset are/aren't current
    identify_org_asset_changes(pe_db_conn)
