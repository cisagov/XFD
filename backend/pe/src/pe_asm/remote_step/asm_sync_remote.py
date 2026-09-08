"""Script to run the remote portion of the ASM Sync process."""

# Standard Python Libraries
from datetime import timedelta
import logging
import time

# Third-Party Libraries
import pandas as pd
from pe_asm.remote_step.asm_sync_remote_helpers.enum_ips_from_subs import (
    enum_ips_from_subs,
)
from pe_asm.remote_step.asm_sync_remote_helpers.enum_subs_from_ips import (
    enum_subs_from_ips,
)
from pe_asm.remote_step.asm_sync_remote_helpers.enum_subs_from_roots import (
    enum_subs_from_roots,
)
from pe_asm.remote_step.asm_sync_remote_helpers.shodan_dedupe import shodan_dedupe
from pe_asm.remote_step.asm_sync_remote_helpers.upsert_cyhy_cidrs import (
    upsert_cyhy_cidrs,
)
from pe_asm.remote_step.asm_sync_remote_query import (
    get_orgs,
    update_cidrs_status,
    update_ips_status,
    update_ips_subs_status,
    update_subs_identified,
    update_subs_status,
)

# Setup logging
LOGGER = logging.getLogger(__name__)


def run_asm_sync_remote(orgs_list):
    """Run the remote phase of the ASM Sync process."""
    # Only run on the specified orgs
    all_orgs = get_orgs()
    if orgs_list == "all":
        orgs_list_final = [d for d in all_orgs if d.get("report_on")]
    elif orgs_list == "DEMO":
        orgs_list_final = [d for d in all_orgs if d.get("demo")]
    else:
        orgs_list = orgs_list.split(",")
        orgs_list_final = [
            d for d in all_orgs if d.get("cyhy_db_name") in set(orgs_list)
        ]
    orgs_list_final = sorted(orgs_list_final, key=lambda d: d["cyhy_db_name"])
    if len(orgs_list_final) > 1:
        start_org = orgs_list_final[0].get("cyhy_db_name")
        end_org = orgs_list_final[-1].get("cyhy_db_name")
        orgs_logging = f"{start_org} - {end_org}"
    else:
        orgs_logging = orgs_list_final[0].get("cyhy_db_name")

    LOGGER.info(f"--- SQS ASM Sync Process Starting for {orgs_logging} ---")
    sqs_asm_start = time.time()
    # Retrieve additional info for the specified orgs
    orgs_df = pd.DataFrame(orgs_list_final)
    orgs_df = orgs_df[["organizations_uid", "cyhy_db_name", "name", "agency_type"]]

    # Begin iterating over each org
    for idx, org in orgs_df.iterrows():
        # Run ASM Sync process for this org
        curr_org_name = org.get("cyhy_db_name")
        curr_org_df = org.to_frame().T
        curr_org_uid = list(curr_org_df["organizations_uid"])
        LOGGER.info(
            f"Running ASM Sync process on {curr_org_name}, {idx+1} of {len(orgs_df)}"
        )
        # Fill the cidrs table with new data from the cyhy_db_assets
        LOGGER.info("Upserting retieved CyHy CIDR assets into the CIDRs table...")
        upsert_cyhy_cidrs(curr_org_df)
        LOGGER.info("Finished upserting retieved CyHy CIDR assets into the CIDRs table")
        # Update CIDRs "current" status
        LOGGER.info("Updating statuses of this org's CIDRs...")
        update_cidrs_status(curr_org_uid)
        LOGGER.info("Finished updating statuses of this org's CIDRs")
        # Enumerate subdomains from roots
        LOGGER.info("Enumerating sub-domains from root domains...")
        enum_subs_from_roots(curr_org_df)
        LOGGER.info("Finished enumerating sub-domains from root domains")
        # Enumerate subdomains from IPs, this takes the longest
        LOGGER.info("Enumerating sub-domains from IPs...")
        enum_subs_from_ips(curr_org_df)
        LOGGER.info("Finished enumerating sub-domains from IPs")
        # Enumerate IPs from subdomains
        LOGGER.info("Enumerating IPs sub-domains...")
        enum_ips_from_subs(curr_org_df)
        LOGGER.info("Finished enumerating IPs sub-domains")
        # Identify which IPs, sub-domains, and connections are current
        LOGGER.info("Updating statuses of this org's IPs...")
        update_ips_status(curr_org_uid)
        LOGGER.info("Finished updating statuses of this org's IPs...")
        LOGGER.info("Updating statuses of this org's subdomains...")
        update_subs_status(curr_org_uid)
        LOGGER.info("Finished updating statuses of this org's subdomains")
        LOGGER.info("Updating statuses of this org's IP-subdomains links...")
        update_ips_subs_status(curr_org_uid)
        LOGGER.info("Finished updating statuses of this org's IP-subdomains links")
        LOGGER.info("Updating identified field for this org's subdomains...")
        update_subs_identified(curr_org_uid)
        LOGGER.info("Finished updating identified field for this org's subdomains")
        # Run shodan dedupe using the specified API key
        LOGGER.info("Running Shodan dedupe...")
        shodan_dedupe(curr_org_df)
        LOGGER.info("Finished running Shodan dedupe")
        LOGGER.info(
            f"Finished running ASM Sync on {curr_org_name}, {idx+1} of {len(orgs_df)}"
        )

    sqs_asm_end = time.time()
    LOGGER.info(
        f"SQS ASM Sync execution time for {orgs_logging}: {str(timedelta(seconds=(sqs_asm_end - sqs_asm_start)))} (H:M:S)"
    )
    LOGGER.info(f"--- SQS ASM Sync Process Complete for {orgs_logging} ---")
