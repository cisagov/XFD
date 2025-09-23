#!/usr/bin/env python
"""Shodan dedupe script."""
# Standard Python Libraries
import datetime
import hashlib
import logging
import os
import time

# Third-Party Libraries
import shodan

API_KEY = os.getenv("SHODAN_API_KEY")

# Third-Party Libraries
from xfd_api.helpers.asset_inserts import create_or_update_ip
from xfd_mini_dl.models import Cidr, Ip, Organization

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


def connect_to_shodan():
    """Create shodan connection."""
    try:
        api = shodan.Shodan(API_KEY)
        # Test api key
        api.info()
        return api
    except Exception:
        LOGGER.error("Invalid Shodan API key")
        return 0


def cidr_dedupe(cidrs, api, org):
    """Dedupe CIDR."""
    ip_obj = []
    results = []
    for cidr in cidrs:
        query = "net:{cidr}".format(cidr=cidr.network)
        result = search(api, query, ip_obj, cidr, org.type)
        if result:
            results.append(result)
    found = len([i for i in results if i != 0])
    LOGGER.info("CIDRs with IPs found: %d", found)

    if len(ip_obj) > 0:
        update_shodan_ips(ip_obj, org)


def update_shodan_ips(ip_list, org):
    """Update if an IP is a shodan IP."""
    ip_set = set()
    for ip in ip_list:
        try:
            if ip.get("ip") not in ip_set:
                ip_set.add(ip.get("ip"))
                create_default = {
                    "ip": ip.get("ip"),
                    "organization": org,
                    "origin_cidr": ip.get("origin_cidr"),
                    "has_shodan_results": True,
                    "current": True,
                    "from_cidr": bool(ip.get("origin_cidr")),
                    "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
                }
                update_default = {
                    "has_shodan_results": True,
                    "current": True,
                    "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
                }
                if ip.get("origin_cidr"):
                    update_default["origin_cidr"] = ip.get("origin_cidr")
                    update_default["from_cidr"] = True
                create_or_update_ip(create_default, update_default, linked_sub=None)

        except Exception as e:
            LOGGER.error("Error saving the IP to the db: %s", e)


def ip_dedupe(api, ips, org):
    """Count number of IPs with data on Shodan."""
    matched = 0
    ips = list(ips)
    float_ips = []
    for i in range(int(len(ips) / 100) + 1):
        LOGGER.info(ips[i * 100 : len(ips)])
        if (i + 1) * 100 > len(ips):
            try:
                hosts = api.host(ips[i * 100 : len(ips)])
            except shodan.exception.APIError:
                try:
                    time.sleep(2)
                    hosts = api.host(ips[i * 100 : len(ips)])
                except Exception:
                    LOGGER.error("%s failed again", i)
                    continue
        else:
            try:
                hosts = api.host(ips[i * 100 : (i + 1) * 100])
            except shodan.exception.APIError:
                time.sleep(2)
                try:
                    hosts = api.host(ips[i * 100 : (i + 1) * 100])
                except shodan.APIError as err:
                    LOGGER.error("Error: %s", err)
                    continue
        if isinstance(hosts, list):
            for h in hosts:
                state = state_check(h["org"])
                hash_object = hashlib.sha256(str(h["ip_str"]).encode("utf-8"))
                ip_hash = hash_object.hexdigest()
                if state and org.type == "FEDERAL":
                    continue

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
            state = state_check(hosts["org"])
            hash_object = hashlib.sha256(str(hosts["ip_str"]).encode("utf-8"))
            ip_hash = hash_object.hexdigest()
            if state and org.type == "FEDERAL":
                continue

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
    if len(float_ips) > 0:
        update_shodan_ips(float_ips, org)


def search(api, query, ip_obj, cidr, org_type):
    """Search Shodan API using query and add IPs to set."""
    # Wrap the request in a try/ except block to catch errors
    try:
        # Search Shodan
        try:
            results = api.search(query)
        except shodan.exception.APIError:
            time.sleep(2)
            results = api.search(query)

        for result in results["matches"]:
            # if ":" in result["ip_str"]:
            #     LOGGER.info("ipv6 found ", result["ip_str"])
            #     ip_type = "ipv6"
            # else:
            #     ip_type = "ipv4"
            state = state_check(result["org"])
            hash_object = hashlib.sha256(str(result["ip_str"]).encode("utf-8"))
            ip_hash = hash_object.hexdigest()
            if state and org_type == "FEDERAL":
                continue

            ip_obj.append(
                {
                    "ip_hash": ip_hash,
                    "ip": result["ip_str"],
                    "shodan_results": True,
                    "origin_cidr": cidr,
                    "current": True,
                }
            )
        i = 1
        while i < results["total"] / 100:
            try:
                # Search Shodan
                try:
                    results = api.search(query=query, page=i)
                except shodan.exception.APIError:
                    time.sleep(2)
                    results = api.search(query, page=i)
                # Show the results
                for result in results["matches"]:
                    # if ":" in result["ip_str"]:
                    #     LOGGER.info("ipv6 found ", result["ip_str"])
                    #     ip_type = "ipv6"
                    # else:
                    #     ip_type = "ipv4"
                    state = state_check(result["org"])
                    hash_object = hashlib.sha256(str(result["ip_str"]).encode("utf-8"))
                    ip_hash = hash_object.hexdigest()
                    if state and org_type == "FEDERAL":
                        continue

                    ip_obj.append(
                        {
                            "ip_hash": ip_hash,
                            "ip": result["ip_str"],
                            "shodan_results": True,
                            "origin_cidr": cidr,
                            "current": True,
                        }
                    )
                i = i + 1
            except shodan.APIError as e:
                LOGGER.error("Error: %s", e)
                LOGGER.error(query)
                results = {"total": 0}
    except shodan.APIError as e:
        LOGGER.error("Error: %s", e)
        # IF it breaks to here it fails
        LOGGER.error("Failed on %s", query)
        return 0
    return results["total"]


def dedupe(orgs_obj_list=None):
    """Check list of IPs, CIDRs, ASNS, and FQDNs in Shodan and output set of IPs."""
    # Get P&E organizations DataFrame
    if not orgs_obj_list:
        orgs_obj_list = Organization.objects.all()
    num_orgs = len(orgs_obj_list)
    api = connect_to_shodan()
    # Loop through orgs
    org_count = 1
    for org in orgs_obj_list:
        # Connect to database
        LOGGER.info(
            "Running Shodan dedupe on %s, %d/%d",
            org.acronym,
            org_count,
            num_orgs,
        )
        # Query CIDRS
        cidrs = Cidr.objects.filter(cidrorgs__organization=org, cidrorgs__current=True)
        LOGGER.info("%d CIDRs found", len(cidrs))
        # Run cidr dedupe if there are CIDRs
        if len(cidrs) > 0:
            cidr_dedupe(cidrs, api, org)

        # Get IPs related to current sub-domains
        LOGGER.info("Retrieving floating IPs")
        ips = (
            Ip.objects.filter(
                origin_cidr__isnull=True,  # No origin_cidr linked
                current=True,  # Ip must be marked as current
                sub_domains__current=True,  # The related subdomains must be current
                sub_domains__organization=org,
                ipssubs__current=True,  # The linking table IpsSubs must have current=True
            )
            .distinct()
            .values_list("ip", flat=True)
        )
        LOGGER.info("Floating IPs retrieved")
        if len(ips) > 0:
            LOGGER.info("Running dedupe on IPs")
            ip_dedupe(api, ips, org)
        LOGGER.info("Finished dedupe")

        org_count += 1


def main():
    """Run all orgs net assets through the dedupe process."""
    dedupe(False)


if __name__ == "__main__":
    main()
