"""ASMsync scan."""
# Standard Python Libraries
import datetime
import logging
import os

# Third-Party Libraries
import django
from django.db.models import Q
from django.utils import timezone
import requests
from xfd_api.helpers.date_time_helpers import calculate_days_back
from xfd_api.helpers.dmz_sync_helper import query_api
from xfd_mini_dl.models import Cidr, DataSource, Ip, IpsSubs, Organization, SubDomains

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Constants
LOGGER = logging.getLogger(__name__)
SALT = os.getenv("CHECKSUM_SALT", "default_salt")
MAX_RETRIES = 3  # Max retries for failed tasks
TIMEOUT = 60  # Timeout in seconds for waiting on task completion
HEADERS = {
    "X-API-KEY": os.getenv("DMZ_API_KEY"),
    "Content-Type": "application/json",
}

BASE_URL = os.getenv("DMZ_SYNC_ENDPOINT", "").rstrip("/")
db_name = "mini_data_lake"

unknown_data_source, uds_created = DataSource.objects.using(db_name).get_or_create(
    name="Unknown",
    defaults={
        "description": "Unable to link to one of our data sources.",
        "last_run": timezone.now().date(),  # Sets the current date and time
    },
)


def handler(command_options):
    """Query ASM data for API endpoint."""
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
            "statusCode": 200,
            "body": "ASM DMZ Sync completed successfully.",
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}


def main(command_options):
    """Run ASM Sync API test owned by each stakeholder."""
    try:
        organization_name = command_options.get("organizationName")
        organization_id = command_options.get("organizationId")
        if not organization_name or not organization_id:
            return {"statusCode": 400, "body": "Organization name or id not provided."}

        orgs_to_sync = Organization.objects.using(db_name).filter(id=organization_id)
        if not orgs_to_sync.exists():
            return {"statusCode": 500, "body": "Organization not found."}

        organization = orgs_to_sync.first()
        get_data_sources()

        LOGGER.info("Pulling ASM data for %s", organization.acronym)
        acronym = organization.acronym
        page_size = 10
        page_number = 1

        last_seen_after = calculate_days_back(15)
        response = query_api(
            "/dmz_sync/asm_sync", acronym, last_seen_after, page_size, page_number
        )

        if response:
            total_pages = process_response(response, organization)
        else:
            LOGGER.error("Failed to query DMZ ASM Sync API.")
            return {"statusCode": 500, "body": "Failed to query DMZ ASM Sync API."}

        page_number += 1
        while page_number <= total_pages:
            response = query_api(
                "/dmz_sync/asm_sync", acronym, last_seen_after, page_size, page_number
            )
            if response:
                total_pages = process_response(response, organization)
                page_number += 1
            else:
                LOGGER.error("Failed to query DMZ ASM Sync API.")
                flag_asset_changes(organization)
                return {
                    "statusCode": 500,
                    "body": "Failed during pagination of ASM Sync API.",
                }

        flag_asset_changes(organization)
        LOGGER.info("Completed pulling ASM data for %s", organization.acronym)
        return {"statusCode": 200, "body": "ASM sync completed successfully."}

    except Exception as e:
        LOGGER.error("Error Running Sync ASM Sync: %s", e)
        return {"statusCode": 500, "body": "Internal server error during ASM sync."}


def get_data_sources():
    """Pull and save data sources."""
    url = BASE_URL + "/dmz_sync/data_sources"

    response = requests.request("GET", url, headers=HEADERS, timeout=29)
    if response.status_code == 200:
        data_sources = response.json()

        for data_source in data_sources:
            DataSource.objects.using(db_name).get_or_create(
                name=data_source.get("name"),
                defaults={
                    "description": data_source.get("description"),
                    "last_run": datetime.datetime.fromisoformat(
                        data_source.get("last_run")
                    ).date(),
                },
            )


def process_response(response, org):
    """Save ASM sync response to the MDL."""
    data = response.json()

    for ip_sub in data.get("ip_data", []):
        cidr = Cidr.objects.using(db_name).get(
            network=ip_sub.get("origin_cidr_network"), cidrorgs__organization=org
        )

        ip_obj, created = Ip.objects.using(db_name).get_or_create(
            ip=ip_sub.get("ip"),
            organization=org,
            defaults={
                "ip_hash": ip_sub.get("ip_hash"),
                "created_timestamp": ip_sub.get("created_timestamp"),
                "updated_timestamp": ip_sub.get("updated_timestamp"),
                "last_seen_timestamp": ip_sub.get("last_seen_timestamp"),
                "ip_version": ip_sub.get("ip_version"),
                "live": ip_sub.get("live"),
                "false_positive": ip_sub.get("false_positive"),
                "retired": ip_sub.get("retired"),
                "last_reverse_lookup": ip_sub.get("last_reverse_lookup"),
                "from_cidr": ip_sub.get("from_cidr"),
                "origin_cidr": cidr,
                "has_shodan_results": ip_sub.get("has_shodan_results"),
                "current": ip_sub.get("current"),
                "conflict_alerts": ip_sub.get("conflict_alerts"),
            },
        )
        if not created:
            ip_obj.updated_timestamp = ip_sub.get("updated_timestamp")
            ip_obj.last_seen_timestamp = ip_sub.get("last_seen_timestamp")
            ip_obj.retired = ip_sub.get("retired")
            ip_obj.false_positive = ip_sub.get("false_positive")
            ip_obj.from_cidr = ip_sub.get("from_cidr")
            ip_obj.origin_cidr = cidr
            ip_obj.last_reverse_lookup = ip_sub.get("last_reverse_lookup")
            ip_obj.has_shodan_results = ip_sub.get("has_shodan_results")
            ip_obj.current = ip_sub.get("current")
            ip_obj.conflict_alerts = ip_sub.get("conflict_alerts")
            ip_obj.save()

        for sub_dict in ip_sub.get("ip_sub_list", []):
            sub_obj = save_sub(sub_dict, org)
            if sub_obj:
                IpsSubs.objects.using(db_name).update_or_create(
                    ip=ip_obj,
                    sub_domain=sub_obj,
                    defaults={
                        "first_seen": sub_dict.get("link_first_seen"),
                        "last_seen": sub_dict.get("link_last_seen"),
                        "current": sub_dict.get("link_current"),
                    },
                )

    for loose_sub in data.get("loose_subs", []):
        save_sub(loose_sub, org)

    return data.get("total_pages")


def save_sub(sub_dict, org):
    """Save and update sub_domain."""
    try:
        data_source = DataSource.objects.using(db_name).get(
            name=sub_dict.get("subdomain_source")
        )
    except DataSource.DoesNotExist:
        data_source = unknown_data_source
    try:
        if not sub_dict.get("is_root_domain"):
            root_obj, rd_created = SubDomains.objects.using(db_name).get_or_create(
                sub_domain=sub_dict.get("from_root_domain"),
                organization=org,
                defaults={
                    "is_root_domain": True,
                    "enumerate_subs": False,
                    "current": True,
                    "data_source": unknown_data_source,
                },
            )
        else:
            root_obj = None
        sub_obj, sd_created = SubDomains.objects.using(db_name).get_or_create(
            sub_domain=sub_dict.get("sub_domain"),
            organization=org,
            defaults={
                "root_domain": root_obj,
                "is_root_domain": sub_dict.get("is_root_domain"),
                "data_source": data_source,
                # 'dns_record':
                "status": sub_dict.get("status"),
                "first_seen": sub_dict.get("first_seen"),
                "last_seen": sub_dict.get("last_seen"),
                "created_at": sub_dict.get("created_at"),
                "updated_at": sub_dict.get("updated_at"),
                "current": sub_dict.get("current"),
                "identified": sub_dict.get("identified"),
                "ip_address": sub_dict.get("ip_address"),
                "synced_at": sub_dict.get("synced_at"),
                "from_root_domain": sub_dict.get("from_root_domain"),
                "enumerate_subs": sub_dict.get("enumerate_subs"),
                "subdomain_source": sub_dict.get("subdomain_source"),
                "ip_only": sub_dict.get("ip_only"),
                "reverse_name": sub_dict.get("reverse_name"),
                "screenshot": sub_dict.get("screenshot"),
                "country": sub_dict.get("country"),
                "asn": sub_dict.get("asn"),
                "cloud_hosted": sub_dict.get("cloud_hosted"),
                "ssl": sub_dict.get("ssl"),
                "censys_certificates_results": sub_dict.get(
                    "censys_certificates_results"
                ),
                "trustymail_results": sub_dict.get("trustymail_results"),
            },
        )
        if not sd_created:
            sub_obj.data_source = data_source
            sub_obj.status = sub_dict.get("status")
            sub_obj.first_seen = sub_dict.get("first_seen")
            sub_obj.last_seen = sub_dict.get("last_seen")
            sub_obj.updated_at = sub_dict.get("updated_at")
            sub_obj.current = sub_dict.get("current")
            sub_obj.identified = sub_dict.get("identified")
            sub_obj.ip_address = sub_dict.get("ip_address")
            sub_obj.enumerate_subs = sub_dict.get("enumerate_subs")
            sub_obj.subdomain_source = sub_dict.get("subdomain_source")
            sub_obj.ip_only = sub_dict.get("ip_only")
            sub_obj.reverse_name = sub_dict.get("reverse_name")
            sub_obj.screenshot = sub_dict.get("screenshot")
            sub_obj.country = sub_dict.get("country")
            sub_obj.asn = sub_dict.get("asn")
            sub_obj.cloud_hosted = sub_dict.get("cloud_hosted")
            sub_obj.ssl = sub_dict.get("ssl")
            sub_obj.censys_certificates_results = sub_dict.get(
                "censys_certificates_results"
            )
            sub_obj.trustymail_results = sub_dict.get("trustymail_results")
            sub_obj.save()

        return sub_obj

    except Exception as e:
        LOGGER.warning(sub_dict)
        LOGGER.warning("Failed to save sub domain to mdl: %s", e)
        return None


def flag_asset_changes(org):
    """Mark Ips and Subdomains that are were not seen in the last scan as not current."""
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=5
    )

    SubDomains.objects.using(db_name).filter(
        last_seen__lt=cutoff_date, organization=org
    ).exclude(
        Q(is_root_domain=True) & (Q(identified=False) | Q(identified__isnull=True))
    ).update(
        current=False
    )

    IpsSubs.objects.using(db_name).filter(
        last_seen__lt=cutoff_date, ip__organization=org
    ).update(current=False)

    Ip.objects.using(db_name).filter(
        last_seen_timestamp__lt=cutoff_date, organization=org
    ).update(current=False)
