#!/usr/bin/env python
"""Shodan dedupe script."""

# Standard Python Libraries
import hashlib
import ipaddress
import logging
import time

# Third-Party Libraries
import pandas as pd
from pe_asm.remote_step.asm_sync_remote_query import (
    connect,
    query_cidrs_by_org,
    update_shodan_ips,
)
from pe_source.data.config_source import shodan_api_init
import shodan

# Setup logging
LOGGER = logging.getLogger(__name__)

states = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
]
state_names = [
    "Alaska",
    "Alabama",
    "Arkansas",
    "American Samoa",
    "Arizona",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Guam",
    "Hawaii",
    "Iowa",
    "Idaho",
    "Illinois",
    "Indiana",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Massachusetts",
    "Maryland",
    "Maine",
    "Michigan",
    "Minnesota",
    "Missouri",
    "Mississippi",
    "Montana",
    "North Carolina",
    "North Dakota",
    "Nebraska",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "Nevada",
    "New York",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Puerto Rico",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Virginia",
    "Virgin Islands",
    "Vermont",
    "Washington",
    "Wisconsin",
    "West Virginia",
    "Wyoming",
]


def state_check(host_org):
    """Check state."""
    found = False
    if host_org:
        for state in state_names:
            if state in host_org:
                return state
    return found


def append_if_result_valid(
    result,
    ip_results,
    cidr_uid,
    cidr_network,
    org_type,
):
    """Append a Shodan result only if it meets criteria."""
    # Check if the Shodan result's IP address is valid
    try:
        result_ip = ipaddress.ip_address(result["ip_str"])
    except (KeyError, TypeError, ValueError):
        LOGGER.warning("Skipping Shodan result b/c invalid IP: %s", result)
        return False
    # Check if the Shodan result's IP is within the specified CIDR
    if result_ip not in cidr_network:
        LOGGER.warning(
            "Skipping Shodan result b/c IP %s is outside queried CIDR %s",
            result_ip,
            cidr_network,
        )
        return False
    # Skip if Shodan result is within USA and federal organization
    state = state_check(result.get("org"))
    if state and org_type == "FEDERAL":
        return False
    # Calculate hash for Shodan result's IP and append to results list
    ip_string = str(result_ip)
    ip_hash = hashlib.sha256(ip_string.encode("utf-8")).hexdigest()
    ip_results.append(
        {
            "ip_hash": ip_hash,
            "ip": ip_string,
            "shodan_results": True,
            "origin_cidr": cidr_uid,
            "current": True,
        }
    )
    return True


def search(api, query, ip_results, cidr_uid, cidr_network, org_type):
    """Search Shodan API using query and add IPs to set."""
    network = ipaddress.ip_network(str(cidr_network), strict=False)
    accepted_results = 0
    # Wrap the request in a try/ except block to catch errors
    try:
        # Attempt to search Shodan
        try:
            results = api.search(query)
        except shodan.exception.APIError:
            time.sleep(2)
            results = api.search(query)
        # Iterate over first page of Shodan search results
        for result in results["matches"]:
            if append_if_result_valid(
                result,
                ip_results,
                cidr_uid,
                network,
                org_type,
            ):
                accepted_results += 1
        # Continue retrieving results from the next page if there's more
        i = 1
        while i < results["total"] / 100:
            try:
                # Search Shodan for page i
                try:
                    results = api.search(query=query, page=i)
                except shodan.exception.APIError:
                    time.sleep(2)
                    results = api.search(query, page=i)
                # Iterate over this page of Shodan search results
                for result in results["matches"]:
                    if append_if_result_valid(
                        result,
                        ip_results,
                        cidr_uid,
                        network,
                        org_type,
                    ):
                        accepted_results += 1
                i = i + 1
            except shodan.APIError as e:
                LOGGER.error("Error: {}".format(e))
                LOGGER.error(query)
                results = {"total": 0}
    except shodan.APIError as e:
        LOGGER.error("Error: {}".format(e))
        LOGGER.error(f"Failed on {query}")
        return 0
    # Return total number of results for this query
    return accepted_results


def cidr_dedupe(cidrs, api, org_type, conn):
    """Dedupe CIDR."""
    ip_results = []
    cidr_result_totals = []
    # Iterate over each CIDR in list
    for cidr_index, cidr in cidrs.iterrows():
        # Search Shodan for the current CIDR
        query = f"net:{cidr['network']}"
        result = search(
            api,
            query,
            ip_results,
            cidr["cidr_uid"],
            cidr["network"],
            org_type,
        )
        # Record how many Shodan results this CIDR contained
        cidr_result_totals.append(result)
    # Log how many CIDRs contained IPs with Shodan results
    found = len([i for i in cidr_result_totals if i != 0])
    LOGGER.info(f"CIDRs that contain IPs with Shodan results: {found}")
    # If there were any Shodan results within this org's CIDRs
    new_ips = pd.DataFrame(ip_results)
    if len(new_ips) > 0:
        # Deduplicate the list of CIDR IPs that had Shodan results
        new_ips = new_ips.drop_duplicates(subset="ip", keep="first")
        # Mark those IP records in the PE DB as having Shodan results
        LOGGER.info(f"Updating {len(new_ips)} IPs after Shodan CIDR dedupe")
        update_shodan_ips(conn, new_ips)


def shodan_dedupe(orgs_df):
    """Check list of IPs, CIDRs, ASNS, and FQDNs in Shodan and output set of IPs."""
    num_orgs = len(orgs_df.index)
    # Get Shodan key from config file
    api = shodan_api_init()[0]
    # Iterate over orgs
    org_count = 1
    for org_index, org in orgs_df.iterrows():
        # Connect to database
        conn = connect()
        LOGGER.info(
            "Running Shodan dedupe on %s, %d/%d",
            org["cyhy_db_name"],
            org_count,
            num_orgs,
        )
        # Query CIDRS for this org
        cidrs = query_cidrs_by_org(org["organizations_uid"])
        LOGGER.info(f"{len(cidrs)} CIDRs found")
        # Run CIDR dedupe if there are any CIDRs
        if len(cidrs) > 0:
            LOGGER.info("Running dedupe on CIDR IPs")
            cidr_dedupe(cidrs, api, org["agency_type"], conn)
        LOGGER.info("Finished deduping CIDR IPs")
        org_count += 1
        conn.close()


def main():
    """Run all orgs net assets through the dedupe process."""
    shodan_dedupe(False)


if __name__ == "__main__":
    main()
