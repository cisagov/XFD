"""Enumerate subdomains from IP lookups."""

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

# Setup logging
LOGGER = logging.getLogger(__name__)

DATE = datetime.datetime.today().date()


def reverseLookup(ip_obj, failed_ips, thread):
    """Take an ip and find all associated subdomains."""
    # Query WhoisXML endpoint
    whoisxml_key = os.environ.get("WHOIS_XML_KEY")
    url = f"https://dns-history.whoisxmlapi.com/api/v1?apiKey={whoisxml_key}&ip={ip_obj['ip']}"
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    # Retry clause
    retry_count, max_retries, time_delay = 1, 5, 3
    while response.status_code != 200 and retry_count <= max_retries:
        if retry_count >= 4:
            LOGGER.warning(
                f"Retrying WhoisXML API endpoint (code {response.status_code}), attempt {retry_count} of {max_retries} (url: {url})"
            )
        time.sleep(time_delay)
        response = requests.request("GET", url, headers=headers, data=payload)
        retry_count += 1
    # If API call still unsuccessful
    if response.status_code != 200:
        bad_ip = ip_obj["ip"]
        LOGGER.error(f"Max retries reached for {bad_ip}, labeling as failed")
        failed_ips.append(ip_obj["ip"])
    # Extract found domains from response
    response = response.json()
    found_domains = []
    try:
        # If there is a response, save domain
        if response["size"] > 0:
            # Insert or update IP
            upsert_ips(ip_obj)
            result = response["result"]
            for domain in result:
                try:
                    found_domains.append(
                        {
                            "sub_domain": domain["name"],
                            "root": ".".join(domain["name"].rsplit(".")[-2:]),
                        }
                    )
                except KeyError:
                    continue
    except Exception as e:
        LOGGER.error(f"{thread}: Failed to return WHOIsXML response")
        LOGGER.error(f"{thread}: {response}")
        LOGGER.error(f"{thread}: {e}")
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


def run_ip_chunk(org_name, org_uid, ips_df, thread):
    """Run the provided chunk through the linking process."""
    conn = connect()
    count = 0
    last_chunk = time.time()
    failed_ips = []
    for ip_index, ip in ips_df.iterrows():
        # Log progress
        count += 1
        if count % 1000 == 0:
            LOGGER.info(
                f"{thread}: Running {org_name} IPs: {count}/{len(ips_df)}, {time.time() - last_chunk} seconds for the last IP chunk"
            )
            last_chunk = time.time()
        # Link domain from IP
        try:
            link_domain_from_ip(ip, org_uid, "WhoisXML", failed_ips, conn, thread)
        except requests.exceptions.SSLError as e:
            LOGGER.error(e)
            time.sleep(1)
            continue
    conn.close()


def enum_subs_from_ips(orgs_df):
    """Enumerate subdomains from an org's IPs and create link in the ip_subs table."""
    num_orgs = len(orgs_df.index)
    # Loop through orgs
    org_count = 1
    for org_index, org in orgs_df.iloc[::-1].iterrows():
        org_name = org["cyhy_db_name"]
        LOGGER.info("Running on %s, %d/%d", org_name, org_count, num_orgs)
        # Query IPs
        org_uid = org["organizations_uid"]
        cidrs = query_cidrs_by_org(org_uid)
        ips_list = []
        for cidr_index, cidr_row in cidrs.iterrows():
            for ip in list(ipaddress.IPv4Network(cidr_row["network"]).hosts()):
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

        # if no IPS, continue to next org
        if len(ips_df.index) == 0:
            org_count += 1
            continue

        # Split IPs into 8 threads, then call run_ip_chunk function
        num_chunks = 5
        row_chunks = np.array_split(np.arange(len(ips_df)), num_chunks)
        ips_split = [ips_df.iloc[row_indexes].copy() for row_indexes in row_chunks]
        thread_num = 0
        thread_list = []
        while thread_num < len(ips_split):
            thread_name = f"Thread {thread_num + 1}: "
            # Start thread
            t = threading.Thread(
                target=run_ip_chunk,
                args=(org_name, org_uid, ips_split[thread_num], thread_name),
            )
            t.start()
            thread_list.append(t)
            thread_num += 1

        for thread in thread_list:
            thread.join()

        LOGGER.info("All threads have finished.")
        org_count += 1
