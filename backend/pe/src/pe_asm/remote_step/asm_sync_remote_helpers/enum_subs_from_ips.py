"""Enumerate subdomains from IP reverse lookups."""

# Standard Python Libraries
import datetime
import hashlib
import ipaddress
import logging
import socket
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

# Setup logging
LOGGER = logging.getLogger(__name__)

DATE = datetime.datetime.today().date()

QPS_MAX = 100
QPS_DELAY = 1 / QPS_MAX
QPS_RATE_LOCK = threading.Lock()
NEXT_LOOKUP = 0.0


def limit_lookup_rate():
    """Limit all threads in this process to a combined 100 lookups/second."""
    global NEXT_LOOKUP

    with QPS_RATE_LOCK:
        now = time.monotonic()
        if now < NEXT_LOOKUP:
            time.sleep(NEXT_LOOKUP - now)
        NEXT_LOOKUP = max(now, NEXT_LOOKUP) + QPS_DELAY


def reverseLookup(ip_obj, failed_ips, thread):
    """Perform a PTR-based reverse lookup on IP and return the associated domain."""
    # Enforce rate limit across all threads
    limit_lookup_rate()
    # Perform PTR-based reverse lookup on IP
    try:
        hostname, aliases, _ = socket.gethostbyaddr(ip_obj["ip"])
        hostnames = {hostname, *aliases}
    except socket.herror:
        # A missing PTR record is a valid negative result, not a failure.
        return [], failed_ips
    except (socket.gaierror, TimeoutError, OSError) as e:
        LOGGER.error(
            "%s: PTR reverse lookup failed for %s: %s", thread, ip_obj["ip"], e
        )
        failed_ips.append(ip_obj["ip"])
        return [], failed_ips
    # Parse out root and subdomains
    found_domains = []
    for hostname in hostnames:
        hostname = hostname.rstrip(".").lower()
        if not hostname:
            continue
        found_domains.append(
            {
                "sub_domain": hostname,
                "root": ".".join(hostname.rsplit(".")[-2:]),
            }
        )
    # If any domains found, ensure the IP they came from exists in the DB (upsert)
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


def run_ip_chunk(org_name, org_uid, ips_df, thread):
    """Run the provided chunk through the linking process."""
    conn = connect()
    count = 0
    last_chunk = time.time()
    failed_ips = []
    # Iterate over each IP in the chunk
    for ip_index, ip in ips_df.iterrows():
        # Log progress
        count += 1
        if count % 1000 == 0:
            LOGGER.info(
                f"{thread}: Running {org_name} IPs: {count}/{len(ips_df)}, {time.time() - last_chunk} seconds for the last IP chunk"
            )
            last_chunk = time.time()
        # Get domain from IP and link them in the database
        link_domain_from_ip(ip, org_uid, "Python Socket", failed_ips, conn, thread)
    conn.close()


def enum_subs_from_ips(orgs_df):
    """Enumerate subdomains from an org's IPs and create link in the ip_subs table."""
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
        while thread_num < len(ips_split):
            # Start thread
            thread_name = f"Thread {thread_num + 1}: "
            t = threading.Thread(
                target=run_ip_chunk,
                args=(org_name, org_uid, ips_split[thread_num], thread_name),
            )
            t.start()
            thread_list.append(t)
            thread_num += 1
        # Wait for all threads to finish
        for thread in thread_list:
            thread.join()
        LOGGER.info("All threads have finished.")
        org_count += 1
