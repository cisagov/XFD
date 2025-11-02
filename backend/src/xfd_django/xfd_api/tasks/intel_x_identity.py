"""Collect Intelx credential leak data."""
# Standard Python Libraries
import datetime
import logging
import os
import sys
import time

# Third-Party Libraries
import django
from django.db.models import Q
from django.utils import timezone
import numpy as np
import pandas as pd
import requests
from xfd_api.helpers.data_pull_history import get_last_queried, update_query_timestamp
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    DataSource,
    Organization,
    SubDomains,
)

# Calculate Datetimes for collection period
TODAY = timezone.now()
DAYS_BACK = datetime.timedelta(days=100)
START_DATE = (TODAY - DAYS_BACK).strftime("%Y-%m-%d %H:%M:%S")
END_DATE = TODAY.strftime("%Y-%m-%d %H:%M:%S")

LOGGER = logging.getLogger(__name__)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
# Constants
MAX_RETRIES = 3  # Max retries for failed tasks
TIMEOUT = 60  # Timeout in seconds for waiting on task completion
BASE_URL = "https://3.intelx.io"
api_key = os.getenv("INTELX_KEY")

# Get data source uid
SOURCE_OBJ, created = DataSource.objects.get_or_create(
    name="IntelX",
    defaults={
        "description": "Credentials and web posts identified by IntelX.",
        "last_run": timezone.now().date(),  # Sets the current date and time
    },
)


def handler(command_options):
    """Identify credential breaches associated with stakeholder's root domains."""
    try:
        is_dmz = os.getenv("IS_DMZ")
        is_local = os.getenv("IS_LOCAL")
        if str(is_dmz).lower() not in {"true", "1"} and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exitting now.")
            return {
                "status_code": 200,
                "body": "IntelX Credential scan cannot run outside the DMZ.",
            }
        main(command_options)
        return {
            "status_code": 200,
            "body": "IntelX Credential scan completed successfully.",
        }
    except Exception as e:
        return {"status_code": 500, "body": str(e)}


def main(command_options):
    """Identify credential breaches associated with stakeholder's root domains."""
    try:
        organization_name = command_options.get("organizationName")
        organization_id = command_options.get("organizationId")
        if not organization_name or not organization_id:
            return {"statusCode": 400, "body": "Organization name or id not provided."}

        orgs_to_sync = Organization.objects.filter(id=organization_id)
        if not orgs_to_sync.exists():
            return {"statusCode": 500, "body": "Organization not found."}

        organization = orgs_to_sync.first()

        intelx = IntelX([organization])
        intelx.run_intelx()

        return {
            "statusCode": 200,
            "body": "Credential breach scan completed successfully.",
        }

    except Exception as e:
        LOGGER.error("Error running IntelX Credential Scan %s", e)
        return {"statusCode": 500, "body": "Internal server error."}


class IntelX:
    """Fetch IntelX data."""

    def __init__(self, org_objects: list[Organization]):
        """Initialize IntelX class."""
        self.org_objects = org_objects

    def run_intelx(self):
        """Run IntelX api calls."""
        LOGGER.info("Running IntelX")
        orgs_objects = self.org_objects

        # Run IntelX on each org
        success = 0
        failed = 0
        index = 0
        total_org_count = len(orgs_objects)
        for org in orgs_objects:
            LOGGER.info(
                "Running IntelX on %s (%d of %d)",
                org.acronym,
                index + 1,
                total_org_count,
            )

            if self.get_credentials(org) == 1:
                LOGGER.error(
                    "Failed to retrieve IntelX credentials for %s", org.acronym
                )
                failed += 1
            else:
                success += 1
            index += 1
        # Log summary statistics
        LOGGER.info(
            "IntelX scan ran successfully for %d/%d organizations",
            success,
            total_org_count,
        )
        LOGGER.info(
            "IntelX scan had significant failures for %d/%d organizations",
            failed,
            total_org_count,
        )

    def get_credentials(self, org: Organization):
        """Get credentials for a provided org."""
        # Get the org root domains
        LOGGER.info("Retrieving root domains for %s", org.acronym)
        try:
            roots = (
                SubDomains.objects.filter(
                    is_root_domain=True, organization__id=org.id, current=True
                )
                .filter(Q(enumerate_subs=True) | Q(enumerate_subs=None))
                .exclude(identified=True)
            )

        except Exception as e:
            LOGGER.error("Failed fetching root domains for %s", org.acronym)
            LOGGER.error(e)
            return 1

        # Catch situation where org has no eligble root domains
        if not roots.exists():
            LOGGER.warning(
                "%s does not have any eligible root domains for IntelX", org.acronym
            )
            return 0

        # Retrieve credential leaks from IntelX
        LOGGER.info("Retrieving IntelX findings for %s", org.acronym)
        since_timestamp = get_last_queried(org, "intel_x_pull")
        if since_timestamp:
            start = since_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            start = START_DATE
        start_pulling_time = datetime.datetime.now(datetime.timezone.utc)
        count = 0
        for root in roots:
            LOGGER.info(
                "IntelX working on domain: %s %d/%d",
                root.sub_domain,
                count + 1,
                len(roots),
            )
            count += 1
            leaks_json = self.find_credential_leaks(root, start, END_DATE)

            # Process and format results
            if len(leaks_json) < 1:
                LOGGER.info("No IntelX credentials found for %s", root.sub_domain)
                continue
            creds_df, breaches_df = self.process_leaks_results(leaks_json, org)
            # Insert breach data into the PE database
            LOGGER.info("Inserting IntelX breach data for %s", root.sub_domain)
            try:
                breach_dict = insert_intelx_breaches(breaches_df)
                # insert_intelx_breaches(breaches_df)
            except Exception as e:
                LOGGER.error(
                    "Failed inserting IntelX breach data for %s", root.sub_domain
                )
                LOGGER.error(e)
                continue

            # Insert credential data into the PE database
            LOGGER.info("Inserting IntelX credential data for %s", root.sub_domain)
            try:
                insert_intelx_credentials(creds_df, breach_dict, org, root)

            except Exception as e:
                LOGGER.error(
                    "Failed inserting IntelX credential data for %s", root.sub_domain
                )
                LOGGER.error(e)
                continue
        update_query_timestamp(
            org,
            "intel_x_pull",
            start_pulling_time,
        )
        return 0

    def query_identity_api(self, domain, start_date, end_date):
        """Create an initial search and return the search id."""
        url = (
            BASE_URL
            + "/accounts/csv?selector={domain}&k={api_key}&datefrom={start_date}&dateto={end_date}".format(
                domain=domain, api_key=api_key, start_date=start_date, end_date=end_date
            )
        )
        payload = {}
        headers = {}
        attempts = 0
        # Call IntelX endpoint to submit initial search query
        while attempts < 5:
            try:
                response = requests.request(
                    "GET", url, headers=headers, data=payload, timeout=TIMEOUT
                )
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                time.sleep(5)
                attempts += 1
                if attempts == 5:
                    LOGGER.error("IntelX identity is not responding. Exiting program.")
                    sys.exit()
                LOGGER.info("IntelX Identity API response timed out. Trying again.")
            except Exception as e:
                LOGGER.error("Error occured getting search id: %s", e)
                return 0
        time.sleep(5)
        return response.json()

    def get_search_results(self, search_id):
        """Search IntelX for email leaks."""
        url = BASE_URL + "/live/search/result?id={id}&format=1&k={api_key}".format(
            id=search_id, api_key=api_key
        )
        payload = {}
        headers = {}
        attempts = 0
        # Call IntelX endpoint to retrieve search results
        try:
            response = requests.request(
                "GET", url, headers=headers, data=payload, timeout=TIMEOUT
            )
        except requests.exceptions.Timeout:
            time.sleep(5)
            attempts += 1
            if attempts == 5:
                LOGGER.error("IntelX identity is not responding. Exiting program.")
                sys.exit()
            LOGGER.info("IntelX Identity API response timed out. Trying again.")
        except Exception as e:
            LOGGER.error("Error occured geting search results: %s", e)
            return 0
        response = response.json()

        return response

    def find_credential_leaks(self, root_obj: SubDomains, start_date, end_date):
        """Find leaks for a domain between two dates."""
        # Retrieve results for each domain

        all_results_list: list[dict] = []

        if not root_obj:
            return all_results_list

        response = self.query_identity_api(root_obj.sub_domain, start_date, end_date)
        if not response:
            return all_results_list
        search_id = response["id"]
        while True:
            # Retrieve full results for the search id
            results = self.get_search_results(search_id)
            if not results:
                break
            # If status is 0, there are still more results to retrieve
            if results["status"] == 0:
                current_results = results["records"]
                if current_results:
                    # Add the root_domain to each result object
                    LOGGER.info(
                        "Intelx returned %d more credentials for %s",
                        len(current_results),
                        root_obj.sub_domain,
                    )
                    result = [
                        dict(item, **{"root_domain": root_obj.sub_domain})
                        for item in current_results
                    ]
                    all_results_list = all_results_list + result
                time.sleep(3)
            # If status is 1, IntelX is still working on it (wait)
            elif results["status"] == 1:
                # LOGGER.info("Intelx still searching for more credentials")
                time.sleep(7)
            # if status is 2, collect the final remaining results and exit loop
            elif results["status"] == 2:
                current_results = results["records"]
                if current_results:
                    # Add the root_domain to each result object
                    LOGGER.info(
                        "Intelx returned %d more credentials for %s",
                        len(current_results),
                        root_obj.sub_domain,
                    )
                    result = [
                        dict(item, **{"root_domain": root_obj.sub_domain})
                        for item in current_results
                    ]
                    all_results_list = all_results_list + result
                break
            # If status is 3, invalid search id error
            elif results["status"] == 3:
                LOGGER.error("Search id not found")
                break
        # Return all results
        return all_results_list

    def process_leaks_results(self, leaks_json, org):
        """Prepare and format credentials and breach dataframes."""
        # Convert json into a dataframe
        all_df = pd.DataFrame.from_dict(leaks_json)
        # format email to all lowercase and remove duplicates
        all_df["user"] = all_df["user"].str.lower()
        # Log stats
        num_email = all_df["user"].nunique()
        num_post = all_df["sourceshort"].nunique()
        all_df = all_df.drop_duplicates(subset=["user", "sourceshort"], keep="first")
        # num emails after removing duplicates in the same post
        num_email_dedupe = len(leaks_json)
        LOGGER.info(
            "IntelX results %s: %d unique emails, %d unique posts, %d email/post pairs",
            org.acronym,
            num_email,
            num_post,
            num_email_dedupe,
        )
        # Format date
        all_df["breach_datetime"] = pd.to_datetime(all_df["date"])
        # all_df["breach_date"] = all_df["datetime"].dt.strftime("%Y-%m-%d")
        all_df["added_date"] = pd.to_datetime(all_df["added"])
        all_df["modified_date"] = pd.to_datetime(all_df["added"])

        # Create boolean column for if password is included
        all_df["password_included"] = np.where(
            (pd.isna(all_df["password"])) | (all_df["password"] == ""), 0, 1
        )
        # Create new column for subdomain, organization uid, and data source uid
        all_df["sub_domain"] = all_df["user"].str.split("@").str[1]
        # all_df["organizations"] = org
        # all_df["data_source_uid"] = SOURCE_UID
        # rename fields to match database
        all_df.rename(
            columns={
                "user": "email",
                "sourceshort": "breach_name",
                "systemid": "intelx_system_id",
                "passwordtype": "hash_type",
            },
            inplace=True,
        )
        # Select specific columns
        creds_df = all_df[
            [
                "email",
                "root_domain",
                "sub_domain",
                "breach_name",
                "modified_date",
                "password",
                "hash_type",
                "intelx_system_id",
            ]
        ].reset_index(drop=True)
        # group results by breaches
        breaches_df = all_df.groupby(["breach_name", "bucket"]).aggregate(
            {
                "email": "count",
                "password_included": "sum",
                "modified_date": "max",
                "added_date": "min",
                "breach_datetime": "min",
            }
        )
        breaches_df = breaches_df.reset_index()
        breaches_df["password_included"] = breaches_df["password_included"] > 0
        # Build breach description
        breaches_df.rename(columns={"email": "exposed_cred_count"}, inplace=True)
        breaches_df["description"] = (
            breaches_df["breach_name"]
            + " was identified on "
            + breaches_df["modified_date"].dt.strftime("%Y-%m-%d")
            + ". The post "
            + (
                "does not contain"
                if breaches_df["password_included"] is True
                else "contains"
            )
            + " passwords. It falls in the following category: "
            + breaches_df["bucket"]
        )
        breaches_df["breach_date"] = breaches_df["breach_datetime"].dt.strftime(
            "%Y-%m-%d"
        )
        breaches_df = breaches_df[
            [
                "breach_name",
                "description",
                "breach_date",
                "added_date",
                "modified_date",
                "password_included",
            ]
        ]
        # Return processed data
        return creds_df, breaches_df


def insert_intelx_breaches(df):
    """Save breach dataframe to DB."""
    breach_dict = {}
    df = df.drop_duplicates(subset=["breach_name"])
    df_dict_list = df.to_dict("records")

    for breach in df_dict_list:
        breach_obj, created = CredentialBreaches.objects.get_or_create(
            breach_name=breach.get("breach_name"),
            defaults={
                "description": breach.get("description"),
                "breach_date": breach.get("breach_date"),
                "added_date": breach.get("added_date"),
                "modified_date": datetime.datetime.now(datetime.timezone.utc),
                "password_included": breach.get("password_included"),
                "data_source": SOURCE_OBJ,
            },
        )

        if not created:
            breach_obj.modified_date = datetime.datetime.now(datetime.timezone.utc)
            breach_obj.save()

        breach_dict[breach.get("breach_name")] = breach_obj

    return breach_dict


def insert_intelx_credentials(df, breach_obj_dict, org: Organization, root: SubDomains):
    """Save intelx credentials to DB."""
    df_dict_list = df.to_dict("records")

    for exposure in df_dict_list:
        if root.sub_domain == exposure.get("sub_domain"):
            sub = root
        else:
            sub, created = SubDomains.objects.get_or_create(
                organization=org,
                sub_domain=exposure.get("sub_domain"),
                defaults={
                    "root_domain": root,
                    "is_root_domain": False,
                    "data_source": SOURCE_OBJ,
                    "subdomain_source": "IntelX",
                    "first_seen": datetime.datetime.now(datetime.timezone.utc),
                    "last_seen": datetime.datetime.now(datetime.timezone.utc),
                    "from_root_domain": root.sub_domain,
                    "identified": True,
                    "current": True,
                },
            )
            if created:
                sub.last_seen = datetime.datetime.now(datetime.timezone.utc)
                sub.current = True
                sub.save()

        CredentialExposures.objects.get_or_create(
            email=exposure.get("email"),
            breach_name=exposure.get("breach_name"),
            organization=org,
            defaults={
                "root_domain": exposure.get("root_domain"),
                "sub_domain_string": exposure.get("sub_domain"),
                "sub_domain": sub,
                "credential_breach": breach_obj_dict.get(exposure.get("breach_name")),
                "modified_date": exposure.get("modified_date"),
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "data_source": SOURCE_OBJ,
                "password": exposure.get("password"),
                "hash_type": exposure.get("hash_type"),
                "intelx_system_id": exposure.get("intelx_system_id"),
            },
        )
