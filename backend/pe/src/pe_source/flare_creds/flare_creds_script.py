"""Scripts to collect credential leak data from Flare."""

# Standard Python Libraries
import datetime
import logging
import os
import time
import traceback

# Third-Party Libraries
import numpy as np
import openpyxl
from openpyxl import load_workbook
import pandas as pd
import requests

# cisagov Libraries
from pe_source.flare_events.flare_helpers import (
    get_event_details,
    get_ident_group_info,
    get_all_ident_by_group_id,
    get_flare_token,
)
from pe_source.data.db_query_source import (
    get_cred_breach_uids,
    get_orgs,
    insert_flare_breaches,
    insert_flare_credentials,
    get_data_source_uid,
)

# Set up logging
LOGGER = logging.getLogger(__name__)

# Calculate start and end dates for data collection period
TODAY = datetime.date.today()
DAYS_BACK = datetime.timedelta(days=20)  # 20 days back default
START_DATE = (TODAY - DAYS_BACK).strftime("%Y-%m-%d")
END_DATE = TODAY.strftime("%Y-%m-%d")

def get_ident_creds_chunk(token, ident_id, payload):
    """Retrieve chunk of leaked creds for the speicifed identifier ID."""
    size = payload.get("size")
    frm = payload.get("from")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if frm is not None:
        url = f"https://api.flare.io/firework/v3/identifiers/{ident_id}/feed/credentials?size={size}&from={frm}"
    else:
        url = f"https://api.flare.io/firework/v3/identifiers/{ident_id}/feed/credentials?size={size}"
    resp = requests.get(url, headers=headers, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            f"\tRetrying Flare leaked cred retrieval API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error(f"Error: Failed to retrieve Flare leaked creds for {ident_id}")
        return None
    else:
        # Print stats
        resp = resp.json()
        num_items = len(resp.get("items"))
        more_data = False
        if resp.get("next"):
            more_data = True
        LOGGER.info(f"\tChunk retrieved, contained {num_items} items")
        LOGGER.info(f"\tIs there another chunk to retrieve? {more_data}")
        # Return results
        return resp


def get_ident_creds(ident_id, start_date, end_date):
    """Retrieve all leaked creds for the specified identifier ID."""
    LOGGER.info(f"Retrieving all leaked creds for the identifier ID: {ident_id}")
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    flare_token = get_flare_token()
    results_list = []
    more_data = False
    curr_next = ""
    chunk_size = 100  # default 20
    # Make initial data feed call
    LOGGER.info("Working on data feed chunk 1")
    ini_payload = {
        "size": chunk_size,
        # "filters": {
        #     "estimated_created_at": {
        #         "gte": start_date,
        #         "lte": end_date,
        #     }
        # }
    }
    ini_resp = get_ident_creds_chunk(flare_token, ident_id, ini_payload)
    results_list += ini_resp.get("items")
    # rate control delay
    time.sleep(0.75)
    # Check if there's any more data to retrieve
    if ini_resp.get("next"):
        more_data = True
        curr_next = ini_resp.get("next")
    # If there's a "next" value, continue fetching data
    retrieve_ct = 2
    while more_data:
        # rate control delay
        time.sleep(1)
        LOGGER.info(f"Working on leaked credentials feed chunk {retrieve_ct}")
        # Make API call for current chunk
        curr_payload = {
            "size": chunk_size,
            "from": curr_next,
            # "filters": {
            #     "estimated_created_at": {
            #         "gte": start_date,
            #         "lte": end_date,
            #     }
            # }
        }
        curr_resp = get_ident_creds_chunk(flare_token, ident_id, curr_payload)
        # Handle edge case where no results found for this chunk
        if len(curr_resp.get("items")) != 0:
            # Append results
            results_list += curr_resp.get("items")
            curr_last_record = curr_resp.get("items")[-1]
            last_rec_date = datetime.datetime.fromisoformat(
                curr_last_record.get("imported_at")
            ).date()
        else:
            last_rec_date = end_date
        # Check if data retrieval should continue
        if last_rec_date < start_date:
            # Stop retrieving if we've passed the start date of the specified time period
            more_data = False
            # No use in continuing since all following results will be even older records
        elif curr_resp.get("next"):
            # If there's more data, update next value - continue
            curr_next = curr_resp.get("next")
        else:
            # If no next value, there's no more data to retrieve - stop
            more_data = False
        retrieve_ct += 1

    #Get Data Source UID for Flare
    flare_data_source_uid = get_data_source_uid("Flare")

    # Once all data has been retrieved, format and return results
    results_list = [
        {
            "modified_date": item.get("imported_at"),
            "email": item.get("identity_name"),
            "password": item.get("hash"),
            "hash_type": "plain-text",
            "root_domain": item.get("domain"),
            "sub_domain": item.get("domain"),
            "credential_breaches_uid": None,
            "breach_name": item.get("source").get("id"),
            "breach_description": item.get("source").get("description_en"),
            "breach_date": item.get("source").get("breached_at"),
            "related_identifier": ident_id,
            "data_source_uid": flare_data_source_uid,
            "url": None,
        }
        for item in results_list
    ]
    # Filter for results only within the specified time period
    results_list = [
        record
        for record in results_list
        if start_date
        <= datetime.datetime.fromisoformat(record["modified_date"]).date()
        <= end_date
    ]
    # Return results
    LOGGER.info(
        f"Total number of leaked credentials retrieved for identifier: {len(results_list)}"
    )
    return results_list


def get_ident_group_stealer_logs_chunk(token, ident_group_id, payload):
    """Call the Flare identifier group event feed endpoint, specifically for stealer_logs."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    url = f"https://api.flare.io/firework/v4/events/identifier_groups/{ident_group_id}/_search"
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
                    "\tRetrying Flare event retrieval API endpoint (code %s), attempt %s of %s",
                    resp.status_code,
                    retry_count,
                    max_retries,
                )
        time.sleep(time_delay)
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error(
            f"Error: Failed to retrieve Flare stealer_log events for {ident_group_id}"
        )
        return None
    else:
        # Print stats
        resp = resp.json()
        num_items = len(resp.get("items"))
        more_data = False
        if resp.get("next"):
            more_data = True
        LOGGER.info(f"\tChunk retrieved, contained {num_items} items")
        LOGGER.info(f"\tIs there another chunk to retrieve? {more_data}")
        # Return results
        return resp


def get_ident_group_stealer_logs(
    identifier_group, event_severities, start_date, end_date
):
    """Retrieve all stealer_log events for the specified identifier group (organization)."""
    ident_group_name = identifier_group.get("name")
    ident_group_id = identifier_group.get("id")
    LOGGER.info(
        f"Retrieving all stealer_log events for the identifier group: {ident_group_name}"
    )
    flare_token = get_flare_token()
    results_list = []
    more_data = False
    curr_next = ""
    chunk_size = 10  # max size is 10
    # Make initial data feed call
    LOGGER.info("Working on data feed chunk 1")
    ini_payload = {
        "size": chunk_size,
        "filters": {
            "severity": event_severities,
            "type": ["stealer_log"],
            "estimated_created_at": {
                "gte": start_date,
                "lte": end_date,
            },
        },
    }
    ini_resp = get_ident_group_stealer_logs_chunk(
        flare_token, ident_group_id, ini_payload
    )
    results_list += ini_resp.get("items")
    # Check if there's any more data to retrieve
    if ini_resp.get("next"):
        more_data = True
        curr_next = ini_resp.get("next")
    # If there's a "next" value, continue fetching data
    retrieve_ct = 2
    while more_data:
        # rate control delay
        time.sleep(1)
        LOGGER.info(f"Working on data feed chunk {retrieve_ct}")
        # Make API call for current chunk
        curr_payload = {
            "size": chunk_size,
            "from": curr_next,
            "filters": {
                "severity": event_severities,
                "type": ["stealer_log"],
                "estimated_created_at": {
                    "gte": start_date,
                    "lte": end_date,
                },
            },
        }
        curr_resp = get_ident_group_stealer_logs_chunk(
            flare_token, ident_group_id, curr_payload
        )
        # Handle edge case where no results found for this chunk
        if len(curr_resp.get("items")) != 0:
            # Append results
            results_list += curr_resp.get("items")
        # Check if there's anymore data to retrieve
        if curr_resp.get("next"):
            # If there's more data, update next value
            curr_next = curr_resp.get("next")
        else:
            # If no next value, there's no more data to retrieve
            more_data = False
        retrieve_ct += 1

    # Once all data has been retrieved, format and return results
    results_list = [
        {
            "event_uid": item.get("metadata").get("uid"),
            "event_type": item.get("metadata").get("type"),
            "severity": item.get("metadata").get("severity"),
            "identifiers": item.get("identifiers"),
            "event_date": item.get("metadata").get("estimated_created_at"),
        }
        for item in results_list
    ]
    LOGGER.info(
        f"Total number of stealer_log records retrieved for identifier group: {len(results_list)}"
    )
    return results_list


def get_stealer_log_creds(event_list, org_idents):
    """Retrieve any relevant leaked credentials from the list of stealer_log events."""
    flare_token = get_flare_token()
    # Iterate over each event
    total_cred_list = []
    for idx, event in enumerate(event_list):
        # General event info
        event_uid = event.get("event_uid")
        event_type = event.get("event_type")
        org_domain_idents = [d["value"] for d in org_idents if d["type"] == "domain"]
        # If event doesn't have related identifiers, skip
        if len(event.get("identifiers")) == 0:
            LOGGER.error("\tERROR: no related identifiers for this event")
            continue
        # Call event details endpoint
        event_details = get_event_details(event_uid, flare_token)
        # Skip event if no details available
        if event_details is None:
            continue
        # Otherwise, proceed to parse all creds from event details response
        event.update({"event_date": event.get("event_date")[:10]})
        LOGGER.info(
            f"Retrieved details for event {idx+1} of {len(event_list)} - Type: {event_type}"
        )
        # Parse any leaked credentials in this stealer_logs event
        cred_list = extract_stealer_log_creds(event, event_details, org_domain_idents)
        # Append any creds found to overall list
        if (cred_list is not None) and (len(cred_list) > 0):
            total_cred_list.extend(cred_list)

    # Return full list of stealer_log creds
    return total_cred_list


def extract_stealer_log_creds(event, event_details, domain_idents):
    """Extract leaked username password pairs from a stealer_log event if available."""
    # Check if this stealer_log event has any credentials
    try:
        raw_creds_list = event_details.get("activity").get("data").get("credentials")
    except Exception as e:
        LOGGER.error(f"\tError: No credentials found for this stealer_log event - {e}")
        return None
    if raw_creds_list is None:
        LOGGER.error("\tError: No credentials found for this stealer_log event")
        return None
    # Flare data source uid
    flare_data_source_uid = get_data_source_uid("Flare")
    # If it does, iterate over the list of creds to find the ones relevant to the organization
    creds_list = []
    for dict in raw_creds_list:
        curr_url = dict.get("url")
        curr_username = dict.get("username")
        curr_mod_date = event_details.get("activity").get("header").get("timestamp")
        curr_str_date = curr_mod_date[:19]
        vic_ip = (
            event_details.get("activity")
            .get("data")
            .get("user_information")
            .get("ip_address")
        )
        vic_os = (
            event_details.get("activity").get("data").get("user_information").get("os")
        )
        vic_user = (
            event_details.get("activity")
            .get("data")
            .get("user_information")
            .get("username")
        )
        # Iterate over all of this org's domain assets
        for domain in domain_idents:
            # Only record leaked creds whose username or login URL contains an organization's domain
            if ((domain in curr_url) or (domain in curr_username)) and (
                curr_username != ""
            ):
                # Determine breach name
                if vic_user is None and vic_ip is None:
                    breach_name = (
                        f"Stealer Log from {vic_user}@{vic_ip} {curr_str_date}"
                    )
                else:
                    breach_name = f"Stealer Log from {vic_user}@{vic_ip}"
                # Determine if password present
                pass_incl = False
                if dict.get("password") is not None:
                    pass_incl = True
                # Build breach description
                breach_desc = (
                    "A stealer log was identified on "
                    + curr_mod_date
                    + " that "
                    + (
                        "contained passwords."
                        if pass_incl is True
                        else "did not contain passwords."
                    )
                    + "\nOne or more leaked credentials in this stealer log are relevant to your organization "
                    + "\nbecause either the username or login URL contained one of your organization's domains."
                    + "\nThis data was supposedly stolen off of a device with the following information:"
                    + f"\nIP: {vic_ip}"
                    + f"\nOS: {vic_os}"
                    + f"\nUsername: {vic_user}"
                )
                # Assemble data dict for this credential
                append_dict = {
                    "modified_date": curr_mod_date,
                    "email": dict.get("username"),
                    "password": dict.get("password"),
                    "hash_type": "plain-text",
                    "root_domain": domain,
                    "sub_domain": domain,
                    "credential_breaches_uid": None,
                    "breach_name": breach_name,
                    "breach_description": breach_desc,
                    "breach_date": curr_mod_date,
                    "related_identifier": event.get("identifiers"),
                    "data_source_uid": flare_data_source_uid,
                    "url": dict.get("url"),
                }
                # Append result to the overall list for this stealer_log event
                creds_list.append(append_dict)

    # Format and return results
    return creds_list


def format_creds_for_db(all_creds_df, org_uid):
    """Take overall list of creds and format it for insertion into P&E database."""
    # Filter out ineligible records
    all_creds_df = all_creds_df[
        all_creds_df["email"].str.contains("@", na=False)
    ].reset_index(drop=True)
    all_creds_df = all_creds_df.drop_duplicates(
        subset=["email", "breach_name"], keep="first"
    )
    all_creds_df = all_creds_df.loc[all_creds_df["breach_name"] != ""]
    # Add additional columns
    all_creds_df["password_included"] = np.where(
        (pd.isna(all_creds_df["password"])) | (all_creds_df["password"] == ""), 0, 1
    )
    all_creds_df["sub_domain"] = all_creds_df["email"].str.split("@").str[1]
    # all_creds_df["sub_domain"].fillna("None", inplace=True)
    all_creds_df.fillna({"sub_domain": "None"}, inplace=True)
    all_creds_df["organizations_uid"] = org_uid
    all_creds_df["intelx_system_id"] = "None"
    # Assemble credential exposures dataframe
    creds_df = all_creds_df[
        [
            "email",
            "organizations_uid",
            "root_domain",
            "sub_domain",
            "breach_name",
            "modified_date",
            "credential_breaches_uid",
            "data_source_uid",
            "password",
            "hash_type",
            "intelx_system_id",
            "url",
        ]
    ].reset_index(drop=True)
    # Assemble credential breaches dataframe
    breaches_df = all_creds_df.groupby(
        [
            "breach_name",
            "breach_description",
            "modified_date",
            # "bucket",
            "data_source_uid",
        ]
    ).aggregate({"email": "count", "password_included": "sum"})
    breaches_df = breaches_df.reset_index()
    breaches_df["password_included"] = breaches_df["password_included"] > 0
    breaches_df.rename(
        columns={
            "breach_description": "description",
            "email": "exposed_cred_count",
        },
        inplace=True,
    )
    breaches_df["breach_date"] = breaches_df["modified_date"]
    breaches_df["added_date"] = END_DATE
    breaches_df = breaches_df[
        [
            "breach_name",
            "description",
            "breach_date",
            "added_date",
            "modified_date",
            "password_included",
            "data_source_uid",
        ]
    ]
    # Return results
    return creds_df, breaches_df


def run_flare_creds(orgs_list):
    """Retrieve Flare leaked credential data for the specified list of organizations and insert into the P&E DB."""
    # Retrieve full org info from PE database
    pe_orgs = get_orgs()
    pe_orgs_final = []
    if orgs_list == "all":
        for pe_org in pe_orgs:
            if pe_org["report_on"]:
                pe_orgs_final.append(pe_org)
            else:
                continue
    elif orgs_list == "DEMO":
        for pe_org in pe_orgs:
            if pe_org["demo"]:
                pe_orgs_final.append(pe_org)
            else:
                continue
    else:
        for org in orgs_list:
            org_dict = next((d for d in pe_orgs if d["cyhy_db_name"] == org), None)
            pe_orgs_final.append(org_dict)
    # Alphabetize org list for consistent order
    LOGGER.info("Org Information: %s", pe_orgs)
    pe_orgs_final = sorted(pe_orgs_final, key=lambda d: d["cyhy_db_name"])

    # Run Flare leaked credential data collection on each org
    start_date = START_DATE
    end_date = END_DATE
    success = 0
    failed = 0
    failed_list = []
    for org_idx, org in enumerate(pe_orgs_final):
        # Start exe time for this org
        time_start = time.time()
        try:
            # Run Flare on this organization
            org_abbrv = org["cyhy_db_name"]
            org_uid = org["organizations_uid"]
            LOGGER.info(
                f'Running Flare leaked credentials collection on "{org_abbrv}" ({org_idx + 1} of {len(pe_orgs_final)})'
            )
            # Retrieve identifier group info for this org
            ident_group_info = get_ident_group_info(org_abbrv)
            # Retrieve identifiers for this org
            org_idents = get_all_ident_by_group_id(ident_group_info.get("id"))
            LOGGER.info(f"Retrieved identifiers for {org_abbrv}: {len(org_idents)}")

            # Retrieve leaked credentials from each of the org's identifiers
            ident_creds_list = []
            for ident_idx, ident in enumerate(org_idents):
                ident_val = ident.get("value")
                ident_id = ident.get("id")
                LOGGER.info(
                    f"Retrieving creds for identifier: {ident_val} ({ident_idx+1} of {len(org_idents)})"
                )
                # Look up credentials for this identifier
                ident_creds = get_ident_creds(ident_id, start_date, end_date)
                # Add it to the overall list for this org
                ident_creds_list.extend(ident_creds)
            LOGGER.info(
                f"Found {len(ident_creds_list)} Flare creds from {org_abbrv}'s identifiers"
            )

            # Retrieve leaked credentials from this org's stealer_log events
            stealer_log_creds_list = []
            event_severities = [
                # "info",
                "low",
                "medium",
                "high",
                "critical",
            ]
            # Get all stealer_log type events for this org
            stealer_log_event_list = get_ident_group_stealer_logs(
                ident_group_info, event_severities, start_date, end_date
            )
            stealer_log_event_list = [
                d for d in stealer_log_event_list if d["event_type"] == "stealer_log"
            ]
            # Check if any stealer_log events found
            if len(stealer_log_event_list) > 0:
                # If so, retrieve any relevant credentials from the stealer_log events
                stealer_log_creds_list = get_stealer_log_creds(
                    stealer_log_event_list, org_idents
                )
            LOGGER.info(
                f"Found {len(stealer_log_creds_list)} Flare creds from {org_abbrv}'s stealer_log events"
            )

            # Combine lists of identifier creds and stealer_log creds
            expected_cols = [
                "modified_date",
                "email",
                "password",
                "hash_type",
                "root_domain",
                "sub_domain",
                "credential_breaches_uid",
                "breach_name",
                "breach_description",
                "breach_date",
                "related_identifier",
                "data_source_uid",
                "url",
            ]
            if len(stealer_log_creds_list) > 0:
                stealer_log_creds_df = pd.DataFrame(stealer_log_creds_list)
            else:
                stealer_log_creds_df = pd.DataFrame(columns=expected_cols)
            if len(ident_creds_list) > 0:
                ident_creds_df = pd.DataFrame(ident_creds_list)
            else:
                ident_creds_df = pd.DataFrame(columns=expected_cols)
            ident_creds_df["email"] = ident_creds_df["email"].str.lower()
            stealer_log_creds_df["email"] = stealer_log_creds_df["email"].str.lower()
            # Use full password (instead of censored version) if available
            if (len(ident_creds_df) > 0) and (len(stealer_log_creds_df) > 0):
                full_pass_dict = dict(
                    zip(ident_creds_df["email"], ident_creds_df["password"])
                )
                stealer_log_creds_df["full_password"] = (
                    stealer_log_creds_df["email"]
                    .map(full_pass_dict)
                    .fillna(stealer_log_creds_df["password"])
                )
                stealer_log_creds_df.drop(columns=["password"], inplace=True)
                stealer_log_creds_df.rename(
                    columns={"full_password": "password"}, inplace=True
                )
                stealer_log_creds_df = stealer_log_creds_df[expected_cols]
            # Drop duplicates, prioritize the stealer_log version of creds
            all_creds_df = pd.concat(
                [stealer_log_creds_df, ident_creds_df], ignore_index=True
            )
            all_creds_df = all_creds_df.drop_duplicates(
                subset=["email"], keep="first"
            ).reset_index(drop=True)

            # Format total list of creds and insert into the P&E database
            if len(all_creds_df) > 0:
                LOGGER.info(
                    f"Found {len(all_creds_df)} unique Flare creds overall for {org_abbrv}"
                )
                # Format creds list to align with database tables
                LOGGER.info("Formatting credentials for insertion into P&E database")
                exposures_df, breaches_df = format_creds_for_db(all_creds_df, org_uid)
                LOGGER.info(
                    f"Found {len(exposures_df)} viable Flare creds after formatting"
                )
                if len(exposures_df) == 0 or len(breaches_df) == 0:
                    LOGGER.info(
                        "No viable Flare creds found for DB insertion, continuing..."
                    )
                    success += 1
                    continue
                # Insert Flare breach data into PE DB
                insert_flare_breaches(breaches_df)
                LOGGER.info(
                    f"Flare breaches for {org_abbrv} successfully inserted into PE database"
                )
                # Retrieve UIDs for the breaches that were just inserted
                breach_uid_df = get_cred_breach_uids(list(exposures_df["breach_name"]))
                breach_dict = dict(
                    zip(
                        breach_uid_df["breach_name"],
                        breach_uid_df["credential_breaches_uid"],
                    )
                )
                # Add breach UIDs to credential records
                for idx, row in exposures_df.iterrows():
                    breach_uid = breach_dict.get(row["breach_name"])
                    exposures_df.at[idx, "credential_breaches_uid"] = breach_uid
                # Insert Flare credential data into PE DB
                insert_flare_credentials(exposures_df)
                LOGGER.info(
                    f"Flare credentials for {org_abbrv} successfully inserted into PE database"
                )
                # Log successful data collection for this org
                success += 1
            else:
                LOGGER.info(f"No Flare creds found for {org_abbrv}, moving on...")
                success += 1

        except Exception as e:
            LOGGER.error(f"Error encountered during Flare scan for {org_abbrv} - {e}")
            # Log failed data collection for this org
            failed += 1
            failed_list.append(org_abbrv)


    # Log overall success/fail statistics
    LOGGER.info(
        f"{success}/{len(pe_orgs_final)} organizations successfully completed their Flare leaked creds data collection"
    )
    LOGGER.info(
        f"{failed}/{len(pe_orgs_final)} organizations encountered an error during their Flare leaked creds data collection: {failed_list}"
    )

