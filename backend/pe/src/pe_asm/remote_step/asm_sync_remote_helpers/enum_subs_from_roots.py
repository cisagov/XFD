"""Script to enumerate subdomains from organization's root domains."""

# Standard Python Libraries
import datetime
import json
import logging
import os
import time

# Third-Party Libraries
import pandas as pd
from pe_asm.remote_step.asm_sync_remote_query import (
    get_data_source_uid,
    insert_sub_domains,
    query_roots,
)
import requests

# Setup logging
LOGGER = logging.getLogger(__name__)


def whoisxml_enum_subs_from_root(root_domain, root_uid):
    """Get all sub-domains from passed in root domain."""
    today = datetime.datetime.today().date()
    whois_api_key = os.environ.get("WHOIS_XML_KEY")
    # Call API endpoint
    url = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1"
    payload = json.dumps(
        {
            "apiKey": f"{whois_api_key}",
            "domains": {"include": [f"{root_domain}"]},
            "subdomains": {"include": ["*"], "exclude": []},
        }
    )
    headers = {"Content-Type": "application/json"}
    response = requests.request("POST", url, headers=headers, data=payload)
    # Retry clause
    retry_count, max_retries, time_delay = 1, 10, 5
    while response.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            f"Retrying WhoisXML API endpoint (code {response.status_code}), attempt {retry_count} of {max_retries} (url: {url})"
        )
        time.sleep(time_delay)
        response = requests.request("POST", url, headers=headers, data=payload)
        retry_count += 1
    data = response.json()
    sub_domains = data["domainsList"]
    data_source = get_data_source_uid("WhoisXML")
    # First add the root domain to the total subs list
    found_subs = [
        {
            "sub_domain": root_domain,
            "root_domain_uid": root_uid,
            "data_source_uid": data_source,
            "first_seen": today,
            "last_seen": today,
            "identified": False,
        }
    ]
    # Then add any found subdomains that aren't www.<root>.gov to the total list
    for sub in sub_domains:
        if sub != f"www.{root_domain}":
            found_subs.append(
                {
                    "sub_domain": sub,
                    "root_domain_uid": root_uid,
                    "data_source_uid": data_source,
                    "first_seen": today,
                    "last_seen": today,
                    "identified": False,
                }
            )
    return found_subs


def enum_subs_from_roots(orgs_df=None):
    """Enumerate roots and save subdomains."""
    # Get root domains for this org
    roots_df = query_roots(list(orgs_df["organizations_uid"]))
    total_roots = len(roots_df.index)
    LOGGER.info("Found %d root domains", total_roots)
    # Iterate over roots
    count = 0
    for root_index, root_row in roots_df.iterrows():
        # Enumerate for sub-domains
        LOGGER.info("Enumerating this root: %s", root_row["root_domain"])
        subs = whoisxml_enum_subs_from_root(
            root_row["root_domain"], root_row["root_domain_uid"]
        )
        subs_df = pd.DataFrame(subs)
        # Insert into P&E database
        insert_sub_domains(subs_df)
        count += 1
        if count % 10 == 0 or count == total_roots:
            LOGGER.info("\t\t%d/%d roots enumerated", count, total_roots)


def main():
    """Query org's root domains and run them through the enuemeration function to get subdomains."""
    enum_subs_from_roots(False)


if __name__ == "__main__":
    main()
