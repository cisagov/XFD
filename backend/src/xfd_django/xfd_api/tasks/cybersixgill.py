"""Tasks for ingesting Cybersixgill alerts, mentions, credentials, and CVEs."""

# Standard Python Libraries
import datetime
import logging
import os
import traceback

# Third-Party Libraries
import django
from django.utils import timezone
import pandas as pd
from xfd_mini_dl.models import CredentialBreaches, DataSource, Organization

from .helpers.sixgill_helpers.api import get_sixgill_organizations
from .helpers.sixgill_helpers.db_query_source import (
    insert_sixgill_alerts,
    insert_sixgill_breaches,
    insert_sixgill_credentials,
    insert_sixgill_mentions,
    insert_sixgill_topCVEs,
)
from .helpers.sixgill_helpers.source import (
    alerts,
    alias_organization,
    creds,
    mentions,
    root_domains,
    top_cves,
)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Logging
LOGGER = logging.getLogger(__name__)

# Dates
TODAY = datetime.date.today()
DAYS_BACK = datetime.timedelta(days=30)
MENTIONS_DAYS_BACK = datetime.timedelta(days=20)
MENTIONS_START_DATE = str(TODAY - MENTIONS_DAYS_BACK)
END_DATE = str(TODAY)
DATE_SPAN = f"[{MENTIONS_START_DATE} TO {END_DATE}]"
NOW = datetime.datetime.now()
START_DATE_TIME = (NOW - DAYS_BACK).strftime("%Y-%m-%d %H:%M:%S")
END_DATE_TIME = NOW.strftime("%Y-%m-%d %H:%M:%S")

SOURCE_OBJ, _ = DataSource.objects.get_or_create(
    name="Cybersixgill",
    defaults={
        "description": "Data from Cybersixgill dark web monitoring",
        "last_run": timezone.now().date(),
    },
)


class Cybersixgill:
    """Main class to run Cybersixgill scans for alerts, mentions, credentials, and CVEs."""

    def __init__(self, org_objects, method_list, soc_med_included):
        """Initialize with orgs, scan methods, and social media inclusion flag."""
        self.org_objects = org_objects
        self.method_list = method_list
        self.soc_med_included = soc_med_included
        self.sixgill_org_map = get_sixgill_organizations()

    def run(self):
        """Run all selected scan methods for each organization."""
        LOGGER.info("Cybersixgill.run() started")
        failed = []

        # Run top CVE scan globally
        if "topCVEs" in self.method_list:
            if self.get_topCVEs() == 1:
                failed.append("Top CVEs")

        # Run per-org scans
        for idx, org in enumerate(self.org_objects):
            org_id = org.acronym
            sixgill_id = self.sixgill_org_map.get(org_id, [None])[0]
            if not sixgill_id:
                LOGGER.warning("%s is not registered in Cybersixgill, skipping", org_id)
                continue

            LOGGER.info(
                "Running CSG on %s (%d/%d)", org_id, idx + 1, len(self.org_objects)
            )

            # Run alert scan
            if "alerts" in self.method_list:
                if self.get_alerts(org, org_id, sixgill_id) == 1:
                    failed.append(f"{org_id} alerts")
            # Run mention scan
            if "mentions" in self.method_list:
                if self.get_mentions(org, org_id, sixgill_id) == 1:
                    failed.append(f"{org_id} mentions")
            # Run credential scan
            if "credentials" in self.method_list:
                if self.get_credentials(org, sixgill_id) == 1:
                    failed.append(f"{org_id} credentials")

        # Log any failed scans
        if failed:
            LOGGER.error("Failures: %s", failed)

    def get_alerts(self, org, org_id, sixgill_id):
        """Fetch and store alerts for an organization."""
        try:
            # Fetch alerts for org
            alerts_df = alerts(org_id, sixgill_id)
            if alerts_df.empty:
                LOGGER.info("No alerts found for %s", org.acronym)
                return 0

            # Clean and format alert date field
            alerts_df["date"] = (
                alerts_df["date"].astype(str).str.replace("“", "").str.replace("”", "")
            )
            alerts_df["date"] = pd.to_datetime(
                alerts_df["date"], errors="coerce"
            ).dt.date

            # Optionally exclude social media platforms
            if not self.soc_med_included:
                soc_platforms = [
                    "twitter",
                    "reddit",
                    "parler",
                    "linkedin",
                    "discord",
                    "telegram",
                ]
                alerts_df = alerts_df[
                    ~alerts_df["site"].str.lower().isin(soc_platforms)
                ]

            alerts_df = alerts_df.rename(columns={"id": "sixgill_id"})
            insert_sixgill_alerts(alerts_df, org, SOURCE_OBJ)
        except Exception as e:
            LOGGER.error("Failed alerts for %s: %s", org.acronym, e)
            LOGGER.error(traceback.format_exc())
            return 1
        return 0

    def get_mentions(self, org, org_id, sixgill_id):
        """Fetch and store mentions for an organization."""
        try:
            # Get organization-specific aliases for mention search
            aliases = alias_organization(sixgill_id)
            if org.acronym == "doi_os":
                aliases = [
                    "DOI Office of the Secretary",
                    "Interior Office of the Secretary",
                ]

            # Fetch mentions using aliases
            mentions_df = mentions(org_id, DATE_SPAN, aliases, self.soc_med_included)
            if mentions_df.empty:
                LOGGER.info("No mentions for %s", org.acronym)
                return 0

            mentions_df = mentions_df.rename(columns={"id": "sixgill_mention_id"})
            mentions_df["date"] = (
                mentions_df["date"]
                .astype(str)
                .str.replace("“", "")
                .str.replace("”", "")
            )
            mentions_df["date"] = pd.to_datetime(mentions_df["date"], errors="coerce")

            insert_sixgill_mentions(mentions_df, org, SOURCE_OBJ)
        except Exception as e:
            LOGGER.error("Failed mentions for %s: %s", org.acronym, e)
            LOGGER.error(traceback.format_exc())
            return 1
        return 0

    def get_credentials(self, org, sixgill_id):
        """Fetch and store leaked credentials and breach info."""
        try:
            # Get root domains linked to org
            roots = root_domains(sixgill_id)
            if not roots:
                LOGGER.info("No root domains for %s", org.acronym)
                return 0

            # Fetch leaked credentials
            creds_df = creds(roots, START_DATE_TIME, END_DATE_TIME)
            if creds_df.empty:
                LOGGER.info("No credentials found for %s", org.acronym)
                return 0

            creds_df["breach_name"].replace("", pd.NA, inplace=True)
            creds_df["breach_name"].fillna(
                "Cybersixgill_" + creds_df["breach_id"].astype(str), inplace=True
            )

            breach_df = creds_df[
                ["breach_name", "description", "breach_date", "password"]
            ].copy()
            breach_df["password_included"] = breach_df["password"] != ""
            breach_df = (
                breach_df.groupby(
                    ["breach_name", "description", "breach_date", "password_included"]
                )
                .size()
                .reset_index(name="exposed_cred_count")
            )
            breach_df["modified_date"] = breach_df["breach_date"]
            breach_df.drop_duplicates(
                subset=["breach_name"], keep="first", inplace=True
            )

            insert_sixgill_breaches(breach_df, SOURCE_OBJ)

            # Build lookup table for breaches already inserted
            breach_lookup = {
                b.breach_name: b
                for b in CredentialBreaches.objects.filter(
                    breach_name__in=creds_df["breach_name"].unique()
                )
            }

            creds_df = creds_df.rename(
                columns={"domain": "sub_domain", "breach_date": "modified_date"}
            )
            creds_df = creds_df[
                [
                    "modified_date",
                    "sub_domain",
                    "email",
                    "hash_type",
                    "name",
                    "login_id",
                    "password",
                    "phone",
                    "breach_name",
                ]
            ]

            insert_sixgill_credentials(
                creds_df, breach_lookup, org, roots[0], SOURCE_OBJ
            )
        except Exception as e:
            LOGGER.error("Failed credentials for %s: %s", org.acronym, e)
            LOGGER.error(traceback.format_exc())
            return 1
        return 0

    def get_topCVEs(self):
        """Fetch and store top 10 global CVEs."""
        try:
            # Get top 10 CVEs
            top_df = top_cves(10)
            top_df["date"] = END_DATE
            top_df["nvd_base_score"] = top_df["nvd_base_score"].astype(str)
            insert_sixgill_topCVEs(top_df, SOURCE_OBJ)
        except Exception as e:
            LOGGER.error("Failed top CVEs: %s", e)
            return 1
        return 0


def handler(event):
    """Entrypoint for running Cybersixgill scan, with DMZ/local check."""
    try:
        # Check if script is allowed to run in current environment
        is_dmz = os.getenv("IS_DMZ")
        is_local = os.getenv("IS_LOCAL")

        if str(is_dmz).lower() not in {"true", "1"} and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exiting now.")
            return {
                "statusCode": 200,
                "body": "Cybersixgill scan cannot run outside the DMZ.",
            }

        # Get all organizations
        orgs = Organization.objects.all()
        LOGGER.info("Number of orgs to scan: %d", orgs.count())

        # Define which scan methods to run
        method_list = ["alerts", "mentions", "credentials", "topCVEs"]

        scan = Cybersixgill(
            org_objects=orgs, method_list=method_list, soc_med_included=False
        )
        scan.run()

        return {
            "statusCode": 200,
            "body": "Cybersixgill scan completed successfully.",
        }

    except Exception as e:
        LOGGER.exception("Cybersixgill scan failed")
        return {"statusCode": 500, "body": str(e)}
