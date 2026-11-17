"""Script to run the remote portion of the ASM Sync process."""

# Standard Python Libraries
from datetime import timedelta
import logging
import time

# Third-Party Libraries
import pandas as pd
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
    #Track the start time of the ASM Sync process
    upsert_cidrs_total_time = 0
    update_cidrs_status_total_time = 0
    enum_subs_from_roots_total_time = 0
    enum_subs_from_ips_total_time = 0
    update_ips_status_total_time = 0
    update_subs_status_total_time = 0
    update_ips_subs_status_total_time = 0
    update_subs_identified_total_time = 0
    shodan_dedupe_total_time = 0
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
            f"Running ASM Sync process on {curr_org_name}, {idx + 1} of {len(orgs_df)}"
        )
        # Fill the cidrs table with new data from the cyhy_db_assets
        LOGGER.info("Upserting latest CyHy CIDR assets into the CIDRs table...")
        upsert_cidrs_start = time.time()
        upsert_cyhy_cidrs(curr_org_df)
        upsert_cidrs_time = time.time() - upsert_cidrs_start
        upsert_cidrs_total_time += upsert_cidrs_time
        LOGGER.info("Finished upserting latest CyHy CIDR assets into the CIDRs table")
        # Update CIDRs "current" status
        LOGGER.info("Updating statuses of this org's CIDRs...")
        update_cidrs_status_start = time.time()
        update_cidrs_status(curr_org_uid)
        update_cidrs_status_time = time.time() - update_cidrs_status_start
        update_cidrs_status_total_time += update_cidrs_status_time
        LOGGER.info("Finished updating statuses of this org's CIDRs")
        # Enumerate subdomains from roots
        LOGGER.info("Enumerating sub-domains from root domains...")
        enum_subs_from_roots_start = time.time()
        enum_subs_from_roots(curr_org_df)
        enum_subs_from_roots_time = time.time() - enum_subs_from_roots_start
        enum_subs_from_roots_total_time += enum_subs_from_roots_time
        LOGGER.info("Finished enumerating sub-domains from root domains")
        # Enumerate subdomains by performing PTR-based reverse lookup on IPs
        LOGGER.info("Enumerating sub-domains from IPs via reverse lookup...")
        enum_subs_from_ips_start = time.time()
        enum_subs_from_ips(curr_org_df)
        enum_subs_from_ips_time = time.time() - enum_subs_from_ips_start
        enum_subs_from_ips_total_time += enum_subs_from_ips_time
        LOGGER.info("Finished enumerating sub-domains from IPs via reverse lookup")
        # Update "current" and "identified" status for IPs, subdomains, and ips_subs records
        LOGGER.info("Updating statuses of this org's IPs...")
        update_ip_status_start = time.time()
        update_ips_status(curr_org_uid)
        update_ip_status_time = time.time() - update_ip_status_start
        update_ips_status_total_time += update_ip_status_time
        LOGGER.info("Finished updating statuses of this org's IPs...")
        #Update the current status for subdomains
        LOGGER.info("Updating statuses of this org's subdomains...")
        update_subs_status_start = time.time()
        update_subs_status(curr_org_uid)
        update_subs_status_time = time.time() - update_subs_status_start
        update_subs_status_total_time += update_subs_status_time
        LOGGER.info("Finished updating statuses of this org's subdomains")
        # Update the current status for IP-subdomain links
        LOGGER.info("Updating statuses of this org's IP-subdomains links...")
        update_ips_subs_status_start = time.time()
        update_ips_subs_status(curr_org_uid)
        update_ips_subs_status_time = time.time() - update_ips_subs_status_start
        update_ips_subs_status_total_time += update_ips_subs_status_time
        LOGGER.info("Finished updating statuses of this org's IP-subdomains links")
        # Update the identified field for subdomains
        LOGGER.info("Updating identified field for this org's subdomains...")
        update_subs_identified_start = time.time()
        update_subs_identified(curr_org_uid)
        update_subs_identified_time = time.time() - update_subs_identified_start
        update_subs_identified_total_time += update_subs_identified_time
        LOGGER.info("Finished updating identified field for this org's subdomains")
        # Mark which IPs have Shodan results
        LOGGER.info("Marking IPs with Shodan results...")
        shodan_dedupe_start = time.time()
        shodan_dedupe(curr_org_df)
        shodan_dedupe_time = time.time() - shodan_dedupe_start
        shodan_dedupe_total_time += shodan_dedupe_time
        LOGGER.info("Finished marking IPs with Shodan results")
        LOGGER.info(
            f"Finished running ASM Sync on {curr_org_name}, {idx + 1} of {len(orgs_df)}"
        )
        
    sqs_asm_end = time.time()
    LOGGER.info(
        f"SQS ASM Sync execution time for {orgs_logging}: {str(timedelta(seconds=(sqs_asm_end - sqs_asm_start)))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Upserting Cidrs: {str(timedelta(seconds=upsert_cidrs_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Updating Cidrs Status: {str(timedelta(seconds=update_cidrs_status_total_time))} (H:M:S)"
    )
    LOGGER.info(
        F"Total ASM Sync execution time for Enumerating Subdomains from Roots: {str(timedelta(seconds=enum_subs_from_roots_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Enumerating Subdomains from IPs: {str(timedelta(seconds=enum_subs_from_ips_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Updating IPs: {str(timedelta(seconds=update_ips_status_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Updating Subdomains: {str(timedelta(seconds=update_subs_status_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Updating IP-Subdomain Links: {str(timedelta(seconds=update_ips_subs_status_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Updating Subdomains Identified Field: {str(timedelta(seconds=update_subs_identified_total_time))} (H:M:S)"
    )
    LOGGER.info(
        f"Total ASM Sync execution time for Shodan Dedupe: {str(timedelta(seconds=shodan_dedupe_total_time))} (H:M:S)"
    )
    LOGGER.info(f"--- SQS ASM Sync Process Complete for {orgs_logging} ---")
