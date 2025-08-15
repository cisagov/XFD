"""Utility functions for vulnerability scanning synchronization.

This module provides functions to save and fetch vulnerability scan data,
including organizations, hosts, IPs, CVEs, tickets, and port scans. It supports
data synchronization by interfacing with the data lake and database models.
"""

# Standard Python Libraries
import datetime
import json
import logging
import os
import time
from typing import Dict
from uuid import uuid4

# Third-Party Libraries
from dateutil import parser  # type: ignore
from django.db import connections, models, transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.db.utils import IntegrityError
from django.utils import timezone
from xfd_mini_dl.models import (
    Cidr,
    CidrOrgs,
    Cve,
    Host,
    Ip,
    Location,
    NMIServiceGroup,
    Organization,
    PortScan,
    RiskyServiceGroup,
    Ticket,
    TicketEvent,
    VulnScan,
)


def safe_parse_date(value):
    """Safely parse a date string into a datetime object."""
    try:
        if value:
            return parser.parse(value)
    except (parser.ParserError, TypeError, ValueError):
        return None  # or you can log it / raise a custom error
    return None


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


def save_port_scan_to_datalake(port_scan_obj):
    """
    Save a PortScan record to the datalake, performing an upsert if necessary.

    Args:
        port_scan_obj (dict): A dictionary containing PortScan record data.

    Returns:
        str or None: The ID of the inserted/updated record.
    """
    # print(
    #     f"Starting to save port scan {port_scan_obj.get('ipString')} {port_scan_obj.get('port')} to datalake"
    # )

    id = port_scan_obj.get("id")
    del port_scan_obj["id"]
    try:
        with transaction.atomic(using="mini_data_lake"):
            # Insert but ignore if the record already exists

            obj, created = PortScan.objects.update_or_create(
                id=id, defaults=port_scan_obj
            )
    except Exception as e:
        print("Error saving PortScan to Datalake", e)
        return None


def save_ticket_event_to_datalake(ticket_event_obj, ticket_id, details):
    """Save ticket events to Datalake."""
    id = ticket_event_obj.get("reference")
    if isinstance(id, str):
        id = id.replace("ObjectId('", "").replace("')", "")

    is_port_scan = False
    is_vuln_scan = False
    port_scan_record = None
    vuln_scan_record = None

    try:
        port_scan_record = PortScan.objects.get(id=id)
        is_port_scan = True
    except PortScan.DoesNotExist:
        pass
    try:
        vuln_scan_record = VulnScan.objects.get(id=id)
        is_vuln_scan = True
    except VulnScan.DoesNotExist:
        pass

    ticket_service = details.get("service")

    try:
        if ticket_service:
            ticket_record = Ticket.objects.get(id=ticket_id)
            nmi_service_group_record = NMIServiceGroup.objects.filter(
                service_name=ticket_service
            ).first()
            risky_service_group = RiskyServiceGroup.objects.filter(
                service_name=ticket_service
            ).first()
            if nmi_service_group_record:
                # Set NMI Service Group -> Not a relation, just text mapping field
                ticket_record.nmi_service_group = nmi_service_group_record.group
                ticket_record.save()
                if is_port_scan:
                    port_scan_record.nmi_service_group = nmi_service_group_record.group
                    port_scan_record.save()
                if is_vuln_scan:
                    vuln_scan_record.nmi_service_group = nmi_service_group_record.group
                    vuln_scan_record.save()
            if risky_service_group:
                # Set Risky Service Group -> Not a relation, just text mapping field
                ticket_record.risky_service_group = risky_service_group.group
                ticket_record.save()
                if is_port_scan:
                    port_scan_record.risky_service_group = risky_service_group.group
                    port_scan_record.save()
                if is_vuln_scan:
                    vuln_scan_record.risky_service_group = risky_service_group.group
                    vuln_scan_record.save()
    except Exception as e:
        LOGGER.info("Error setting NMIServiceGroup or RiskyServiceGroup", e)

    shaped = {
        "reference": id,
        "port_scan_id": id if is_port_scan else None,
        "vuln_scan_id": id if is_vuln_scan else None,
        "action": ticket_event_obj.get("action"),
        "reason": ticket_event_obj.get("reason"),
        "event_timestamp": safe_parse_date(ticket_event_obj.get("time")),
        "ticket_id": ticket_id,
    }
    try:
        ticket_event_record = TicketEvent.objects.create(**shaped)
        return ticket_event_record
    except IntegrityError:
        return None


def get_latest_os_type(ip_str):
    """Extract OS type for a given ip."""
    port_scan = (
        PortScan.objects.filter(ip_string=ip_str, service_os_type__isnull=False)
        .order_by("-time_scanned")
        .first()
    )
    return port_scan.service_os_type if port_scan else None


def save_ticket_to_datalake(ticket_obj, events, details):
    """
    Save a Ticket record to the datalake, performing an upsert if necessary.

    Args:
        ticket_obj (dict): A dictionary containing Ticket record data.

    Returns:
        str or None: The ID of the inserted/updated record.
    """
    # print("Starting to save Ticket to datalake")
    obj = None
    id = ticket_obj.get("id")
    del ticket_obj["id"]

    try:
        with transaction.atomic(using="mini_data_lake"):
            # Insert but ignore if the record already exists

            obj, created = Ticket.objects.update_or_create(id=id, defaults=ticket_obj)
    except Exception as e:
        print("Error saving Ticket to Datalake", e)

    try:
        for event in events:
            save_ticket_event_to_datalake(event, obj.id, details)
    except Exception as e:
        print("Error saving TicketEvent to Datalake", e)
        LOGGER.error("Error saving TicketEvent to Datalake, %s", e)
        return None
    return None


def save_host(host_data: Dict) -> str:
    """Save a Host record to the data lake.

    Args:
        host_data (dict): A dictionary containing Host record data.

    Returns:
        str: The ID of the inserted/updated record.
    """
    id = host_data.get("id")
    del host_data["id"]

    with transaction.atomic(using="mini_data_lake"):
        host, created = Host.objects.update_or_create(id=id, defaults=host_data)

    return str(host.id)


def truncate_charfields(model_cls, data_dict):
    """Trim or stringify charfields in the given data dict to their model-defined max_length."""
    for field in model_cls._meta.fields:
        if isinstance(field, models.CharField):
            val = data_dict.get(field.name)
            if val is None:
                continue
            if not isinstance(val, str):
                val = str(val)
            if field.max_length and len(val) > field.max_length:
                LOGGER.warning(
                    "Truncating field %s: %d → %d",
                    field.name,
                    len(val),
                    field.max_length,
                )
                val = val[: field.max_length]
            data_dict[field.name] = val


def save_vuln_scan(vuln_scan: Dict) -> str:
    """Save a Vulnerability Scan record to the data lake.

    Args:
        vuln_scan (dict): A dictionary containing vulnerability scan data.

    Returns:
        str: The ID of the inserted/updated record.
    """
    id = vuln_scan.get("id")
    del vuln_scan["id"]
    truncate_charfields(VulnScan, vuln_scan)
    if isinstance(id, str):
        id = id.replace("ObjectId('", "").replace("')", "")

    vuln_scan_obj, created = VulnScan.objects.update_or_create(
        id=id, defaults=vuln_scan
    )

    return str(vuln_scan_obj.id)


def save_cve_to_datalake(cve_obj):
    """
    Save a CVE record to the datalake, performing an upsert if necessary.

    Args:
        cve_obj (dict): A dictionary containing CVE record data.

    Returns:
        str or None: The ID of the inserted/updated record.
    """
    cve_name = cve_obj.get("name")

    # Determine fields to update, excluding 'name'
    cve_updated_values = [
        key
        for key in cve_obj.keys()
        if key not in ["name"] and cve_obj[key] is not None
    ]

    try:
        with transaction.atomic(using="mini_data_lake"):
            if cve_updated_values:
                # Upsert: Insert or update if a conflict occurs
                cve_record, created = Cve.objects.update_or_create(
                    name=cve_name,
                    defaults={key: cve_obj[key] for key in cve_updated_values}
                    | {"id": str(1)},
                )
                print("Updated CVE" if not created else "Created CVE")
                return cve_record
            else:
                # Insert but ignore if the record already exists
                obj, created = Cve.objects.get_or_create(
                    name=cve_name, defaults=cve_obj | {"id": str(uuid4())}
                )
                return obj
    except Exception as e:
        print("Error saving CVE to Datalake", e)
        return None


def save_ip_to_datalake(ip_obj):
    """
    Save an IP record to the datalake, performing an upsert if necessary.

    Args:
        ip_obj (dict): A dictionary containing IP record data.

    Returns:
        str or None: The ID of the inserted/updated record.
    """
    ip_address = ip_obj.get("ip")
    organization = ip_obj.get("organization")

    # Determine fields to update
    ip_updated_values = [
        key
        for key in ip_obj.keys()
        if key not in ["ip", "organization"] and ip_obj[key] is not None
    ]
    try:
        org_record = Organization.objects.get(id=str(organization["id"]))
        with transaction.atomic(using="mini_data_lake"):
            if ip_updated_values:
                # Upsert: Insert or update if a conflict occurs
                ip_record, created = Ip.objects.update_or_create(
                    ip=ip_address,
                    organization=org_record or None,
                    defaults={key: ip_obj[key] for key in ip_updated_values},
                )
                return ip_record
            else:
                # Insert but ignore if the record already exists
                obj, created = Ip.objects.get_or_create(
                    ip=ip_address,
                    organization=org_record or None,
                    defaults={
                        "ip": ip_address,
                        "organization": org_record,
                        "ip_hash": ip_obj["ip_hash"],
                    },
                )
                print("Created ip")
                return obj
    except Exception as e:
        print("Error saving IP to Datalake", e)
    except IntegrityError:
        pass


# Helper and utility functions
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
        "enrolled_in_vs_timestamp": org.enrolled_in_vs_timestamp.isoformat(),
        "period_start_vs_timestamp": org.period_start_vs_timestamp.isoformat(),
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
    # print("Saving Organization")
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
            print("Error creating location", e)

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
        print("Error occurred creating org", e)

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
        print("IntegrityError:", e)
    except Exception as e:
        print(type(e))
        print("Error occurred while creating or updating CIDR:", e)


# Used for loading test data from file for vuln_scans, port_scans, hosts, tickets
def load_test_data(data_set: str) -> list:
    """Load test data from local files for scanning simulations.

    Args:
        data_set (str): The type of data set to load (e.g., "requests", "vuln_scan").

    Returns:
        list: The parsed JSON data from the file.

    Raises:
        ValueError: If an unknown data_set is provided.
        FileNotFoundError: If the specified file does not exist.
    """
    file_paths = {
        "requests": "~/Downloads/requests_full_redshift.json",
        "vuln_scan": "~/Downloads/vuln_scan_sample.json",
        "port_scans": "~/Downloads/port_scans_sample.json",
        "hosts": "~/Downloads/hosts_sample.json",
        "tickets": "~/Downloads/tickets_sample_new.json",
    }

    file_path = file_paths.get(data_set)

    if file_path is None:
        raise ValueError(f"Unknown data set: {data_set}")

    expanded_path = os.path.expanduser(file_path)

    if not os.path.exists(expanded_path):
        raise FileNotFoundError(f"Test data file not found: {expanded_path}")

    with open(expanded_path, encoding="utf-8") as file:
        return json.load(file)


def enforce_latest_flag_port_scan():
    """
    Enforce the `latest` boolean flag on the PortScan table per org.

    Marks only the most recent scan for each (organization_id, ip_string, port)
    as `latest=True`. All others are set to `False`.
    """
    start = time.time()
    db = "mini_data_lake"
    org_ids = list(Organization.objects.using(db).values_list("id", flat=True))

    for org_id in org_ids:
        try:
            with connections[db].cursor() as cursor, transaction.atomic(using=db):
                # Step 1: Mark all as latest=False
                cursor.execute(
                    """
                    UPDATE port_scan
                    SET latest = FALSE
                    WHERE organization_id = %s;
                """,
                    [org_id],
                )

                # Step 2: Mark latest=True only for the most recent per IP/port
                cursor.execute(
                    """
                    WITH latest_scans AS (
                        SELECT DISTINCT ON (ip_string, port)
                            id
                        FROM port_scan
                        WHERE organization_id = %s
                          AND time_scanned IS NOT NULL
                          AND time_scanned > NOW() - INTERVAL '90 days'
                        ORDER BY ip_string, port, time_scanned DESC
                    )
                    UPDATE port_scan
                    SET latest = TRUE
                    WHERE id IN (SELECT id FROM latest_scans);
                """,
                    [org_id],
                )

        except Exception as e:
            print("Error enforcing latest flag for org {}: {}".format(org_id, e))

    duration = time.time() - start
    print("Completed enforce_latest_flag in {:.2f}s".format(duration))


def map_severity(severity):
    """Map a severity score to a severity level."""
    if severity == 0 or severity is None:
        return "None"
    if severity < 4:
        return "Low"
    if severity < 7:
        return "Medium"
    if severity < 9:
        return "High"
    return "Critical"


def fill_cidr_live_ips():
    """Update live_ips field for all current CIDRs based on recent open PortScans."""
    start_time = time.time()

    # Define the 90-day threshold
    time_threshold = timezone.now() - datetime.timedelta(days=90)

    # Get all Cidrs with at least one related CidrOrgs marked as current
    current_cidrs = Cidr.objects.filter(cidrorgs__current=True).distinct()

    for cidr in current_cidrs:
        if not cidr.network:
            continue

        scans = (
            PortScan.objects.filter(
                state="open",
                time_scanned__gte=time_threshold,
                ip__ip__net_contained=cidr.network,
            )
            .values_list("ip__ip", flat=True)
            .distinct()
        )

        # If live_ips is empty or not set, initialize it as an empty set
        current_live_ips = set(cidr.live_ips or [])

        # Add the new IPs from the scans to the existing set (no duplicates)
        current_live_ips.update(scans)

        # Convert all IP objects to strings for JSON serialization
        cidr.live_ips = [str(ip.ip) for ip in current_live_ips]
        cidr.save()

    duration = time.time() - start_time
    LOGGER.info("fill_cidr_live_ips completed in %.2f seconds", duration)


def fill_cidr_live_ips_bulk_update():
    """Fill live_ips field in the cidr table based on recent port scans."""
    start_time = time.time()

    with transaction.atomic(using="mini_data_lake"):
        with connections["mini_data_lake"].cursor() as cursor:
            cursor.execute(
                """
                WITH new_ips AS (
                    SELECT
                        cidr.id AS cidr_id,
                        array_agg(DISTINCT ip.ip) AS new_ip_list
                    FROM cidr
                    JOIN cidr_orgs ON cidr_orgs.cidr_id = cidr.id
                    JOIN port_scan ON port_scan.state = 'open'
                        AND port_scan.time_scanned >= NOW() - INTERVAL '90 days'
                    JOIN ip ON port_scan.ip_id = ip.id
                    WHERE cidr_orgs.current = TRUE
                      AND cidr.network IS NOT NULL
                      AND ip.ip << cidr.network
                    GROUP BY cidr.id
                ),
                merged_ips AS (
                    SELECT
                        cidr.id,
                        ARRAY(
                            SELECT DISTINCT ip_address::inet
                            FROM jsonb_array_elements_text(
                                COALESCE(cidr.live_ips, '[]'::jsonb) || to_jsonb(new_ips.new_ip_list)
                            ) AS ip_address
                        ) AS updated_ips
                    FROM cidr
                    JOIN new_ips ON cidr.id = new_ips.cidr_id
                )
                UPDATE cidr
                SET live_ips = to_jsonb(merged_ips.updated_ips)
                FROM merged_ips
                WHERE cidr.id = merged_ips.id;
                """
            )

    duration = time.time() - start_time
    LOGGER.info("fill_cidr_live_ips_bulk_update completed in %.2f seconds", duration)
