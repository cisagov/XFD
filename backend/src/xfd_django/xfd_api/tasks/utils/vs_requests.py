"""Vs Requests Helpers."""

# Standard Python Libraries
import datetime
from ipaddress import IPv4Network, IPv6Network
import json
import logging
import os
from uuid import uuid4

# Third-Party Libraries
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from xfd_api.helpers.regionStateMap import REGION_STATE_MAP
from xfd_api.tasks.utils.query_redshift import fetch_from_redshift
from xfd_api.utils.scan_utils.alerting import IngestionError
from xfd_mini_dl.models import Cidr, CidrOrgs, Location, Organization, Sector

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")


def fetch_orgs_from_redshift():
    """Fetch orgs from redshift."""
    request_list = fetch_from_redshift("SELECT * FROM vmtableau.requests;")
    LOGGER.info("Fetched %d requests from Redshift", len(request_list))
    org_id_dict = process_orgs(request_list)
    LOGGER.info("Completed saving organizations to the LZ MDL.")
    return org_id_dict


def fetch_org_id_dict_fast(db_name="mini_data_lake"):
    """Fast path for tests: map acronym -> id using MDL only."""
    rows = Organization.objects.using(db_name).values("id", "acronym")
    # Assumes acronym is unique; if not, last one wins.
    return {r["acronym"]: r["id"] for r in rows}


def process_orgs(request_list):
    """Process organization data, save to MDL and return org ID dict for linking."""
    LOGGER.info("Processing organizations...")
    org_id_dict = {}
    sector_child_dict = {}
    parent_child_dict = {}

    # Process the request data
    try:
        if request_list and isinstance(request_list, list):
            process_request(
                request_list, sector_child_dict, parent_child_dict, org_id_dict
            )

            # Link parent-child organizations
            link_parent_child_organizations(parent_child_dict, org_id_dict)

            # Assign organizations to sectors
            assign_organizations_to_sectors(sector_child_dict, org_id_dict)

        return org_id_dict
    except Exception as e:
        raise IngestionError(
            SCAN_NAME, str(e), "Failed processing organizations"
        ) from e


def process_request(request_list, sector_child_dict, parent_child_dict, org_id_dict):
    """Process requests and build dictionaries for linking later."""
    non_sector_list = {
        "CRITICAL_INFRASTRUCTURE",
        "FEDERAL",
        "ROOT",
        "SLTT",
        "CATEGORIES",
        "INTERNATIONAL",
        "THIRD_PARTY",
    }

    for request in request_list:
        request = parse_request_data(request)

        # Skip non-sector records
        if "type" not in request["agency"]:
            if request["_id"] in non_sector_list:
                continue

            process_sector(request, sector_child_dict)
            continue

        # Process parent-child relationships
        if request.get("children"):
            parent_child_dict[request["_id"]] = request["children"]

        # Process networks
        network_list = process_networks(request.get("networks", []))

        # Process location
        location_dict = process_location(request.get("agency", {}).get("location"))

        # Process organization
        process_organization(request, network_list, location_dict, org_id_dict)


def link_parent_child_organizations(
    parent_child_dict, org_id_dict, db_name="mini_data_lake"
):
    """Link child organizations to their respective parent organizations."""
    for parent_acronym, child_acronyms in parent_child_dict.items():
        parent_id = org_id_dict.get(parent_acronym)
        if not parent_id:
            continue

        try:
            parent_org = Organization.objects.using(db_name).get(id=parent_id)
        except Organization.DoesNotExist:
            continue

        # Collect child organization IDs
        children_ids = [
            org_id_dict.get(acronym)
            for acronym in child_acronyms
            if acronym in org_id_dict
        ]

        # Update parent field for child organizations
        if children_ids:
            Organization.objects.using(db_name).filter(id__in=children_ids).update(
                parent=parent_org.id
            )


def assign_organizations_to_sectors(
    sector_child_dict, org_id_dict, db_name="mini_data_lake"
):
    """Assign organizations to sectors based on sector-child relationships."""
    try:
        for sector_id, child_acronyms in sector_child_dict.items():
            try:
                sector = Sector.objects.using(db_name).get(id=sector_id)
            except Sector.DoesNotExist:
                continue

            organization_ids = [
                org_id_dict.get(acronym)
                for acronym in child_acronyms
                if acronym in org_id_dict
            ]

            if organization_ids:
                sector.organizations.add(
                    *Organization.objects.using(db_name).filter(id__in=organization_ids)
                )
    except Exception as e:
        LOGGER.error("Error assigning organization to sectors: %s", e)
        raise e


def parse_request_data(request):
    """Parse JSON fields in the request if they are strings."""
    json_fields = ["agency", "networks", "report_types", "scan_types", "children"]
    for field in json_fields:
        val = request.get(field)
        if isinstance(val, str):
            try:
                request[field] = json.loads(val)
            except Exception:
                request[field] = {}
        elif not isinstance(val, (dict, list)):  # corrupt or malformed
            request[field] = {} if field == "agency" else []
    return request


def process_sector(request, sector_child_dict):
    """Process sector data and update sector_child_dict."""
    if request.get("children"):
        sector_data = {
            "name": request["agency"]["name"],
            "acronym": request["_id"],
            "retired": bool(request["retired"]),
        }
        try:
            sector_obj, created = Sector.objects.update_or_create(
                acronym=sector_data["acronym"],
                defaults={
                    "name": sector_data["name"],
                    "retired": sector_data["retired"],
                },
            )
            sector_child_dict[sector_obj.id] = request["children"]
        except Exception as e:
            LOGGER.error("Error occurred creating sector: %s", e)


def process_networks(networks):
    """Process network CIDR entries and return a list of network objects."""
    network_list = []
    for cidr in networks:
        try:
            address = (
                IPv6Network(cidr, strict=False)
                if ":" in cidr
                else IPv4Network(cidr, strict=False)
            )
            network_list.append(
                {"network": cidr, "start_ip": address[0], "end_ip": address[-1]}
            )
        except Exception as e:
            LOGGER.error("Invalid CIDR Format: %s", e)
    return network_list


def process_location(org_location):
    """Create a dictionary representation of an organization's location."""
    if not org_location:
        return None

    return {
        "name": org_location.get("name"),
        "country_abrv": org_location.get("country", ""),
        "country": org_location.get("country_name"),
        "county": org_location.get("county"),
        "county_fips": org_location.get("county_fips"),
        "gnis_id": org_location.get("gnis_id"),
        "state_abrv": org_location.get("state"),
        "stateFips": org_location.get("state_fips"),
        "state": org_location.get("state_name"),
    }


def parse_int(value):
    """Safely parse integers, return None for blanks."""
    try:
        if value == "" or value is None:
            return None
        return int(value)
    except (ValueError, TypeError):
        return None


def process_organization(request, network_list, location_dict, org_id_dict):
    """Save organization data and update org_id_dict."""
    ip_blocks: list[str] = [net["network"] for net in network_list]

    org_data = {
        "name": request.get("agency", {}).get("name"),
        "acronym": request.get("_id"),
        "retired": bool(request.get("retired", False)),
        "type": request.get("agency", {}).get("type"),
        "state": request.get("agency", {}).get("location", {}).get("state"),
        "state_name": request.get("agency", {}).get("location", {}).get("state_name"),
        "county": request.get("agency", {}).get("location", {}).get("county"),
        "county_fips": parse_int(
            request.get("agency", {}).get("location", {}).get("county_fips")
        ),
        "state_fips": parse_int(
            request.get("agency", {}).get("location", {}).get("state_fips")
        ),
        "country": request.get("agency", {}).get("location", {}).get("country"),
        "country_name": request.get("agency", {})
        .get("location", {})
        .get("country_name"),
        "region_id": REGION_STATE_MAP.get(
            request.get("agency", {}).get("location", {}).get("state_name"), None
        ),
        "stakeholder": bool(request.get("stakeholder", False)),
        "enrolled_in_vs_timestamp": request.get("enrolled") or timezone.now(),
        "period_start_vs_timestamp": request.get("period_start"),
        "report_types": json.dumps(request.get("report_types", [])),
        "scan_types": json.dumps(request.get("scan_types", [])),
        "ip_blocks": ip_blocks,
        "is_passive": False,
    }
    try:
        org_record = save_organization_to_mdl(org_data, network_list, location_dict)
        org_id_dict[request["_id"]] = org_record.id
    except Exception as e:
        LOGGER.info("Error saving organization: %s - %s", e, request["_id"])
        raise IngestionError(
            SCAN_NAME, str(e), "Failed processing organizations"
        ) from e


def save_organization_to_mdl(
    org_dict, network_list, location, db_name="mini_data_lake"
) -> Organization:
    """Save or update an organization in the specified database.

    This function handles creating or updating an organization record,
    managing its location, and linking CIDRs to the organization.

    Args:
        org_dict (dict): A dictionary containing organization details,
            including name, acronym, type, and enrollment timestamps.
        network_list (list): A list of CIDR dictionaries representing
            the organization's associated networks.
        location (dict or None): A dictionary containing location details
            (e.g., GNIS ID, country, state, etc.), or None if no location is provided.
        db_name (str, optional): The name of the database to use.
            Defaults to "mini_data_lake".

    Returns:
        Organization: The created or updated organization instance.
    """
    LOGGER.debug("Saving Organization")
    location_obj = None
    if location:
        try:
            location_obj, created = Location.objects.using(db_name).update_or_create(
                gnis_id=str(location["gnis_id"]),  # Lookup field
                defaults={  # Fields to update or set if creating
                    "name": location.get("name", None),
                    "country_abrv": location.get("country_abrv", None),
                    "country": location.get("country", None),
                    "county": location.get("county", None),
                    "county_fips": location.get("county_fips", None),
                    "state_abrv": location.get("state_abrv", None),
                    "state": location.get("state", None),
                },
            )
        except Exception as e:
            LOGGER.error("Error creating location", e)

    org_obj = None
    try:
        organization_obj = Organization.objects.using(db_name).get(
            acronym=org_dict["acronym"]
        )
        organization_obj.name = org_dict["name"]
        organization_obj.retired = org_dict["retired"]
        organization_obj.type = org_dict["type"]
        organization_obj.stakeholder = org_dict["stakeholder"]
        organization_obj.enrolled_in_vs_timestamp = org_dict["enrolled_in_vs_timestamp"]
        organization_obj.period_start_vs_timestamp = org_dict[
            "period_start_vs_timestamp"
        ]
        organization_obj.report_types = org_dict["report_types"]
        organization_obj.scan_types = org_dict["scan_types"]
        organization_obj.location = location_obj
        organization_obj.region_id = org_dict["region_id"]
        organization_obj.state = org_dict["state"]
        organization_obj.state_name = org_dict["state_name"]
        organization_obj.county = org_dict["county"]
        organization_obj.county_fips = org_dict["county_fips"]
        organization_obj.state_fips = org_dict["state_fips"]
        organization_obj.country = org_dict["country"]
        organization_obj.country_name = org_dict["country_name"]
        organization_obj.ip_blocks = org_dict["ip_blocks"]
        organization_obj.save()
        org_obj = organization_obj
    except Organization.DoesNotExist:
        organization_obj = Organization.objects.using(db_name).create(
            id=str(uuid4()),
            name=org_dict["name"],
            acronym=org_dict["acronym"],
            retired=org_dict["retired"],
            type=org_dict["type"],
            region_id=org_dict["region_id"],
            state=org_dict["state"],
            state_name=org_dict["state_name"],
            county=org_dict["county"],
            county_fips=org_dict["county_fips"],
            state_fips=org_dict["state_fips"],
            country=org_dict["country"],
            country_name=org_dict["country_name"],
            stakeholder=org_dict["stakeholder"],
            enrolled_in_vs_timestamp=org_dict["enrolled_in_vs_timestamp"],
            period_start_vs_timestamp=org_dict["period_start_vs_timestamp"],
            report_types=org_dict["report_types"],
            scan_types=org_dict["scan_types"],
            ip_blocks=org_dict["ip_blocks"],
            location=location_obj,
            is_passive=False,
        )
        org_obj = organization_obj
    except IntegrityError:
        organization_obj = Organization.objects.using(db_name).get(
            acronym=org_dict["acronym"]
        )
        if organization_obj:
            org_obj = organization_obj
        pass
    except Exception as e:
        LOGGER.error("Error occurred creating org", e)

    if org_obj:
        # Create CIDRs and link them
        for cidr in network_list:
            save_cidr_to_mdl(cidr, org_obj, db_name)

    return org_obj


def save_cidr_to_mdl(cidr_dict: dict, org: Organization, db_name="mini_data_lake"):
    """
    Create or update a CIDR record in the specified database, linking it to the provided organization.

    Args:
        cidr_dict (dict): Dictionary containing CIDR details (network, start_ip, end_ip).
        org (Organization): Organization to associate with the CIDR.
        db_name (str): Name of the database to use. Defaults to "mini_data_lake".
    """
    try:
        with transaction.atomic(using=db_name):
            # Fetch or create the CIDR object
            cidr_obj = (
                Cidr.objects.using(db_name).filter(network=cidr_dict["network"]).first()
            )
            if cidr_obj:
                cidr_obj.start_ip = cidr_dict["start_ip"]
                cidr_obj.end_ip = cidr_dict["end_ip"]
                cidr_obj.retired = False
                cidr_obj.live_ips = cidr_dict.get("live_ips", [])
                cidr_obj.save(using=db_name)  # Save updates

            else:
                cidr_obj = Cidr.objects.using(db_name).create(
                    id=str(uuid4()),
                    network=cidr_dict["network"],
                    start_ip=cidr_dict["start_ip"],
                    end_ip=cidr_dict["end_ip"],
                    live_ips=cidr_dict.get("live_ips", []),
                    retired=False,
                )
            # cidr_obj.organizations.add(org, through_defaults={})
            cidr_obj.save(using=db_name)
            CidrOrgs.objects.using(db_name).update_or_create(
                organization=org,
                cidr=cidr_obj,
                defaults={
                    "last_seen": datetime.datetime.today().date(),
                    "current": True,
                },
            )
    except IntegrityError as e:
        LOGGER.error("IntegrityError: %s", e)
    except Exception as e:
        LOGGER.error("Error occurred while creating or updating CIDR: %s", e)
