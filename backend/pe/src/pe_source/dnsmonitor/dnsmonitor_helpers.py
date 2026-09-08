"""Helper functions for the main DNSMonitor script."""

# Standard Python Libraries
import logging
import socket

# Third-Party Libraries
import dns.resolver
import pandas as pd
from pe_source.data.config_source import create_retry_session
from pe_source.data.db_query_source import get_dnsmonitor_domain_mapping
import requests

# Setup Logging
LOGGER = logging.getLogger(__name__)


def get_monitored_domains(token):
    """Get the domains currently being monitored in DNSMonitor."""
    # Setup API call
    session = create_retry_session()
    url = "https://dns.argosecure.com/dhs/api/GetDomains"
    payload = {}
    headers = {
        "authorization": f"Bearer {token}",
    }
    # Make API Call
    try:
        resp = session.get(url, headers=headers, data=payload, timeout=60)
        resp.raise_for_status()
        resp = resp.json()
        return pd.DataFrame(resp)
    except requests.exceptions.HTTPError as http_err:
        LOGGER.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        LOGGER.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        LOGGER.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as err:
        LOGGER.error(f"Unexpected error occurred: {err}")
    return pd.DataFrame(columns=["domainId", "domainName"])


def dnsmonitor_domains(token):
    """Get all domains currently being monitored in DNSMonitor and what organizations they map to."""
    monitored_domains_df = get_monitored_domains(token)
    domain_org_map_df = get_dnsmonitor_domain_mapping()
    # If list of DNSMonitor domains or org-domain mapping fails, exit
    if monitored_domains_df.empty or domain_org_map_df.empty:
        return pd.DataFrame(columns=["org", "domainName", "domainId"])
    # DNSMonitor Domain-Org Mapping Note:
    # - Some monitored domains are attributed to multiple organizations
    # - DNSMonitor may list the same domain more than once, but with different IDs
    monitored_domains_df = monitored_domains_df.drop_duplicates(
        subset="domainName", keep="first"
    ).reset_index(drop=True)
    domain_id_dict = dict(
        zip(monitored_domains_df["domainName"], monitored_domains_df["domainId"])
    )
    domain_org_map_df["domain_id"] = domain_org_map_df["domain"].map(domain_id_dict)
    domain_org_map_df.dropna(subset=["domain_id"], inplace=True)
    domain_org_map_df["domain_id"] = domain_org_map_df["domain_id"].astype(int)
    domain_org_map_df.rename(
        columns={
            "organization": "org",
            "domain": "domainName",
            "domain_id": "domainId",
        },
        inplace=True,
    )
    domain_org_map_df = (
        domain_org_map_df[
            [
                "org",
                "domainName",
                "domainId",
            ]
        ]
        .sort_values(by="org")
        .reset_index(drop=True)
    )
    return domain_org_map_df


def get_domain_alerts(token, domain_ids, from_date, to_date):
    """Get DNSMonitor domain alerts based on specified IDs and dates."""
    # Setup API call
    session = create_retry_session()
    url = "https://dns.argosecure.com/dhs/api/GetAlerts"
    payload = (
        '{\r\n  "domainIds": %s,\r\n  "fromDate": "%s",\r\n  "toDate": "%s",\r\n  "alertType": null,\r\n  "showBufferPeriod": false\r\n}'
        % (str(domain_ids), from_date, to_date)
    )
    headers = {
        "authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # Make API Call
    try:
        resp = session.get(url, headers=headers, data=payload, timeout=60)
        resp.raise_for_status()
        resp = resp.json()
        return pd.DataFrame(resp)
    except requests.exceptions.HTTPError as http_err:
        LOGGER.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        LOGGER.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        LOGGER.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as err:
        LOGGER.error(f"Unexpected error occurred: {err}")
    return pd.DataFrame(
        columns=[
            "domainId",
            "rootDomain",
            "domainPermutation",
            "alertType",
            "message",
            "previousValue",
            "newValue",
            "dateCreated",
        ]
    )


def get_dns_records(domain):
    """Get DNS records for the specified domain."""
    # NS
    try:
        ns_list = []
        dom_ns = dns.resolver.resolve(domain, "NS")
        for data in dom_ns:
            ns_list.append(str(data.target))
    except Exception:
        ns_list = []
    # MX
    try:
        mx_list = []
        dom_mx = dns.resolver.resolve(domain, "MX")
        for data in dom_mx:
            mx_list.append(str(data.exchange))
    except Exception:
        mx_list = []
    # A
    try:
        ip_address = str(socket.gethostbyname(domain))
        if ":" in ip_address:
            ipv6 = ip_address
            ipv4 = ""
        else:
            ipv4 = ip_address
            ipv6 = ""
    except Exception:
        ipv4 = ""
        ipv6 = ""
    return str(mx_list), str(ns_list), ipv4, ipv6
