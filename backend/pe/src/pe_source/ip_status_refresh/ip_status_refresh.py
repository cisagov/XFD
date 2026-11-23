"""Scripts to refresh IP statuses for organizations."""

# Standard Python Libraries
import ipaddress
import logging

# Third-Party Libraries
from pe_source.data.db_query_source import (
    get_current_ips_cidrs_by_org,
    get_orgs,
    update_ip_statuses,
)
from pe_source.dnstwist.dnstwist import _requested_org_names

LOGGER = logging.getLogger(__name__)


def run_ip_status_refresh(orgs_list):
    """Run IP status refresh for the specified list of organizations."""
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
            else:
                continue
    for org_index, org in enumerate(pe_orgs_final):
        cyhy_db_name = org["cyhy_db_name"]
        LOGGER.info("Running IP status refresh for %s", cyhy_db_name)
        list_of_ips_to_update = []
        org_ips = get_current_ips_cidrs_by_org(cyhy_db_name)
        LOGGER.info(
            "Retrieved %s current IPs for org %s", len(org_ips), org["cyhy_db_name"]
        )
        for ip_index, row in org_ips.iterrows():
            ip = row["ip"]
            cidr = row["network"]
            ip_hash = row["ip_hash"]
            try:
                if ipaddress.ip_address(ip) not in ipaddress.ip_network(cidr):
                    list_of_ips_to_update.append(ip)
                    LOGGER.info(
                        "IP %s is not in network %s, updating statuses", ip, cidr
                    )
                    update_ip_statuses(ip_hash)
                    LOGGER.info("Updated IP statuses for %s", ip)
            except ValueError as e:
                LOGGER.error("Invalid IP or network: %s, %s, error: %s", ip, cidr, e)
                continue

        LOGGER.info(
            "IPs updated for org %s: %s",
            org["cyhy_db_name"],
            len(list_of_ips_to_update),
        )
        LOGGER.info("%s out of %s orgs processed", org_index + 1, len(pe_orgs_final))
    LOGGER.info("IP status refresh completed for all orgs.")
