"""Scripts to collect data and findings (events) from Flare."""

# Standard Python Libraries
import datetime
import logging
import time
import traceback

# Third-Party Libraries
import pandas as pd
from pe_source.data.db_query_source import (
    get_data_source_uid,
    get_orgs,
    insert_flare_events,
)
from pe_source.flare.flare_helpers import (
    get_all_ident_by_group_id,
    get_event_details,
    get_flare_token,
    get_ident_group_info,
    remove_emoji,
)
import requests

# Set up logging
LOGGER = logging.getLogger(__name__)

# Calculate start and end dates for data collection period
TODAY = datetime.date.today()
DAYS_BACK = datetime.timedelta(days=20)  # 20 days back default
START_DATE = (TODAY - DAYS_BACK).strftime("%Y-%m-%d")
END_DATE = TODAY.strftime("%Y-%m-%d")
# Or manually set data collection window
# START_DATE = "2026-01-16"
# END_DATE = "2026-01-31"


def _requested_org_names(orgs_list):
    """Normalize --orgs values to exact cyhy_db_name matches."""
    if isinstance(orgs_list, str):
        return {part.strip() for part in orgs_list.split(",") if part.strip()}
    return set(orgs_list)


def get_ident_group_events_chunk(token, ident_group_id, payload):
    """Call the Flare identifier group event feed endpoint."""
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
        LOGGER.error("Error: Failed to retrieve Flare events for %s", ident_group_id)
        return None
    else:
        # Print stats
        resp = resp.json()
        num_items = len(resp.get("items"))
        more_data = False
        if resp.get("next"):
            more_data = True
        LOGGER.info("\tChunk retrieved, contained %s items", num_items)
        LOGGER.info("\tIs there another chunk to retrieve? %s", more_data)
        # Return results
        return resp


def get_ident_group_events(
    identifier_group, event_severities, event_types, start_date, end_date
):
    """Retrieve all events for the specified identifier group (organization)."""
    ident_group_name = identifier_group.get("name")
    ident_group_id = identifier_group.get("id")
    LOGGER.info("Retrieving all events for the identifier group: %s", ident_group_name)
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
            "type": event_types,
            "estimated_created_at": {
                "gte": start_date,
                "lte": end_date,
            },
        },
    }
    ini_resp = get_ident_group_events_chunk(flare_token, ident_group_id, ini_payload)
    results_list += ini_resp.get("items")
    # Check if there's any more data to retrieve
    if ini_resp.get("next"):
        more_data = True
        curr_next = ini_resp.get("next")
    # If there's a "next" value, continue fetching data
    retrieve_ct = 2
    while more_data:
        # Rate control delay
        time.sleep(1)
        # Refresh auth token every ~30 min (avg event retrieval api call ~= 1.5s)
        if retrieve_ct % 500 == 0:  # default 1200
            LOGGER.warning("Refreshing Flare API auth token for intial event retrieval")
            LOGGER.info("REFRESHING FLARE AUTH TOKEN")
            flare_token = get_flare_token()
        LOGGER.info("Working on data feed chunk %s", retrieve_ct)
        # Make API call for current chunk
        curr_payload = {
            "size": chunk_size,
            "from": curr_next,
            "filters": {
                "severity": event_severities,
                "type": event_types,
                "estimated_created_at": {
                    "gte": start_date,
                    "lte": end_date,
                },
            },
        }
        curr_resp = get_ident_group_events_chunk(
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
        "Total number of items retrieved for all identifiers: %s", len(results_list)
    )
    return results_list


def get_all_event_details(event_list, org_uid, org_idents_df, data_source_uid):
    """Retrieve the full set of details for each of the specified events."""
    flare_token = get_flare_token()
    # Iterate over each event
    total_event_list = []
    for idx, event in enumerate(event_list):
        # Refresh auth token every ~30 min (avg event detail api call ~= 0.5s)
        if (idx % 500 == 0) and (idx != 0):  # default 3600
            LOGGER.warning(
                "Refreshing Flare API auth token for event details retrieval"
            )
            LOGGER.info("REFRESHING FLARE AUTH TOKEN")
            flare_token = get_flare_token()
        # Retrieve further details for event
        event_uid = event.get("event_uid")
        event_type = event.get("event_type")

        LOGGER.info(
            "Retrieving details for event %s of %s - Type: %s",
            idx + 1,
            len(event_list),
            event_type,
        )

        # If event doesn't have related identifiers, skip
        if len(event.get("identifiers")) == 0:
            LOGGER.error("\tNo related identifiers for this event")
            continue
        # If event type is leaked_credential, skip (incompatible with event details endpoint)
        if event_type == "leaked_credential":
            LOGGER.warning("leaked_credential event encountered, skipping")
            LOGGER.info("\tevent_uid: %s", event_uid)
            continue
        # Call event details endpoint
        event_details = get_event_details(event_uid, flare_token)
        # Skip event if no details available
        if event_details is None:
            LOGGER.error("\tNo details found for this event")
            continue
        event.update({"event_date": event.get("event_date")[:10]})
        # Parse out releveant data based on event type
        if event_type == "stealer_log":
            # Special parsing for stealer_log type events
            event_dict = parse_stealer_log_event_fields(
                event, event_details, org_uid, org_idents_df, data_source_uid
            )
            # Append record
            if event_dict != -1:
                total_event_list.append(event_dict)
        elif event_type == "bot":
            # Parse bot events with custom title + content_preview
            bot_title = "A device has potentially been infected by botnet malware and the data stolen from it has been offered for sale."
            event_dict = parse_default_event_fields(
                event,
                event_details,
                org_uid,
                data_source_uid,
                True,
                bot_title,
            )
            # Append record
            total_event_list.append(event_dict)
        elif event_type in ("leak", "ransomleak", "listing", "seller"):
            # Parse event types that: use content_preview field, no custom title
            event_dict = parse_default_event_fields(
                event, event_details, org_uid, data_source_uid, True
            )
            # Append record
            total_event_list.append(event_dict)
        elif event_type == "chat_message":
            # Parse event types that: use content field, no custom title
            event_dict = parse_default_event_fields(
                event, event_details, org_uid, data_source_uid
            )
            # Append record, only if chat_message has content field
            if (event_dict.get("content")) and (event_dict.get("content") != "None"):
                total_event_list.append(event_dict)
            else:
                LOGGER.error("\tNo content field for this chat_message event")
        else:
            # Parse event types that: use content field, no custom title
            event_dict = parse_default_event_fields(
                event, event_details, org_uid, data_source_uid
            )
            # Append record
            total_event_list.append(event_dict)

    # Return parsed event detail data
    return total_event_list


def parse_related_identifiers(event, text=False):
    """Return identifier IDs or names related to this event."""
    identifiers = []
    for identifier in event.get("identifiers") or []:
        if text:
            identifiers.append(identifier.get("name"))
        else:
            identifiers.append(identifier.get("id"))
    return identifiers


def parse_stealer_log_event_fields(
    event, event_details, org_uid, org_idents_df, data_source_uid
):
    """Parse and format relevant data fields for stealer_log type events."""
    event_details = event_details.get("activity")
    content = event_details.get("header").get("content_preview")
    # If content field is like "N credentials", add extra details
    if content[-12:] == " credentials":
        total_creds = int(content[:-12])
        # Identify relevent credentials
        rel_ident = list(org_idents_df.loc[org_idents_df["type"] == "domain"]["value"])
        rel_creds = []
        creds_list = event_details.get("data").get("credentials")
        if creds_list is None:
            return -1
        for cred in creds_list:
            # Record any creds that contain any of the relevant identifiers
            user = cred.get("username")
            passwd = cred.get("password")
            url = cred.get("url")
            if (
                any(item in user for item in rel_ident)
                or any(item in url for item in rel_ident)
            ) and ("@" in user):
                cred_str = f"username: {user} - password: {passwd} - login_url: {url}"
                rel_creds.append(cred_str)
        # Discard this finding if none of the credentials are relevant
        if len(rel_creds) == 0:
            return -1
        # Get compromised device info
        user_ip = event_details.get("data").get("user_information").get("ip_address")
        user_os = event_details.get("data").get("user_information").get("os")
        user_username = (
            event_details.get("data").get("user_information").get("username")
        )
        # Build custom content field
        content = f"A stealer log was offered for sale containing {total_creds} leaked credentials.\n{len(rel_creds)} of those {total_creds} credentials are related to your organization:"
        for cred in rel_creds:
            content += f"\n- {cred}"
        content += f"\n\nInformation about the device this data was supposedly stolen off of:\nip:{user_ip}\nOS:{user_os}\nusername:{user_username}"

    # Return parsed info
    return {
        "organizations_uid": org_uid,
        "flare_uid": event.get("event_uid"),
        "event_type": event.get("event_type"),
        "event_date": event.get("event_date"),
        "collection_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "title": "A Stealer Log Was Offered for Sale",
        "content": content,
        "content_hash": event_details.get("header").get("content_hash"),
        "actor": event_details.get("header").get("actor"),
        "category": event_details.get("header").get("category_name"),
        "source": event_details.get("metadata").get(
            "source"
        ),  # (source ~= site for mentions)
        "url": event_details.get("data").get("url"),
        "risk_scores": event_details.get("header").get("risk"),
        "related_identifiers": parse_related_identifiers(event),
        "related_identifiers_txt": parse_related_identifiers(event, True),
        "data_source_uid": data_source_uid,
        "severity": event.get("severity"),
    }


def parse_default_event_fields(
    event,
    event_details,
    org_uid,
    data_source_uid,
    content_preview=False,
    custom_title=None,
):
    """Parse and format the standard data fields from the specified event."""
    event_details = event_details.get("activity")
    url = event_details.get("data").get("url")

    # Use custom title if provided
    if custom_title is not None:
        title = custom_title
    else:
        title = event_details.get("header").get("title")
    # Use content_preview instead of content if specified
    if content_preview:
        content = event_details.get("header").get("content_preview")
    else:
        content = event_details.get("data").get("content")

    # Special content parsing needed for chat_message events
    if event.get("event_type") == "chat_message":
        content = event_details.get("data").get("message")
        conv_link = event_details.get("data").get("conversation_link")
        if conv_link is not None:
            url = conv_link

    # Special formatting to get rid of emojis and null chars
    if isinstance(content, str):
        content = remove_emoji(content)
        content = content.replace("\x00", "")

    # Return parsed info
    return {
        "organizations_uid": org_uid,
        "flare_uid": event.get("event_uid"),
        "event_type": event.get("event_type"),
        "event_date": event.get("event_date"),
        "collection_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "title": title,
        "content": content,
        "content_hash": event_details.get("header").get("content_hash"),
        "actor": event_details.get("header").get("actor"),
        "category": event_details.get("header").get("category_name"),
        "source": event_details.get("metadata").get(
            "source"
        ),  # (source ~= site for mentions)
        "url": url,
        "risk_scores": event_details.get("header").get("risk"),
        "related_identifiers": parse_related_identifiers(event),
        "related_identifiers_txt": parse_related_identifiers(event, True),
        "data_source_uid": data_source_uid,
        "severity": event.get("severity"),
    }


def run_flare_events(orgs_list):
    """Retrieve Flare data for the specified list of organizations and insert into the PE DB."""
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
        requested = _requested_org_names(orgs_list)
        for pe_org in pe_orgs:
            if pe_org["cyhy_db_name"] in requested:
                pe_orgs_final.append(pe_org)

    data_source_uid = get_data_source_uid("Flare")

    # Specify which event severities to collect
    event_severities = [
        # "info",
        "low",
        "medium",
        "high",
        "critical",
    ]
    # Specify which event types to collect
    event_types = [
        # > Asset Alert Data:
        # Any events involving IP/Domain assets
        # > Executive Alert Data:
        # Any events involving executive name assets
        # > Potential Threat Alert Data:
        "bot",
        "bucket",
        "bucket_object",
        "domain",
        "service",
        # > Market Alert Data:
        "listing",
        "stealer_log",  # warning, lots of results (still somewhat acceptable)
        # > Credential Data:
        "leak",
        "leaked_credential",  # *** Incompatible with event details endpoint for some reason
        "leaked_data",
        "leaked_file",
        "ransomleak",
        # > Chat (Mention) Data:
        "chat_message",
        # > Dark Web Media (Mention) Data:
        "blog_content",
        "blog_post",
        "forum_post",
        "forum_profile",
        "forum_topic",
    ]
    # Run Flare data collection on each org
    LOGGER.info("Gathering Flare event data of the following types: %s", event_types)
    start_date = START_DATE
    end_date = END_DATE
    success = 0
    failed = 0
    failed_list = []
    for org_idx, org in enumerate(pe_orgs_final):
        # Start exe time for this org
        time_start = time.time()
        org_abbrv = org["cyhy_db_name"]
        # Run Flare on this organization
        try:
            org_uid = org["organizations_uid"]
            LOGGER.info(
                'Running Flare on "%s" (%s of %s)',
                org_abbrv,
                org_idx + 1,
                len(pe_orgs_final),
            )
            # Retrieve identifier group info for this org
            ident_group_info = get_ident_group_info(org_abbrv)
            # Retrieve list of all identifiers for this org
            org_idents_df = pd.DataFrame(
                get_all_ident_by_group_id(ident_group_info.get("id"))
            )
            # Retrieve all Flare events for this org
            LOGGER.info("Retrieving all Flare events for %s", org_abbrv)
            event_list = get_ident_group_events(
                ident_group_info, event_severities, event_types, start_date, end_date
            )
            LOGGER.info("Found %s events for %s", len(event_list), org_abbrv)
            # Retrieve further details for the events and format
            LOGGER.info("Retrieving additional details for %s's events", org_abbrv)
            final_event_list = get_all_event_details(
                event_list, org_uid, org_idents_df, data_source_uid
            )
            if len(final_event_list) > 0:
                # Convert risk_score field to string type
                for event in final_event_list:
                    if event.get("risk_scores") is not None:
                        event.update({"risk_scores": str(event.get("risk_scores"))})
                # Drop duplicates
                final_event_df = pd.DataFrame(final_event_list)
                final_event_df = final_event_df.sort_values(
                    by="event_date", ascending=False
                ).reset_index(drop=True)
                final_event_df.drop_duplicates(
                    subset=["organizations_uid", "flare_uid"],
                    keep="first",
                    inplace=True,
                )
                final_event_list = final_event_df.to_dict(orient="records")
                # Insert Flare event data into PE DB
                LOGGER.info(
                    "Inserting %s Flare event records for %s into the PE database",
                    len(final_event_list),
                    org_abbrv,
                )
                insert_flare_events(final_event_list)
                LOGGER.info(
                    "Flare events for %s successfully inserted into PE database",
                    org_abbrv,
                )
            else:
                LOGGER.info("No Flare events for %s to insert, skipping", org_abbrv)
            # Log successful data collection for this org
            success += 1
        except Exception as e:
            LOGGER.error(
                "Error encountered during Flare scan for %s - %s", org_abbrv, e
            )
            traceback.print_exc()
            # Log failed data collection for this org
            failed += 1
            failed_list.append(org_abbrv)

        # End exe time for this org
        time_end = time.time()
        org_exe_time = datetime.timedelta(
            seconds=(time_end - time_start)
        ).total_seconds()
        LOGGER.info(
            "Flare scan for %s finished in %.5f seconds",
            org_abbrv,
            org_exe_time,
        )

    # Log overall success/fail statistics
    LOGGER.info(
        "%s/%s organizations successfully completed their Flare scan",
        success,
        len(pe_orgs_final),
    )
    LOGGER.info(
        "%s/%s organizations encountered an error during their Flare scan: %s",
        failed,
        len(pe_orgs_final),
        failed_list,
    )
    if failed:
        raise RuntimeError(
            "Flare scan failed for {} of {} organization(s): {}".format(
                failed, len(pe_orgs_final), failed_list
            )
        )
