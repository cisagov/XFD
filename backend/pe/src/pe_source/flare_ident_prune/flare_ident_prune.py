"""Scripts to prune auto-enumerated Flare assets."""

# Standard Python Libraries
import asyncio
import datetime
import logging
import socket
import time

# Third-Party Libraries
import aioping
import numpy as np
import pandas as pd
import requests

# cisagov Libraries
from pe_source.data.config_source import create_retry_session
from pe_source.data.db_query_source import get_orgs
from pe_source.flare.flare_helpers import get_flare_token

# Set up logging
LOGGER = logging.getLogger(__name__)


def flare_identifiers_endpoint(token, params):
    """Call the Flare get identifiers endpoint with the specified parameters."""
    # Setup API call
    session = create_retry_session()
    url = "https://api.flare.io/firework/v3/identifiers/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Make API Call
    try:
        response = session.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        return token, response
    except requests.exceptions.HTTPError as http_err:
        # Catch special token expiry scenario
        if response.status_code == 401:
            return token, response
        LOGGER.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        LOGGER.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        LOGGER.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as err:
        LOGGER.error(f"Unexpected error occurred: {err}")
    return token, None


def parse_domain_idents(raw_resp):
    """Parse out domain identifiers given raw API response."""
    resp = raw_resp.json()
    next = resp.get("next")
    total_ct = resp.get("total_count")
    # Get domains
    domain_list = []
    resp_list = resp.get("items")
    for ident in resp_list:
        domain_dict = {
            "id": ident.get("id"),
            "type": ident.get("type"),
            "value": ident.get("name"),
            "ip": None,
            "source": ident.get("source"),
            "curr_enabled": not ident.get("is_disabled"),
            "detected_resolvable": False,
        }
        domain_list.append(domain_dict)
    # Return parsed results
    return {
        "domains": domain_list,
        "next": next,
        "total_count": total_ct,
    }


def get_all_autoenum_domains(custom_params=None):
    """Get Flare auto-enumerated subdomains across all organizations."""
    if custom_params is None:
        custom_params = {}
    all_domain_list = []
    chunk_size = 100  # Max is 100
    flare_token = get_flare_token()
    next = None
    # Make initial API call
    base_params = {
        "source_group": "SYSTEM",
        "types": ["domain"],
        "size": chunk_size,
    }
    params = base_params | custom_params
    flare_token, ini_resp = flare_identifiers_endpoint(flare_token, params)
    # Parse domain identifiers
    ini_resp_dict = parse_domain_idents(ini_resp)
    next = ini_resp_dict.get("next")
    all_domain_list.extend(ini_resp_dict.get("domains"))
    total_ident_count = ini_resp_dict.get("total_count")
    LOGGER.info(
        "Retrieved %d of %d auto-enum identifiers",
        len(all_domain_list),
        total_ident_count,
    )
    # If there's a next value, continue retrieval
    while next is not None:
        # Make API call for this chunk
        curr_base_params = {
            "from": next,
            "source_group": "SYSTEM",
            "types": ["domain"],
            "size": chunk_size,
        }
        curr_params = curr_base_params | custom_params
        flare_token, curr_resp = flare_identifiers_endpoint(flare_token, curr_params)
        # Handle failed API call
        if curr_resp is None:
            LOGGER.error("Failed to retrieve auto-enum identifiers chunk, stopping")
            break
        # 401 token refresh check
        if curr_resp.status_code == 401:
            LOGGER.warning("401 code encountered, refreshing token")
            flare_token = get_flare_token()
            flare_token, curr_resp = flare_identifiers_endpoint(
                flare_token, curr_params
            )
        # Parse domain identifiers
        curr_resp_dict = parse_domain_idents(curr_resp)
        next = curr_resp_dict.get("next")
        all_domain_list.extend(curr_resp_dict.get("domains"))
        LOGGER.info(
            "Retrieved %d of %d auto-enum identifiers",
            len(all_domain_list),
            total_ident_count,
        )
    # Return results
    LOGGER.info("All auto-enum identifiers retrieved")
    return all_domain_list


async def check_ip_reachable(ip, count=1, timeout=3.0):
    """Check if a single IP is reachable using specified ping count and timeout."""
    # Attempt to ping IP the specified amount of times
    for i in range(count):
        try:
            # Attempt ping
            delay = await aioping.ping(ip, timeout=timeout)
            # If response receieved, return results
            return {
                "ip": ip,
                "detected_reachable": True,
                "response_delay": delay,
            }
        except (TimeoutError, PermissionError) as e:
            # If ping failed, try again
            LOGGER.debug("Ping %d/%d failed for %s - %s", i + 1, count, ip, e)
    # If all ping attempts fail, mark as unreachable
    return {
        "ip": ip,
        "detected_reachable": False,
        "response_delay": None,
    }


async def check_ip_list_reachable(ip_list):
    """Launch multiple tasks to check IPs' reachability."""
    # Create separate tasks for each IP
    ping_ct = 5
    timeout = 3
    tasks = [check_ip_reachable(ip, ping_ct, timeout) for ip in ip_list]
    results = await asyncio.gather(*tasks)
    return results


def check_domains_responsive(domain_list):
    """Check each domain in list to see if it's resolvable/reachable."""
    domain_df = pd.DataFrame(domain_list)
    # Check resolvability of each domain
    for (
        idx,
        row,
    ) in domain_df.iterrows():
        domain = row["value"]
        # Test if domain has an IP associated with it (resolvable)
        LOGGER.debug(
            "Checking resolvability of domain '%s' (%d of %d)",
            domain,
            idx + 1,
            len(domain_df),
        )
        try:
            domain_ip = socket.gethostbyname(domain)
            resolvable = True
        except socket.gaierror:
            domain_ip = None
            resolvable = False
        # Update value in this row
        domain_df.at[idx, "ip"] = domain_ip
        domain_df.at[idx, "detected_resolvable"] = resolvable
    # Check reachability of any domains that have an IP (resolvable)
    ip_list = list(set(domain_df.loc[domain_df["ip"].notnull()]["ip"]))
    ip_results_df = pd.DataFrame(asyncio.run(check_ip_list_reachable(ip_list)))
    # Join resolvability and reachability results
    domain_df = pd.merge(domain_df, ip_results_df, on="ip", how="left")
    domain_df["detected_reachable"] = domain_df["detected_reachable"].fillna(False)
    domain_df["response_delay"] = domain_df["response_delay"].fillna(-1)
    # Calculate overall responsiveness and required action
    domain_df["detected_responsive"] = (
        domain_df["detected_resolvable"] & domain_df["detected_reachable"]
    )
    conditions = [
        (domain_df["curr_enabled"]) & (~domain_df["detected_responsive"]),
        (~domain_df["curr_enabled"]) & (domain_df["detected_responsive"]),
    ]
    choices = ["DISABLE", "ENABLE"]
    domain_df["required_action"] = np.select(conditions, choices, default="NO ACTION")
    domain_df = domain_df[
        [
            "id",
            "type",
            "value",
            "ip",
            "source",
            "curr_enabled",
            "detected_resolvable",
            "detected_reachable",
            "detected_responsive",
            "required_action",
        ]
    ]
    # Return results
    enable_list = domain_df.loc[domain_df["required_action"] == "ENABLE"].to_dict(
        orient="records"
    )
    disable_list = domain_df.loc[domain_df["required_action"] == "DISABLE"].to_dict(
        orient="records"
    )
    return enable_list, disable_list, domain_df


def toggle_ident(token, ident_id, active=True):
    """Enable or disable the Flare identifier based on specified ID."""
    # Setup API call
    session = create_retry_session()
    url = f"https://api.flare.io/firework/v2/assets/{ident_id}/toggle"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"is_disabled": not active}
    # Make API Call
    try:
        response = session.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return token, response
    except requests.exceptions.HTTPError as http_err:
        # Catch special token expiry scenario
        if response.status_code == 401:
            return token, response
        LOGGER.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        LOGGER.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        LOGGER.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as err:
        LOGGER.error(f"Unexpected error occurred: {err}")
    return token, None


def update_ident_lists(enable_list, disable_list):
    """Enable/Disable the provided lists of Flare identifiers."""
    # Iterate over each identifier in enable list
    if len(enable_list) > 0:
        token = get_flare_token()
        for idx, ident in enumerate(enable_list):
            # Call endpoint to enable indentifier
            curr_ident_id = ident.get("id")
            curr_ident_name = ident.get("value")
            token, resp = toggle_ident(token, curr_ident_id, active=True)
            # General error handling
            if resp is None:
                LOGGER.error(
                    f'Failed to enable identifier "{curr_ident_name}" ({curr_ident_id}) {idx+1} of {len(disable_list)}, skipping...'
                )
                continue
            # 401 token refresh check
            if resp.status_code == 401:
                LOGGER.warning("401 code encountered, refreshing token")
                token = get_flare_token()
                token, resp = toggle_ident(token, curr_ident_id, active=True)
            LOGGER.info(
                "Enabled identifier '%s' (%s) %d of %d",
                curr_ident_name,
                curr_ident_id,
                idx + 1,
                len(enable_list),
            )
        LOGGER.info("All identifiers marked for re-enabling have been re-enabled")
    else:
        LOGGER.info("No disabled identifiers to re-enable, continuing")
    # Iterate over each identifier in disable list
    if len(disable_list) > 0:
        token = get_flare_token()
        for idx, ident in enumerate(disable_list):
            curr_ident_id = ident.get("id")
            curr_ident_name = ident.get("value")
            # Call endpoint to disable indentifier
            token, resp = toggle_ident(token, curr_ident_id, active=False)
            # General error handling
            if resp is None:
                LOGGER.error(
                    f'Failed to disable identifier "{curr_ident_name}" ({curr_ident_id}) {idx+1} of {len(disable_list)}, skipping...'
                )
                continue
            # 401 token refresh check
            if resp.status_code == 401:
                LOGGER.warning("401 code encountered, refreshing token")
                token = get_flare_token()
                token, resp = toggle_ident(token, curr_ident_id, active=False)
            LOGGER.info(
                "Disabled identifier '%s' (%s) %d of %d",
                curr_ident_name,
                curr_ident_id,
                idx + 1,
                len(disable_list),
            )
        LOGGER.info("All identifiers marked for disabling have been disabled")
    else:
        LOGGER.info("No enabled identifiers to disable, continuing")


def run_flare_ident_prune(orgs_list):
    """Prune flare auto-enumerated assets."""
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
    pe_orgs_final = sorted(pe_orgs_final, key=lambda d: d["cyhy_db_name"])

    # Begin Flare asset prune
    time_start = time.time()
    try:
        # Retrieve list of all auto-enum assets in Flare
        LOGGER.info("Retrieving all auto-enumerated assets within Flare")
        curr_enabled_domains = get_all_autoenum_domains(
            custom_params={"is_disabled": False}
        )
        LOGGER.info("All auto-enumerated assets that are currently enabled retrieved")
        curr_disabled_domains = get_all_autoenum_domains(
            custom_params={"is_disabled": True}
        )
        LOGGER.info("All auto-enumerated assets that are currently disabled retrieved")
        auto_enum_domains = curr_enabled_domains + curr_disabled_domains
        LOGGER.info("All auto-enumerated assets retrieved")
        # Don't modify certain domains
        excluded_roots = (
            "doj.gov",
            "nrc-gateway.gov",
            "nrc.gov",
            "cisa.dhs.gov",
        )
        auto_enum_domains = [
            d for d in auto_enum_domains if not d["value"].endswith(excluded_roots)
        ]
        # Check which domains are responsive
        LOGGER.info("Checking which auto-enumerated assets are responsive")
        enable_list, disable_list, all_resp_results = check_domains_responsive(
            auto_enum_domains
        )
        LOGGER.info("Auto-enumerated assets have been checked for responsiveness")
        # Enable/Disable the appropriate domains
        LOGGER.info("Enabling/Disabling auto-enumerated assets based on responsiveness")
        update_ident_lists(enable_list, disable_list)
        LOGGER.info(
            "Auto-enumerated assets have been enabled/disabled based on responsiveness"
        )
        # Log stats
        total_assets_tested = len(all_resp_results)
        total_enable_assets = len(
            all_resp_results.loc[all_resp_results["required_action"] == "ENABLE"]
        )
        total_disable_assets = len(
            all_resp_results.loc[all_resp_results["required_action"] == "DISABLE"]
        )
        total_no_action = len(
            all_resp_results.loc[all_resp_results["required_action"] == "NO ACTION"]
        )
        post_prune_total = (
            total_assets_tested + total_enable_assets - total_disable_assets
        )
        LOGGER.info(f"Total Flare Assets Tested: {total_assets_tested}")
        LOGGER.info(f"Total Flare Assets Enabled: {total_enable_assets}")
        LOGGER.info(f"Total Flare Assets Disabled: {total_disable_assets}")
        LOGGER.info(f"Total Flare Assets No Action: {total_no_action}")
        LOGGER.info(f"Total Flare Asssets Post Pruning: {post_prune_total}")
    except Exception as e:
        LOGGER.exception("Encountered an error during Flare pruning script - %s", e)

    # Log execution time
    time_end = time.time()
    exe_time = datetime.timedelta(seconds=(time_end - time_start))
    LOGGER.info("Flare Identifier Prune execution time: %s (H:M:S)", str(exe_time))

