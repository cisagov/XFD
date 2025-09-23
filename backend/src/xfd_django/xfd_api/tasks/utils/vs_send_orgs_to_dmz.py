"""Send orgs to the DMZ helpers."""

# Standard Python Libraries
import json
import logging
import os
import traceback

# Third-Party Libraries
from django.db.models import Exists, OuterRef, Prefetch
import requests
from xfd_api.utils.chunk import chunk_list_by_bytes
from xfd_api.utils.csv_utils import create_checksum
from xfd_api.utils.scan_utils.alerting import SyncError
from xfd_mini_dl.models import CidrOrgs, Organization

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"


def send_organizations_to_dmz():
    """Fetch organizations and sync with the external API."""
    try:
        shaped_orgs = fetch_orgs_and_relations()
        if not shaped_orgs:
            return

        # 100_000 = 100 KB
        chunks = chunk_list_by_bytes(shaped_orgs, 100_000)
        for idx, chunk_info in enumerate(chunks):
            chunk = chunk_info["chunk"]
            bounds = chunk_info["bounds"]
            LOGGER.info(
                "Sending chunk %d - %d to sync API", bounds["start"], bounds["end"]
            )
            send_csv_to_sync(json.dumps(chunk), bounds)

    except Exception as e:
        LOGGER.error(
            "Error sending organizations to DMZ sync endpoint:\n%s",
            traceback.format_exc(),
        )
        LOGGER.exception("Error sending organizations to DMZ sync endpoint: %s", e)
        raise SyncError(SCAN_NAME, str(e), "Error sending organizations to dmz") from e


def fetch_orgs_and_relations(db_name="mini_data_lake"):
    """Fetch organizations along with related sectors, CIDRs (via CidrOrgs), and child organizations.

    Returns:
        list: A list of dictionaries representing organizations and their relations.
    """
    sectors_prefetch = Prefetch("sectors")
    cidr_orgs_prefetch = Prefetch(
        "cidrorgs",  # Default reverse name for ForeignKey in Django
        queryset=CidrOrgs.objects.using(db_name).select_related("cidr"),
    )
    children_prefetch = Prefetch(
        "children"
    )  # Reverse ForeignKey for children organizations

    # Annotate organizations to identify if their id exists in another record's parent_id
    organizations = (
        Organization.objects.annotate(
            is_p=Exists(Organization.objects.filter(parent_id=OuterRef("id")))
        )
        .using(db_name)
        .select_related(
            "location",  # ForeignKey
            "parent",  # Self-referential ForeignKey for parent organization
            "org_type",  # ForeignKey for organization type
        )
        .prefetch_related(
            sectors_prefetch,  # ManyToManyField for sectors
            cidr_orgs_prefetch,  # Fetch cidr_orgs and their related cidrs
            children_prefetch,  # Reverse ForeignKey for children organizations
        )
        .order_by(
            "-is_p"
        )  # Order by `is_parent` descending, so parent organizations come first
    )

    # Iterate through results and shape the response
    shaped_orgs = []
    for org in organizations:
        shaped_orgs.append(organization_to_dict(org))
    return shaped_orgs


def send_csv_to_sync(csv_data, bounds):
    """Send CSV data to /sync API."""
    body = {"data": csv_data}
    try:
        checksum = create_checksum(csv_data)
    except Exception as e:
        LOGGER.error("Error creating checksum: %s", e)
        return

    headers = {
        "x-checksum": checksum,
        "x-cursor": f"{bounds['start']}-{bounds['end']}",
        "Content-Type": "application/json",
        "Authorization": os.getenv("DMZ_API_KEY", ""),
    }
    try:
        response = requests.post(
            os.getenv("DMZ_SYNC_ENDPOINT") + "/sync",
            json=body,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        LOGGER.info("Successfully sent chunk to sync API")
    except requests.exceptions.HTTPError as http_err:
        try:
            error_data = response.json()
            error_detail = error_data.get("detail", error_data)
            LOGGER.error(http_err)
        except ValueError:
            error_detail = response.text
        LOGGER.error(
            "HTTPError sending chunk to sync API:\nStatus Code: %s\nDetail: %s\nHeaders: %s",
            response.status_code,
            error_detail,
            response.headers,
        )
    except Exception as e:
        LOGGER.error("Unexpected error sending chunk: %s", str(e))
        raise SyncError(
            SCAN_NAME,
            str(e),
        ) from e


def organization_to_dict(org):
    """Convert an Organization instance and its relations to a nested dictionary.

    Args:
        org (Organization): The organization instance to convert.

    Returns:
        dict: A dictionary representation of the organization and its related data.
    """
    return {
        "id": str(org.id),
        "name": org.name,
        "acronym": org.acronym,
        "retired": org.retired,
        "created_at": org.created_at.isoformat(),
        "updated_at": org.updated_at.isoformat(),
        "type": org.type,
        "state": org.state,
        "state_name": org.state_name,
        "county": org.county,
        "county_fips": org.county_fips,
        "state_fips": org.state_fips,
        "country": org.country,
        "country_name": org.country_name,
        "region_id": org.region_id,
        "stakeholder": org.stakeholder,
        "enrolled_in_vs_timestamp": (
            org.enrolled_in_vs_timestamp.isoformat()
            if org.enrolled_in_vs_timestamp
            else None
        ),
        "period_start_vs_timestamp": (
            org.period_start_vs_timestamp.isoformat()
            if org.period_start_vs_timestamp
            else None
        ),
        "report_types": org.report_types,
        "scan_types": org.scan_types,
        "location": {
            "name": org.location.name,
            "country": org.location.country,
            "county": org.location.county,
            "country_abrv": org.location.country_abrv,
            "county_fips": org.location.county_fips,
            "gnis_id": org.location.gnis_id,
            "state_abrv": org.location.state_abrv,
            "state_fips": org.location.state_fips,
            "state": org.location.state,
        }
        if org.location
        else None,
        "parent": {
            "id": str(org.parent.id) if org.parent else None,
            "name": org.parent.name if org.parent else None,
            "acronym": org.parent.acronym if org.parent else None,
        }
        if org.parent
        else None,
        "children": [
            {"id": str(child.id), "name": child.name} for child in org.children.all()
        ],
        "sectors": [
            {"id": str(sector.id), "name": sector.name, "acronym": sector.acronym}
            for sector in org.sectors.all()
        ],
        "cidrs": [
            {
                "network": str(cidr_org.cidr.network),
                "start_ip": str(cidr_org.cidr.start_ip),
                "end_ip": str(cidr_org.cidr.end_ip),
                "live_ips": cidr_org.cidr.live_ips or [],
            }
            for cidr_org in org.cidrorgs.all()
        ],
    }
