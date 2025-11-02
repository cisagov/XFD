"""CredentialSync scan."""
# Standard Python Libraries
import datetime
import logging
import os

# Third-Party Libraries
import django
from django.conf import settings
from django.utils import timezone
from xfd_api.helpers.data_pull_history import get_last_queried, update_query_timestamp
from xfd_api.helpers.date_time_helpers import calculate_days_back
from xfd_api.helpers.dmz_sync_helper import query_api

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    DataSource,
    Organization,
    SubDomains,
)

LOGGER = logging.getLogger(__name__)


# Constants
MAX_RETRIES = 3  # Max retries for failed tasks
TIMEOUT = 60  # Timeout in seconds for waiting on task completion
db_name = "mini_data_lake"
headers = settings.DMZ_API_HEADER

unknown_data_source, uds_created = DataSource.objects.using(db_name).get_or_create(
    name="Unknown",
    defaults={
        "description": "Unable to link to one of our data sources.",
        "last_run": timezone.now().date(),  # Sets the current date and time
    },
)


def handler(command_options):
    """Retrieve and save credential breaches and exposures from the DMZ."""
    try:
        is_dmz = os.getenv("IS_DMZ")
        is_local = os.getenv("IS_LOCAL")

        if str(is_dmz).lower() in {"true", "1"} and not is_local:
            LOGGER.warning("Scan can only be run in the LZ or locally. Exitting now.")
            return {
                "statusCode": 200,
                "body": "ASM DMZ Sync pull cannot run outside the LZ.",
            }
        main(command_options)
        return {
            "status_code": 200,
            "body": "DMZ credential breaches and exposures sync completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error during DMZ credential sync: %s", e)
        return {"status_code": 500, "body": str(e)}


def main(command_options):
    """Fetch and save DMZ credential breaches and exposures."""
    try:
        organization_name = command_options.get("organizationName")
        organization_id = command_options.get("organizationId")
        data_saved = False
        if not organization_name or not organization_id:
            return {"statusCode": 400, "body": "Organization name or id not provided."}

        orgs_to_sync = Organization.objects.using(db_name).filter(id=organization_id)
        if not orgs_to_sync.exists():
            return {"statusCode": 500, "body": "Organization not found."}

        for org in orgs_to_sync:
            since_timestamp = get_last_queried(org, "credential_sync")
            since_timestamp_str = (
                since_timestamp.isoformat()
                if since_timestamp
                else calculate_days_back(365)
            )

            start_pulling_time = datetime.datetime.now(datetime.timezone.utc)

            LOGGER.info("Processing organization: %s, %s", org.acronym, org.name)
            acronym = org.acronym
            page_size = 10
            page_number = 1
            done = False

            while not done:
                response = query_api(
                    "/dmz_sync/cred_sync",
                    acronym,
                    since_timestamp_str,
                    page_size,
                    page_number,
                )
                if response:
                    LOGGER.info(response.json())
                    result = process_response(response, org)
                    data_saved = result.get("data_saved", data_saved)
                    total_pages = result.get("total_pages", 1)

                else:
                    LOGGER.error("Failed to query DMZ Cred Sync API for %s.", acronym)
                    return {
                        "statusCode": 500,
                        "body": "Failed to query DMZ Cred Sync API for {acronym}.".format(
                            acronym=acronym
                        ),
                    }

                page_number += 1
                if page_number >= total_pages:
                    done = True

            update_query_timestamp(org, "credential_sync", start_pulling_time)
        if data_saved:
            return {
                "statusCode": 200,
                "body": "Credential Sync completed successfully.",
            }
        return {
            "statusCode": 204,
            "body": "Credential Sync found no new data.",
        }

    except Exception as e:
        LOGGER.error("Scan failed to complete: %s", e)
        return {
            "statusCode": 500,
            "body": "Internal server error during credential sync.",
        }


def process_response(response, org):
    """Save credential exposure and breach data to the mini datalake using Django ORM."""
    data = response.json()

    cred_breaches_array = data.get("credential_breaches", [])
    total_pages = data.get("total_pages", 1)
    breaches_saved, exposures_saved = False, False

    if cred_breaches_array:
        breach_dict = {}
        data_source_dict = {}
        for breach in cred_breaches_array:
            try:
                if not data_source_dict.get(
                    breach.get("data_source_name", "Unknown"), None
                ):
                    (
                        data_source_dict[breach.get("data_source_name", "Unknown")],
                        created,
                    ) = DataSource.objects.using(db_name).get_or_create(
                        name=breach.get("data_source_name", "Unknown"),
                        defaults={
                            "description": "Credentials and Breaches identified by {source}".format(
                                source=breach.get("data_source_name", "Unknown")
                            ),
                            "last_run": timezone.now().date(),
                        },
                    )

                if not breach_dict.get(breach.get("breach_name"), None):
                    (
                        breach_dict[breach.get("breach_name")],
                        created,
                    ) = CredentialBreaches.objects.using(db_name).get_or_create(
                        breach_name=breach.get("breach_name"),
                        defaults={
                            "description": breach.get("description"),
                            "exposed_cred_count": breach.get("exposed_cred_count"),
                            "breach_date": datetime.datetime.fromisoformat(
                                breach.get("breach_date")
                            ).date(),
                            "added_date": breach.get("added_date"),
                            "modified_date": breach.get("modified_date"),
                            "data_classes": breach.get("data_classes"),
                            "password_included": breach.get("password_included"),
                            "is_verified": breach.get("is_verified"),
                            "is_fabricated": breach.get("is_fabricated"),
                            "is_sensitive": breach.get("is_sensitive"),
                            "is_retired": breach.get("is_retired"),
                            "is_spam_list": breach.get("is_spam_list"),
                            "data_source": data_source_dict[
                                breach.get("data_source_name", "Unknown")
                            ],
                        },
                    )
                breaches_saved = True
            except Exception as e:
                LOGGER.error("Error saving Cred Breaches: %s", e)

    cred_exposures_array = data.get("credential_exposures", [])
    if cred_exposures_array:
        for exposure in cred_exposures_array:
            try:
                if exposure.get("root_domain") != exposure.get("sub_domain_string"):
                    root_obj, rd_created = SubDomains.objects.using(
                        db_name
                    ).get_or_create(
                        sub_domain=exposure.get("root_domain"),
                        organization=org,
                        defaults={
                            "is_root_domain": True,
                            "enumerate_subs": False,
                            "identified": True,
                            "current": True,
                            "data_source": data_source_dict[
                                exposure.get("data_source_name", "Unknown")
                            ],
                        },
                    )
                else:
                    root_obj = None
                sub_obj, sd_created = SubDomains.objects.using(db_name).get_or_create(
                    sub_domain=exposure.get("sub_domain_string"),
                    organization=org,
                    defaults={
                        "root_domain": root_obj,
                        "is_root_domain": exposure.get("root_domain")
                        == exposure.get("sub_domain_string"),
                        "data_source": data_source_dict[
                            exposure.get("data_source_name", "Unknown")
                        ],
                        "last_seen": datetime.datetime.now(datetime.timezone.utc),
                        "current": True,
                        "identified": True,
                        "from_root_domain": exposure.get("root_domain"),
                        "enumerate_subs": False,
                        "subdomain_source": exposure.get("data_source_name", "Unknown"),
                    },
                )
                if sd_created:
                    sub_obj.current = True
                    sub_obj.last_seen = datetime.datetime.now(datetime.timezone.utc)
                    sub_obj.save()
                CredentialExposures.objects.using(db_name).update_or_create(
                    breach_name=exposure.get("breach_name"),
                    email=exposure.get("email"),
                    defaults={
                        "root_domain": exposure.get("root_domain"),
                        "sub_domain_string": exposure.get("sub_domain"),
                        "modified_date": exposure.get("modified_date"),
                        "name": exposure.get("name"),
                        "login_id": exposure.get("login_id"),
                        "phone": exposure.get("phone"),
                        "password": exposure.get("password"),
                        "hash_type": exposure.get("hash_type"),
                        "intelx_system_id": exposure.get("intelx_system_id"),
                        "organization": org,
                        "credential_breach": breach_dict[exposure.get("breach_name")],
                        "data_source": data_source_dict[
                            exposure.get("data_source_name", "Unknown")
                        ],
                        "sub_domain": sub_obj,
                    },
                )
                exposures_saved = True
            except Exception as e:
                LOGGER.error("Error saving Credential Exposure: %s", e)
    return {
        "total_pages": total_pages,
        "data_saved": exposures_saved or breaches_saved,
    }
