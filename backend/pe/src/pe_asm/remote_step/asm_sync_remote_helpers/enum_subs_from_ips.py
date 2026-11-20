"""Enumerate subdomains from IP reverse lookups."""

# Standard Python Libraries
import datetime
import hashlib
import ipaddress
import logging
import os
import threading
import time

# Third-Party Libraries
import numpy as np
import pandas as pd
from pe_asm.remote_step.asm_sync_remote_query import (
    connect,
    query_cidrs_by_org,
    upsert_ips,
)
import requests
import tldextract

# Setup logging
LOGGER = logging.getLogger(__name__)

DATE = datetime.datetime.today().date()

WHOISXML_QPS_MAX = 10  # WhoisXML API endpoint capped at 10 QPS
WHOISXML_MAX_RETRIES = 10
WHOISXML_CONNECT_TIMEOUT = 10
WHOISXML_READ_TIMEOUT = 30
WHOISXML_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
QPS_DELAY = 1 / WHOISXML_QPS_MAX
QPS_RATE_LOCK = threading.Lock()
NEXT_LOOKUP = 0.0

TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())


def limit_lookup_rate():
    """Limit WhoisXML total request rate across all threads in this process."""
    global NEXT_LOOKUP
    with QPS_RATE_LOCK:
        now = time.monotonic()
        if now < NEXT_LOOKUP:
            time.sleep(NEXT_LOOKUP - now)
        NEXT_LOOKUP = max(now, NEXT_LOOKUP) + QPS_DELAY


def whoisxml_reverse_endpoint(ip_address, thread):
    """Retrieve IP results from WhoisXML's paginated DNS A reverse lookup endpoint."""
    # Get API key from env variable
    api_key = os.environ.get("WHOIS_XML_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing required environment variable: WHOIS_XML_KEY")
    # Request params
    params = {
        "apiKey": api_key,
        "searchType": "reverse",
        "recordType": "a",
        "ipAddress": ip_address,
    }
    all_records = []
    # Loop for paginated retrieval
    while True:
        # Attempt to call WhoisXML API w/ retries
        for attempt in range(1, WHOISXML_MAX_RETRIES + 1):
            # Call WhoisXML API
            limit_lookup_rate()
            try:
                response = requests.post(
                    "https://dns-history.whoisxmlapi.com/api/v1",
                    json=params,
                    timeout=(
                        WHOISXML_CONNECT_TIMEOUT,
                        WHOISXML_READ_TIMEOUT,
                    ),
                )
                # If good 200 response
                if response.status_code == 200:
                    result = response.json()
                    result_data = result.get("result")
                    # Check that response is properly structured
                    if not isinstance(result, dict) or not isinstance(
                        result_data,
                        dict,
                    ):
                        raise ValueError(
                            "WhoisXML response had an unexpected structure"
                        )
                    # Check that records field is properly structured
                    records = result_data.get("records", [])
                    if records is None:
                        records = []
                    elif not isinstance(records, list):
                        raise ValueError(
                            "WhoisXML response's records field was not a list"
                        )
                    # Append the results from this page
                    all_records.extend(records)
                    after = result_data.get("after")
                    # If no more pages to retrieve, return full list of results
                    if not after:
                        result_data["records"] = all_records
                        return result
                    # Otherwise update after variable for next page
                    if not isinstance(after, dict):
                        raise ValueError(
                            "WhoisXML response's after field was not an object"
                        )
                    params["after"] = after
                    break
                # Immediately raise if authentication/authorization error
                if response.status_code in (401, 403):
                    raise PermissionError(
                        f"WhoisXML authent./authoriz. failed: HTTP {response.status_code}"
                    )
                # If non-retryable response, log error and return None
                if response.status_code not in WHOISXML_RETRYABLE_STATUS_CODES:
                    LOGGER.error(
                        "%s: Non-retryable WhoisXML response for %s: HTTP %d",
                        thread,
                        ip_address,
                        response.status_code,
                    )
                    return None
                # Capture error code
                error = f"HTTP {response.status_code}"
            except (
                requests.exceptions.RequestException,
                ValueError,
            ) as exception:
                # Capture error code
                error = str(exception)
            # If retries remaining, log warning and sleep before retrying
            if attempt < WHOISXML_MAX_RETRIES:
                delay = min(2 ** (attempt - 1), 30)
                LOGGER.warning(
                    "%s: WhoisXML lookup failed for %s: %s; "
                    "retrying in %d seconds (%d/%d)",
                    thread,
                    ip_address,
                    error,
                    delay,
                    attempt,
                    WHOISXML_MAX_RETRIES,
                )
                time.sleep(delay)
        else:
            # If max retries reached, log error and return None
            LOGGER.error(
                "%s: WhoisXML lookup failed for %s after %d attempts",
                thread,
                ip_address,
                WHOISXML_MAX_RETRIES,
            )
            return None


def reverseLookup(ip_obj, failed_ips, thread):
    """Reverse lookup IPv4 address using WhoisXML's historical A records."""
    # Call WhoisXML reverse lookup endpoint for IP
    response = whoisxml_reverse_endpoint(ip_obj["ip"], thread)
    # If overall response is None, API call failed
    if response is None:
        failed_ips.append(ip_obj["ip"])
        return [], failed_ips
    # If records field is none/empty, no results for this IP
    response_records = response.get("result", {}).get("records", [])
    if not response_records:
        return [], failed_ips
    # Ensure list of records has date field
    dated_records = [
        record
        for record in response_records
        if isinstance(record, dict) and record.get("date")
    ]
    if not dated_records:
        return [], failed_ips
    # Grab the domains from the most recent dated record
    latest_date = max(record["date"] for record in dated_records)
    response_domains = [
        domain
        for record in dated_records
        if record["date"] == latest_date and isinstance(record.get("domains"), list)
        for domain in record["domains"]
    ]
    # Begin parsing each domain
    found_domains = []
    for domain in response_domains:
        # Skip malformed/wildcard DNS results
        if not isinstance(domain, dict) or domain.get("wildcard") is True:
            continue
        # Skip if domain field is not a string
        domain_name = domain.get("domain")
        if not isinstance(domain_name, str):
            continue
        # Isolate the hostname
        hostname = domain.get("domain", "").rstrip(".").lower()
        if not hostname:
            continue
        # Extract the root domain/suffix from the hostname
        extracted = TLD_EXTRACTOR(hostname)
        if not extracted.domain or not extracted.suffix:
            LOGGER.warning(
                "Unable to determine root domain for hostname %s",
                hostname,
            )
            continue
        # Append parsed domain results
        found_domains.append(
            {
                "sub_domain": hostname,
                "root": f"{extracted.domain}.{extracted.suffix}",
            }
        )
    # If any domains found, upsert to DB
    if found_domains:
        upsert_ips(ip_obj)
    # Return results
    return found_domains, failed_ips


def link_domain_from_ip(ip_obj, org_uid, data_source, failed_ips, conn, thread):
    """From a provided ip find domains and link them in the db."""
    # Lookup subdomains from IP
    found_domains, failed_ips = reverseLookup(ip_obj, failed_ips, thread)
    # Add those subdomains to PE DB and link them to their associated IP
    for domain in found_domains:
        cur = conn.cursor()
        cur.callproc(
            "link_ips_and_subs",
            (
                DATE,
                ip_obj["ip_hash"],
                ip_obj["ip"],
                org_uid,
                domain["sub_domain"],
                data_source,
                None,
                domain["root"],
            ),
        )
        cur.fetchone()
        conn.commit()
        cur.close()
    return found_domains


def run_ip_chunk(
    org_name, org_uid, ips_df, thread, failed_ips, worker_errors, stop_event
):
    """Run the provided chunk through the linking process."""
    conn = None
    try:
        conn = connect()
        count = 0
        last_chunk = time.time()
        # Iterate over each IP in the chunk
        for ip_index, ip in ips_df.iterrows():
            # Exit if stop event encountered
            if stop_event.is_set():
                break
            # Log progress
            count += 1
            if count % 1000 == 0:
                LOGGER.info(
                    f"{thread}: Running {org_name} IPs: {count}/{len(ips_df)}, {time.time() - last_chunk} seconds for the last IP chunk"
                )
                last_chunk = time.time()
            # Get domain from IP and link them in the database
            link_domain_from_ip(ip, org_uid, "WhoisXML", failed_ips, conn, thread)
    except PermissionError as exception:
        # Propagate authentication/authorization error
        worker_errors.append(exception)
        stop_event.set()
    except Exception as exception:
        # Propagate unexpected worker failures
        worker_errors.append(exception)
        stop_event.set()
    finally:
        if conn is not None:
            conn.close()


def enum_subs_from_ips(orgs_df):
    """Enumerate subdomains from an org's IPs and create link in the ip_subs table."""
    # Ensure WhoisXML API key present
    if not os.environ.get("WHOIS_XML_KEY", "").rstrip():
        raise RuntimeError("Missing required environment variable: WHOIS_XML_KEY")
    num_orgs = len(orgs_df.index)
    # Iterate over each organization
    org_count = 1
    for org_index, org in orgs_df.iloc[::-1].iterrows():
        org_name = org["cyhy_db_name"]
        LOGGER.info("Running on %s, %d/%d", org_name, org_count, num_orgs)
        # Get current CIDRs for this org
        org_uid = org["organizations_uid"]
        cidrs = query_cidrs_by_org(org_uid)
        ips_list = []
        # Break CIDRs into individual IPs
        for cidr_index, cidr_row in cidrs.iterrows():
            # Skip IPv6 CIDRs
            network = ipaddress.ip_network(cidr_row["network"])
            if network.version == 6:
                LOGGER.warning(
                    "Skipping IPv6 CIDR %s found for org %s, unsupported",
                    network,
                    org_name,
                )
                continue
            # Continue if IPv4 CIDR
            for ip in network.hosts():
                hash_object = hashlib.sha256(str(ip).encode("utf-8"))
                ip_obj = {
                    "ip_hash": hash_object.hexdigest(),
                    "ip": str(ip),
                    "origin_cidr": cidr_row["cidr_uid"],
                    "first_seen": DATE,
                    "last_seen": DATE,
                    "current": True,
                    "from_cidr": True,
                    "last_reverse_lookup": DATE,
                    "organizations_uid": org_uid,
                }
                ips_list.append(ip_obj)
        ips_df = pd.DataFrame(ips_list)
        LOGGER.info(f"Number of CIDRs: {len(cidrs)}")
        # if no IPs, continue to next org
        if len(ips_df.index) == 0:
            org_count += 1
            continue

        # Split IPs across 10 threads, for each thread call run_ip_chunk
        num_chunks = 10
        row_chunks = np.array_split(np.arange(len(ips_df)), num_chunks)
        ips_split = [ips_df.iloc[row_indexes].copy() for row_indexes in row_chunks]
        thread_num = 0
        thread_list = []
        failed_ips = []
        worker_errors = []
        stop_event = threading.Event()
        while thread_num < len(ips_split):
            # Start thread
            thread_name = f"Thread {thread_num + 1}: "
            t = threading.Thread(
                target=run_ip_chunk,
                args=(
                    org_name,
                    org_uid,
                    ips_split[thread_num],
                    thread_name,
                    failed_ips,
                    worker_errors,
                    stop_event,
                ),
            )
            t.start()
            thread_list.append(t)
            thread_num += 1
        # Wait for all threads to finish
        for thread in thread_list:
            thread.join()
        # Raise any fatal worker errors
        if worker_errors:
            raise RuntimeError(
                f"Worker failed while performing WhoisXML lookups for {org_name}"
            ) from worker_errors[0]
        # Raise error if all IP lookups fail for an org
        if len(failed_ips) == len(ips_df):
            raise RuntimeError(
                f"All {len(ips_df)} WhoisXML lookups failed for {org_name}"
            )
        LOGGER.info("All threads have finished.")
        org_count += 1
