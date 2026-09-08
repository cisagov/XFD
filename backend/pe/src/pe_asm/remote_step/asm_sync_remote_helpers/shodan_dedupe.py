#!/usr/bin/env python
"""Shodan dedupe script."""

# Standard Python Libraries
import hashlib
import logging
import time

# Third-Party Libraries
import pandas as pd
from pe_asm.remote_step.asm_sync_remote_query import (
    connect,
    query_cidrs_by_org,
    query_floating_ips,
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


def cidr_dedupe(cidrs, api, org_type, conn):
    """Dedupe CIDR."""
    ip_obj = []
    results = []
    # Iterate over each CIDR in list
    for cidr_index, cidr in cidrs.iterrows():
        # Search Shodan for the current CIDR
        query = f"net:{cidr['network']}"
        result = search(api, query, ip_obj, cidr["cidr_uid"], org_type)
        # Append results
        results.append(result)
    # Log how many CIDRs contained IPs with Shodan results
    found = len([i for i in results if i != 0])
    LOGGER.info(f"CIDRs that contain IPs with Shodan results: {found}")
    new_ips = pd.DataFrame(ip_obj)
    # If there are any CIDR IPs with Shodan results
    if len(new_ips) > 0:
        # Deduplicate the list of IPs
        new_ips = new_ips.drop_duplicates(subset="ip", keep="first")
        # Update those IP records in the PE DB
        LOGGER.info(f"Updating {len(new_ips)} IPs after Shodan CIDR dedupe")
        update_shodan_ips(conn, new_ips)


def ip_dedupe(api, ips, agency_type, conn):
    """Count number of IPs with data on Shodan."""
    matched = 0
    ips = list(ips)
    float_ips = []
    # Iterate over subdomain IPs in chunks of 100
    for i in range(int(len(ips) / 100) + 1):
        # Retrieve Shodan results for this chunk of IPs
        if (i + 1) * 100 > len(ips):
            try:
                hosts = api.host(ips[i * 100 : len(ips)])
            except shodan.exception.APIError:
                try:
                    time.sleep(2)
                    hosts = api.host(ips[i * 100 : len(ips)])
                except Exception:
                    LOGGER.error(f"{i} failed again")
                    continue
            except shodan.APIError as e:
                LOGGER.error("Error: {}".format(e))
        else:
            try:
                hosts = api.host(ips[i * 100 : (i + 1) * 100])
            except shodan.exception.APIError:
                time.sleep(2)
                try:
                    hosts = api.host(ips[i * 100 : (i + 1) * 100])
                except shodan.APIError as err:
                    LOGGER.error(f"Error: {err}")
                    continue
        # Parse results for this chunk depending on if multiple or single result
        if isinstance(hosts, list):
            # Go through and parse relevant info for each one
            for h in hosts:
                # Check if the state for this result is in USA
                state = state_check(h["org"])
                # Get IP hash for this result
                hash_object = hashlib.sha256(str(h["ip_str"]).encode("utf-8"))
                ip_hash = hash_object.hexdigest()
                # Check if this result is in USA + for a federal organization
                if state and agency_type == "FEDERAL":
                    # If it is, skip
                    continue
                else:
                    # Otherwise append the IP result to the list
                    float_ips.append(
                        {
                            "ip_hash": ip_hash,
                            "ip": h["ip_str"],
                            "shodan_results": True,
                            "origin_cidr": None,
                            "current": True,
                        }
                    )
        else:
            # Check if the state for this result is in USA
            state = state_check(hosts["org"])
            # Get IP hash for this result
            hash_object = hashlib.sha256(str(hosts["ip_str"]).encode("utf-8"))
            ip_hash = hash_object.hexdigest()
            # Check if this result is in USA + for a federal organization
            if state and agency_type == "FEDERAL":
                # If it is, skip
                continue
            else:
                # Otherwise append the IP result to list
                float_ips.append(
                    {
                        "ip_hash": ip_hash,
                        "ip": hosts["ip_str"],
                        "shodan_results": True,
                        "origin_cidr": None,
                        "current": True,
                    }
                )
        matched = matched + len(hosts)
    # Consolidated list of subdomain IPs that have Shodan results
    new_ips = pd.DataFrame(float_ips)
    # If there are any subdomain IPs with Shodan results
    if len(new_ips) > 0:
        # Deduplicate the list of IPs
        new_ips = new_ips.drop_duplicates(subset="ip", keep="first")
        # Update those IP records in the PE DB
        LOGGER.info(f"Updating {len(new_ips)} IPs after Shodan IP dedupe")
        update_shodan_ips(conn, new_ips)


def search(api, query, ip_obj, cidr_uid, org_type):
    """Search Shodan API using query and add IPs to set."""
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
            # Check if the state for this result is in USA
            state = state_check(result["org"])
            # Get the IP hash for this result
            hash_object = hashlib.sha256(str(result["ip_str"]).encode("utf-8"))
            ip_hash = hash_object.hexdigest()
            # Check if this result is in USA + for a federal organization
            if state and org_type == "FEDERAL":
                # If it is, skip
                continue
            else:
                # Otherwise append the IP result to the list
                ip_obj.append(
                    {
                        "ip_hash": ip_hash,
                        "ip": result["ip_str"],
                        "shodan_results": True,
                        "origin_cidr": cidr_uid,
                        "current": True,
                    }
                )

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
                    # Check if the state for this result is in USA
                    state = state_check(result["org"])
                    # Get the IP hash for this result
                    hash_object = hashlib.sha256(str(result["ip_str"]).encode("utf-8"))
                    ip_hash = hash_object.hexdigest()
                    # Check if this result is in USA + for a federal organization
                    if state and org_type == "FEDERAL":
                        # If it is, skip
                        continue
                    else:
                        # Otherwise append the IP result to the list
                        ip_obj.append(
                            {
                                "ip_hash": ip_hash,
                                "ip": result["ip_str"],
                                "shodan_results": True,
                                "origin_cidr": cidr_uid,
                                "current": True,
                            }
                        )
                i = i + 1
            except shodan.APIError as e:
                LOGGER.error("Error: {}".format(e))
                LOGGER.error(query)
                results = {"total": 0}
    except shodan.APIError as e:
        LOGGER.error("Error: {}".format(e))
        # IF it breaks to here it fails
        LOGGER.error(f"Failed on {query}")
        return 0

    # Return full list of results
    return results["total"]


def shodan_dedupe(orgs_df):
    """Check list of IPs, CIDRs, ASNS, and FQDNs in Shodan and output set of IPs."""
    num_orgs = len(orgs_df.index)
    # Get Shodan key from config file
    api = shodan_api_init()[0]
    # Loop through orgs
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
        # Query CIDRS
        cidrs = query_cidrs_by_org(org["organizations_uid"])
        LOGGER.info(f"{len(cidrs)} CIDRs found")
        # Run CIDR dedupe if there are any CIDRs
        if len(cidrs) > 0:
            LOGGER.info("Running dedupe on CIDR IPs")
            cidr_dedupe(cidrs, api, org["agency_type"], conn)
        LOGGER.info("Finished deduping CIDR IPs")
        # Get IPs related to current subdomains
        LOGGER.info("Retrieving floating IPs")
        ips = query_floating_ips(org["organizations_uid"])
        LOGGER.info("Floating IPs retrieved")
        # Run IP dedupe if there are any IPs from subdomains
        if len(ips) > 0:
            LOGGER.info("Running dedupe on floating IPs")
            ip_dedupe(api, ips, org["agency_type"], conn)
        LOGGER.info("Finished deduping floating IPs")

        org_count += 1
        conn.close()


def main():
    """Run all orgs net assets through the dedupe process."""
    shodan_dedupe(False)


if __name__ == "__main__":
    main()
