"""Script to collect data from DNSMonitor for the P&E Reports."""

# Standard Python Libraries
import datetime
import logging

# Third-Party Libraries
from pe_source.data.config_source import get_dnsmonitor_token
from pe_source.data.db_query_source import (
    get_data_source_uid,
    get_orgs,
    get_subdomain_uid,
    insert_domain_alert,
    insert_domain_permu,
    insert_subdomain,
)
from pe_source.dnsmonitor.dnsmonitor_helpers import (
    dnsmonitor_domains,
    get_dns_records,
    get_domain_alerts,
)

# Setup Logging
LOGGER = logging.getLogger(__name__)

# Calculate Timeframe
NOW = datetime.datetime.now()
DAYS_BACK = datetime.timedelta(days=20)
DAY = datetime.timedelta(days=1)
START_DATE = NOW - DAYS_BACK
END_DATE = NOW + DAY


def run_dnsmonitor(orgs_list):
    """Run the DNSMonitor data collection script."""
    # Only run on the specified orgs
    all_orgs = get_orgs()
    if orgs_list == "all":
        orgs_list_final = [d for d in all_orgs if d.get("report_on")]
    elif orgs_list == "demo":
        orgs_list_final = [d for d in all_orgs if d.get("demo")]
    else:
        orgs_list = orgs_list.split(",")
        orgs_list_final = [
            d for d in all_orgs if d.get("cyhy_db_name") in set(orgs_list)
        ]
    orgs_list_final = sorted(orgs_list_final, key=lambda d: d["cyhy_db_name"])
    # Get all of the domains currently being monitored in DNSMonitor
    token = get_dnsmonitor_token()
    all_domains = dnsmonitor_domains(token)
    if all_domains.empty:
        LOGGER.error(
            "Error fetching org-domain mapping or DNSMonitor monitored domains"
        )
        return
    # Iterate over each org
    failed = []
    warnings = []
    for org_idx, org in enumerate(orgs_list_final):
        org_uid = org["organizations_uid"]
        org_code = org["cyhy_db_name"]
        LOGGER.info(
            f"Running DNSMonitor on {org_code} ({org_idx+1} of {len(orgs_list_final)})"
        )
        # Get the DNSMonitor domains associated with this org
        org_domains = all_domains.loc[all_domains["org"] == org_code]
        LOGGER.info(
            f"Found {len(org_domains)} root domains being monitored for {org_code}"
        )
        org_domain_ids = org_domains["domainId"].tolist()
        # Get alerts for the current org if available
        if not org_domain_ids:
            LOGGER.warning(f"No domains being monitored by DNSMonitor for {org_code}")
            warnings.append(f"{org_code} - No domains being monitored")
            continue
        else:
            alerts_df = get_domain_alerts(token, org_domain_ids, START_DATE, END_DATE)
            LOGGER.info("Retrieved %s alerts", len(alerts_df.index))
        # If no alerts found, continue
        if alerts_df.empty:
            LOGGER.warning(f"No DNSMonitor alerts found for {org_code}")
            warnings.append(f"{org_code} - No alerts found")
            continue
        # Process each alert
        for alert_index, alert_row in alerts_df.iterrows():
            # Get the subdomain_uid for this alert's domain
            alert_domain = alert_row["rootDomain"]
            sub_domain_uid = get_subdomain_uid(alert_domain)
            # If subdomain isn't in PE DB yet, attempt to add it
            if (sub_domain_uid == -1) or (not sub_domain_uid):
                LOGGER.info(
                    "Domain %s isn't in the subdomain table, attempting to add it",
                    alert_domain,
                )
                try:
                    insert_subdomain(alert_domain, org_uid, True)
                    LOGGER.info(
                        "Success adding %s to the subdomain table", alert_domain
                    )
                except Exception as e:
                    LOGGER.error("Failure adding domain to subdomain table")
                    LOGGER.error(e)
                    failed.append(
                        f"{org_code} - {alert_domain} - Failed inserting into subdomain table"
                    )
                    continue
                # Once the new subdomain has been created, retrieve its uid
                sub_domain_uid = get_subdomain_uid(alert_domain)
            # Enrich domain alert record
            alerts_df.at[alert_index, "sub_domain_uid"] = sub_domain_uid
            domain_permu = alert_row["domainPermutation"]
            mx_list, ns_list, ipv4, ipv6 = get_dns_records(domain_permu)
            alerts_df.at[alert_index, "mail_server"] = mx_list
            alerts_df.at[alert_index, "name_server"] = ns_list
            alerts_df.at[alert_index, "ipv4"] = ipv4
            alerts_df.at[alert_index, "ipv6"] = ipv6
        # Set the data_source_uid and organization_uid columns
        alerts_df.dropna(subset=["sub_domain_uid"], inplace=True)
        alerts_df["data_source_uid"] = get_data_source_uid("DNSMonitor")
        alerts_df["organizations_uid"] = org_uid
        alerts_df = alerts_df.rename(
            columns={
                "domainPermutation": "domain_permutation",
                "dateCreated": "date_observed",
                "alertType": "alert_type",
                "previousValue": "previous_value",
                "newValue": "new_value",
            }
        )
        # Assemble domain_permutations dataframe
        domain_permu_df = alerts_df[
            [
                "organizations_uid",
                "sub_domain_uid",
                "data_source_uid",
                "domain_permutation",
                "ipv4",
                "ipv6",
                "mail_server",
                "name_server",
                "date_observed",
            ]
        ]
        domain_permu_df = domain_permu_df.drop_duplicates(
            subset=["domain_permutation"], keep="last"
        )
        # Insert into domain_permutations table
        try:
            LOGGER.info(f"Inserting DNSMonitor domain permutations for {org_code}")
            insert_domain_permu(domain_permu_df)
        except Exception as e:
            LOGGER.error(
                "Failed inserting DNSMonitor domain permutations for %s", org_code
            )
            LOGGER.error(e)
            failed.append(f"{org_code} - Failed inserting into domain_permutations")
        # Assemble domain_alerts dataframe
        alerts_df = alerts_df.rename(columns={"date_observed": "date"})
        domain_alerts_df = alerts_df[
            [
                "organizations_uid",
                "sub_domain_uid",
                "data_source_uid",
                "alert_type",
                "message",
                "previous_value",
                "new_value",
                "date",
            ]
        ]
        # Insert into domain_alerts table
        try:
            LOGGER.info(f"Inserting DNSMonitor domain alerts for {org_code}")
            insert_domain_alert(domain_alerts_df)
        except Exception as e:
            LOGGER.error("Failed inserting DNSMonitor domain alerts for %s", org_code)
            LOGGER.error(e)
            failed.append(f"{org_code} - Failed inserting into domain_alerts")

    # Output any warnings
    if len(warnings) > 0:
        LOGGER.warning("Warnings: %s", warnings)
    # Output any failures
    if len(failed) > 0:
        LOGGER.error("Failures: %s", failed)
    # Output summary stats
    num_no_domain_monitor = sum("No domains being monitored" in s for s in warnings)
    num_no_alerts = sum("No alerts found" in s for s in warnings)
    num_success = (
        len(orgs_list_final) - num_no_domain_monitor - num_no_alerts - len(failed)
    )
    num_fail = len(failed)
    LOGGER.info(
        f"{num_no_domain_monitor}/{len(orgs_list_final)} orgs do not have domains being monitored by DNSMonitor"
    )
    LOGGER.info(
        f"{num_no_alerts}/{len(orgs_list_final)} orgs have domains being monitored, but didn't have any new alerts"
    )
    LOGGER.info(
        f"{num_success}/{len(orgs_list_final)} orgs had new DNSMonitor findings and successfully added them to the database"
    )
    LOGGER.info(
        f"{num_fail}/{len(orgs_list_final)} orgs had a significant failure during the DNSMonitor scan"
    )
