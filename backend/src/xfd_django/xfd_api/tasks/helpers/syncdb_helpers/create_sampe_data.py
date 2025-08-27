"""Create sample data for local development."""

# Standard Python Libraries
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import ipaddress
import json
import logging
import os
import random
import secrets
import string
import sys
from typing import Optional
import uuid

# Third-Party Libraries
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from faker import Faker
from xfd_api.helpers.regionStateMap import REGION_STATE_MAP
from xfd_api.models import Domain, Service, Vulnerability
from xfd_api.tasks.refresh_material_views import handler as refresh_materialized_views
from xfd_api.tasks.refresh_vs_summaries import handler as refresh_vs_summaries
from xfd_api.tasks.utils.mdl_insert_utils import fill_cidr_live_ips_bulk_update
from xfd_mini_dl.models import (
    ApiKey,
    Cidr,
    CidrOrgs,
    Cve,
    Host,
    Ip,
    Location,
    Organization,
    PortScan,
    Ticket,
    TicketEvent,
    User,
    UserType,
    VulnScan,
)

fake = Faker()
LOGGER = logging.getLogger(__name__)

# Constants for sample data generation
SAMPLE_TAG_NAME = "Sample Data"
NUM_SAMPLE_ORGS = 10
NUM_SAMPLE_DOMAINS = 10
PROB_SAMPLE_SERVICES = 0.5
PROB_SAMPLE_VULNERABILITIES = 0.5
SAMPLE_STATES = ["Virginia", "California", "Colorado"]
SAMPLE_REGION_IDS = ["1", "2", "3"]
FAKE_ORG_COUNT = 20
FAKE_VULN_SCAN_COUNT = 200
FAKE_PORT_SCAN_COUNT = 200
FAKE_HOST_COUNT = 2
FAKE_TICKET_COUNT = 100
# Load sample data files
SAMPLE_DATA_DIR = os.path.join(settings.BASE_DIR, "xfd_api", "tasks", "sample_data")
services = json.load(open(os.path.join(SAMPLE_DATA_DIR, "services.json")))
cpes = json.load(open(os.path.join(SAMPLE_DATA_DIR, "cpes.json")))
vulnerabilities = json.load(open(os.path.join(SAMPLE_DATA_DIR, "vulnerabilities.json")))
nouns = json.load(open(os.path.join(SAMPLE_DATA_DIR, "nouns.json")))
adjectives = json.load(open(os.path.join(SAMPLE_DATA_DIR, "adjectives.json")))
CVSS_SEVERITIES = ["Low", "Medium", "High", "Critical"]
CVSS_VECTORS = {
    "v2": "AV:N/AC:L/Au:N/C:P/I:P/A:P",
    "v3": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "v4": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
}


def create_ip_within_org_cidr(org: Organization) -> Optional[Ip]:
    """
    Create and return an Ip record with an address that falls within one of the organization's CIDRs.

    Args:
        org (Organization): The organization for which to create the IP.

    Returns:
        Ip: The created or retrieved Ip object, or None if no valid CIDRs found.
    """
    cidrs = Cidr.objects.filter(organizations=org, network__isnull=False)

    if not cidrs.exists():
        return None, None

    # Try generating a valid IP from a randomly selected CIDR block
    for _ in range(len(cidrs)):
        cidr = random.choice(cidrs)
        try:
            network = ipaddress.ip_network(cidr.network)

            # Get usable hosts (skipping network/broadcast for IPv4)
            hosts = list(network.hosts())
            if not hosts:
                continue  # Try another CIDR

            ip_string = str(random.choice(hosts))
            ip_hash = hashlib.sha256(ip_string.encode()).hexdigest()

            ip_record, _ = Ip.objects.get_or_create(
                ip=ip_string, organization=org, defaults={"ip_hash": ip_hash}
            )
            return ip_record, ip_string
        except ValueError:
            continue

    LOGGER.warning("⚠️ Failed to generate IP from any CIDR for org: %s", org)
    return None


def build_fake_cve() -> Cve:
    """Build a fake CVE object."""
    year = random.randint(2000, 2024)
    if year < 2014:
        cve_id = f"CVE-{year}-{random.randint(1000, 9999)}"
    else:
        cve_id = f"CVE-{year}-{random.randint(1000, 99999)}"
    published_at = fake.date_time_between(
        start_date=f"-{2024 - year + 1}y", end_date=f"-{2024 - year}y"
    )
    modified_at = published_at + timedelta(days=random.randint(10, 365))
    try:
        return Cve.objects.create(
            name=cve_id,
            published_at=timezone.make_aware(published_at),
            modified_at=timezone.make_aware(modified_at),
            status=random.choice(["Analyzed", "Under Review", "Rejected", "Reserved"]),
            description=fake.paragraph(nb_sentences=3),
            cvss_v2_source="NVD",
            cvss_v2_type=random.choice(["Primary", "Secondary"]),
            cvss_v2_version="2.0",
            cvss_v2_vector_string=CVSS_VECTORS["v2"],
            cvss_v2_base_score=str(round(random.uniform(3.0, 10.0), 1)),
            cvss_v2_base_severity=random.choice(CVSS_SEVERITIES),
            cvss_v2_exploitability_score=str(round(random.uniform(1.0, 10.0), 1)),
            cvss_v2_impact_score=str(round(random.uniform(1.0, 10.0), 1)),
            cvss_v3_source="MITRE",
            cvss_v3_type=random.choice(["Primary", "Secondary"]),
            cvss_v3_version="3.1",
            cvss_v3_vector_string=CVSS_VECTORS["v3"],
            cvss_v3_base_score=str(round(random.uniform(3.0, 10.0), 1)),
            cvss_v3_base_severity=random.choice(CVSS_SEVERITIES),
            cvss_v3_exploitability_score=str(round(random.uniform(1.0, 10.0), 1)),
            cvss_v3_impact_score=str(round(random.uniform(1.0, 10.0), 1)),
            cvss_v4_source="Cisco",
            cvss_v4_type="Primary",
            cvss_v4_version="4.0",
            cvss_v4_vector_string=CVSS_VECTORS["v4"],
            cvss_v4_base_score=str(round(random.uniform(3.0, 10.0), 1)),
            cvss_v4_base_severity=random.choice(CVSS_SEVERITIES),
            cvss_v4_exploitability_score=str(round(random.uniform(1.0, 10.0), 1)),
            cvss_v4_impact_score=str(round(random.uniform(1.0, 10.0), 1)),
            weaknesses=[
                f"CWE-{random.randint(20, 999)}" for _ in range(random.randint(1, 3))
            ],
            reference_urls=[fake.url() for _ in range(random.randint(1, 3))],
            cpe_list=[
                f"cpe:/a:vendor:product:{random.randint(1, 5)}"
                for _ in range(random.randint(1, 2))
            ],
        )
    except IntegrityError:
        return Cve.objects.get(name=cve_id)


def build_fake_vulnscan(org):
    """Build a fake VulnScan object."""
    ip_record, ip_string = create_ip_within_org_cidr(org)
    cve = Cve.objects.order_by("?").first()

    return VulnScan(
        id=str(uuid.uuid4()),
        organization=org,
        ip=ip_record,
        ip_string=ip_string,
        cve=cve,
        cve_string=cve.name if cve else None,
        cert_id=fake.bothify("CERT-####-###"),
        cpe="cpe:/a:microsoft:iis",
        cvss_base_score=str(round(random.uniform(3.0, 9.0), 1)),
        cvss_temporal_score=str(round(random.uniform(3.0, 9.0), 1)),
        cvss_temporal_vector="AV:N/AC:L/Au:N/C:P/I:N/A:N",
        cvss_vector="CVSS2#AV:N/AC:L/Au:N/C:P/I:N/A:N",
        description=fake.sentence(nb_words=12),
        exploit_available=random.choice(["true", "false"]),
        exploitability_ease=random.choice(["Low", "Medium", "High"]),
        latest=random.choice([True, False]),
        owner=org.acronym,
        osvdb_id=str(random.randint(10000, 99999)),
        patch_publication_timestamp=timezone.make_aware(
            fake.date_time_between(start_date="-5y", end_date="now")
        ),
        cisa_known_exploited=timezone.make_aware(
            fake.date_time_between(start_date="-2y", end_date="now")
        ),
        port=random.choice([22, 80, 443, 3389]),
        port_protocol=random.choice(["tcp", "udp"]),
        risk_factor=random.choice(["Low", "Medium", "High", "Critical"]),
        script_version=f"{random.randint(1, 5)}.{random.randint(0, 9)}",
        see_also="https://www.example.com/vuln-info",
        service=random.choice(["http", "ssh", "rdp"]),
        severity=random.randint(1, 5),
        solution=fake.sentence(nb_words=10),
        source="nessus",
        synopsis="The remote web server has an information disclosure vulnerability.",
        vuln_detection_timestamp=timezone.now()
        - timedelta(days=random.randint(0, 365)),
        vuln_publication_timestamp=timezone.now()
        - timedelta(days=random.randint(365, 1000)),
        xref=f"XREF-{random.randint(1000, 9999)}",
        cwe=f"CWE-{random.randint(20, 999)}",
        bid=str(random.randint(10000, 99999)),
        exploited_by_malware=random.choice([True, False]),
        thorough_tests=random.choice([True, False]),
        cvss_score_rationale="Vendor supplied CVSS score rationale.",
        cvss_score_source="NVD",
        cvss3_base_score=round(random.uniform(3.0, 10.0), 1),
        cvss3_vector=CVSS_VECTORS["v3"],
        cvss3_temporal_vector=CVSS_VECTORS["v3"],
        cvss3_temporal_score=round(random.uniform(2.0, 8.0), 1),
        asset_inventory=random.choice([True, False]),
        plugin_id=str(random.randint(50000, 60000)),
        plugin_modification_date=timezone.make_aware(
            fake.date_time_between(start_date="-2y", end_date="now")
        ),
        plugin_publication_date=timezone.make_aware(
            fake.date_time_between(start_date="-10y", end_date="-2y")
        ),
        plugin_name="IIS Detailed Error Information Disclosure",
        plugin_type="remote",
        plugin_family="Web Servers",
        f_name="iis_detailed_error.nasl",
        cisco_bug_id=f"CSC-{fake.lexify(text='?????-###')}",
        cisco_sa=fake.uri(),
        plugin_output="Nessus was able to obtain a detailed error message...",
        other_findings={"notes": "Simulated record."},
        nmi_service_group="NMI",
        risky_service_group=random.choice(
            ["Potentially Risky Service", "Known Exploited Service"]
        ),
    )


def build_fake_port_scan(org):
    """Build a fake PortScan object."""
    ip_record, ip_string = create_ip_within_org_cidr(org)

    service_info = {
        "conf": str(random.randint(1, 10)),
        "method": random.choice(["probed", "banner", "snmp", "ssl-cert"]),
        "name": random.choice(["http", "ssh", "tcpwrapped", "ftp", "mysql"]),
    }
    risky_service_group = random.choice(
        [
            "rdp",
            "telnet",
            "smb",
            "ldap",
            "netbios",
            "ftp",
            "rpc",
            "sql",
            "irc",
            "kerberos",
            None,
            None,
            None,
        ]
    )
    nmi_group = (
        risky_service_group if risky_service_group in ["smb", "telnet", "rdp"] else None
    )

    return PortScan(
        id=str(uuid.uuid4()),
        ip=ip_record,
        ip_string=ip_string,
        organization=org,
        latest=random.choice([True, True, True, True, False]),
        port=random.choice([22, 80, 443, 8080, 33542]),
        protocol=random.choice(["tcp", "udp"]),
        reason=random.choice(["syn-ack", "response", "reset", "none"]),
        service=service_info,
        service_name=service_info["name"],
        service_confidence=int(service_info["conf"]),
        service_method=service_info["method"],
        source="nmap",
        state=random.choice(["open", "open", "open", "open", "silent"]),
        time_scanned=timezone.make_aware(
            fake.date_time_between(start_date="-1y", end_date="now")
        ),
        nmi_service_group=nmi_group,
        risky_service_group=risky_service_group,
    )


def build_fake_host(org):
    """Build a fake Host object."""
    ip_record, ip_string = create_ip_within_org_cidr(org)

    base_time = timezone.now() - timedelta(days=random.randint(10, 100))

    return Host(
        id=str(uuid.uuid4()),
        ip_string=ip_string,
        ip=ip_record,
        organization=org,
        updated_timestamp=base_time + timedelta(days=5),
        latest_netscan_1_timestamp=base_time,
        latest_netscan_2_timestamp=base_time + timedelta(days=1),
        latest_vulnscan_timestamp=base_time + timedelta(days=2),
        latest_portscan_timestamp=base_time + timedelta(days=3),
        latest_scan_completion_timestamp=base_time + timedelta(days=4),
        location_latitude=round(Decimal(fake.latitude()), 6),
        location_longitude=round(Decimal(fake.longitude()), 6),
        priority=random.choice([None, -16, -8, 0, 1]),
        next_scan_timestamp=base_time + timedelta(days=random.randint(1, 14)),
        rand=Decimal(str(round(random.uniform(0, 1), 6))),
        curr_stage=random.choice(["DISCOVERY", "PORT_SCAN", "VULN_SCAN", "DONE", None]),
        host_live=random.choice([True, False, None]),
        host_live_reason=random.choice(["ping", "syn-ack", "timeout", "reset", None]),
        status=random.choice(["WAITING", "READY", "RUNNING", "DONE", None]),
    )


def build_fake_ticket(org):
    """Build a fake Ticket object."""
    ip_record, ip_string = create_ip_within_org_cidr(org)
    cve = Cve.objects.order_by("?").first()
    port = random.choice([21, 22, 80, 443])
    severity_ranges = {
        "1.0": (0.1, 3.9),  # Low
        "2.0": (4.0, 6.9),  # Medium
        "3.0": (7.0, 8.9),  # High
        "4.0": (9.0, 10.0),  # Critical
    }
    severity = random.choice(list(severity_ranges.keys()))
    cvss_base_score = round(random.uniform(*severity_ranges[severity]), 1)
    protocol = random.choice(["tcp", "udp"])
    opened_time = timezone.now() - timedelta(days=random.randint(0, 30))
    is_kev = random.choice([True, True, False])
    # 80% chance of ticket being open (closed_timestamp = None)
    if random.random() < 0.8:
        closed_time = None
    else:
        closed_time = opened_time + timedelta(days=random.randint(30, 600))
    return Ticket(
        id=str(uuid.uuid4()),
        ip=ip_record,
        ip_string=ip_string
        if ip_string
        else random.choice(
            [
                "192.0.2.1",
                "198.51.100.2",
                "203.0.113.3",
                "127.0.0.1",
                "10.0.0.1",
                "172.16.0.1",
                "192.168.1.1",
            ]
        ),
        organization=org,
        cve=cve,
        cve_string=cve.name if cve else "CVE-2021-0001",
        cvss_base_score=cvss_base_score,
        cvss_version="3.1",
        vuln_name=cve.name
        + " "
        + random.choice(
            [
                "Super Alarming Vuln",
                "Super Hazardous Vuln",
                "Super Risky Vuln",
                "Super Menacing Vuln",
                "Super unsupported Vuln",
            ]
        )
        if cve
        else "CVE-2021-0001",
        cvss_score_source="nvd",
        cvss_severity=Decimal(severity),
        vpr_score=Decimal("6.9"),
        false_positive=random.choices([True, False], weights=[1, 19])[0],
        updated_timestamp=timezone.now(),
        location_latitude=Decimal(str(round(random.uniform(-90, 90), 6))),
        location_longitude=Decimal(str(round(random.uniform(-180, 180), 6))),
        found_in_latest_host_scan=True,
        vuln_port=port,
        port_protocol=protocol,
        snapshots_bool=False,
        vuln_source="nessus",
        operating_system=random.choice(
            [
                None,
                None,
                None,
                None,
                None,
                None,
                "Windows 10",
                "Linux (Ubuntu 22.04)",
                "macOS (macOS Ventura)",
                "FreeBSD",
                "Cisco IOS",
            ]
        ),
        vuln_source_id=random.choice([10081, 12345, 34567, 89012]),
        closed_timestamp=closed_time,
        opened_timestamp=opened_time,
        is_kev=is_kev,
        is_kev_ransomware=random.choices([True, False], weights=[1, 4])[0]
        if is_kev
        else False,
        is_risky=random.choice([True, False]),
        is_open=not closed_time,
        service_name="ftp",
        nmi_service_group="NMI",
        risky_service_group=random.choice(
            ["Potentially Risky Service", "Known Exploited Service"]
        ),
    )


def build_fake_ticket_events(ticket, port_scans, vuln_scans):
    """Build fake TicketEvent objects for a given ticket."""
    base_time = ticket.opened_timestamp or (timezone.now() - timedelta(days=365))
    use_vuln_scan = random.choice([True, False])
    vuln_scan_to_use = random.choice(vuln_scans) if use_vuln_scan else None
    port_scan_to_use = random.choice(port_scans) if not use_vuln_scan else None

    templates = [
        {"action": "OPENED", "reason": "backfill new"},
        {"action": "VERIFIED", "reason": "backfill verified"},
        {
            "action": "CHANGED",
            "reason": "details changed",
            "delta": [
                {"from": None, "key": "score_source", "to": ticket.cvss_score_source},
                {"from": None, "key": "cve", "to": ticket.cve_string},
            ],
        },
        {"action": "CLOSED", "reason": "backfill auto closed (not latest)"},
    ]
    events = []
    for i, tmpl in enumerate(templates):
        event_time = base_time + timedelta(days=i * 30)
        events.append(
            TicketEvent(
                ticket=ticket,
                action=tmpl["action"],
                reason=tmpl["reason"],
                event_timestamp=event_time,
                reference=str(uuid.uuid4()) if random.random() < 0.7 else None,
                vuln_scan=vuln_scan_to_use,
                port_scan=port_scan_to_use,
                delta=tmpl.get("delta", []),
            )
        )
    return events


def generate_cidr_blocks(n=5):
    """Generate a list of random CIDR blocks."""
    cidrs = []
    for _ in range(n):
        # Generate random private IP ranges
        net = ipaddress.IPv4Network(
            f"{random.randint(10, 172)}.{random.randint(0, 255)}.{random.randint(0, 255)}.0/{random.choice([26, 27, 28])}",
            strict=False,
        )
        cidrs.append(str(net))
    return cidrs


def generate_acronym(name: str) -> str:
    """Generate an acronym from a given name."""
    # Take first letters of up to 4 words
    words = name.split()
    acronym = "".join(word[0] for word in words[:4]).upper()

    # Pad if too short
    if len(acronym) < 3:
        acronym += "".join(random.choices(string.ascii_uppercase, k=3 - len(acronym)))

    # Truncate if too long
    return acronym[:6]


def gen_orgs(num_orgs):
    """Generate a specified number of organizations."""
    dummy_location, _ = Location.objects.get_or_create(
        id=uuid.uuid4(), defaults={"name": fake.city()}
    )

    orgs = []
    LOGGER.info("Generating %d organizations...", num_orgs)
    for i in range(num_orgs):
        try:
            company = fake.company()
            acronym = generate_acronym(company)
            state = fake.state()
            region_id = REGION_STATE_MAP[state]
            org = Organization.objects.create(
                acronym=acronym,
                name=company,
                retired=False,
                root_domains=[fake.domain_name() for _ in range(2)],
                ip_blocks=generate_cidr_blocks(),
                is_passive=fake.boolean(),
                pending_domains=[fake.domain_name() for _ in range(2)],
                date_pe_first_reported=timezone.now(),
                country=fake.country_code(),
                country_name=fake.country(),
                state=fake.state_abbr(),
                region_id=region_id,
                state_fips=fake.random_int(min=1, max=99),
                state_name=state,
                county=fake.city(),
                county_fips=fake.random_int(min=1000, max=9999),
                type=random.choice(["PRIVATE", "FEDERAL", "STATE"]),
                pe_report_on=fake.boolean(),
                pe_premium=fake.boolean(),
                pe_demo=fake.boolean(),
                agency_type=random.choice(["Federal", "State", "Local", "Private"]),
                is_parent=fake.boolean(),
                pe_run_scans=fake.boolean(),
                stakeholder=True,
                election=fake.boolean(),
                was_stakeholder=fake.boolean(),
                vs_stakeholder=fake.boolean(),
                pe_stakeholder=fake.boolean(),
                receives_cyhy_report=fake.boolean(),
                receives_bod_report=fake.boolean(),
                receives_cybex_report=fake.boolean(),
                init_stage=random.choice(["stage_1", "stage_2", "stage_3"]),
                scheduler=random.choice(["cron", "manual", "event"]),
                enrolled_in_vs_timestamp=timezone.now(),
                period_start_vs_timestamp=timezone.now(),
                report_types=["CYHY"],
                scan_types=["CYHY"],
                scan_windows=[],
                scan_limits=[],
                password=fake.password(length=12),
                cyhy_period_start=fake.date_this_decade(),
                location=dummy_location,
                parent=None,
                created_by=None,
            )
            orgs.append(org)
            user = create_sample_user(org)

            # Create an API key for the user
            create_api_key_for_user(user)

            test_user = create_test_user(org)

            create_api_key_for_user(test_user)
        except IntegrityError:
            continue
    LOGGER.info("Generated %d organizations.", len(orgs))
    return orgs


def create_ip_hash(ip_str: str) -> str:
    """Create a SHA-256 hash of the given IP address string."""
    return hashlib.sha256(ip_str.encode()).hexdigest()


def create_cidrs_for_org(org, cidr_list, data_source=None, ips_per_cidr=4):
    """Create CIDR objects and link them to the organization."""
    for cidr_str in cidr_list:
        try:
            net = ipaddress.ip_network(cidr_str, strict=False)
            cidr_obj, _ = Cidr.objects.get_or_create(
                network=str(net),
                defaults={
                    "start_ip": str(net.network_address),
                    "end_ip": str(net.broadcast_address),
                    "retired": False,
                    "data_source": data_source,
                },
            )

            # Link CIDR to Org
            CidrOrgs.objects.get_or_create(
                organization=org, cidr=cidr_obj, defaults={"current": True}
            )

            # Generate IPs from this CIDR
            usable_ips = list(net.hosts())
            for ip_addr in usable_ips[:ips_per_cidr]:
                ip_str = str(ip_addr)
                ip_hash = create_ip_hash(ip_str)

                Ip.objects.create(
                    ip=ip_str,
                    ip_hash=ip_hash,
                    organization=org,
                    origin_cidr=cidr_obj,
                    live=random.choice([True, False]),
                    false_positive=False,
                    retired=False,
                    from_cidr=True,
                    last_seen_timestamp=timezone.now(),
                    last_reverse_lookup=timezone.now(),
                    has_shodan_results=random.choice([True, False]),
                    current=random.choice([True, True, True, False]),
                    conflict_alerts=[],
                    synced_at=timezone.now(),
                )

        except ValueError:
            LOGGER.warning("Skipping invalid CIDR: %s", cidr_str)


def populate_sample_data():
    """Populate the database with sample data."""
    orgs = Organization.objects.all()

    if len(orgs) == 0:
        gen_orgs(FAKE_ORG_COUNT)
        orgs = Organization.objects.all()

    for org in orgs:
        cidrs = generate_cidr_blocks()
        create_cidrs_for_org(org, cidrs)

    LOGGER.info("Populating vuln_scans, port_scans, tickets, and ticket_events...")
    for idx, org in enumerate(orgs, start=1):
        try:
            if idx == 1:
                continue
            with transaction.atomic():
                # Bulk create CVEs (once per run)
                build_fake_cve()  # Generates 1 or skips if exists. You could loop N times if needed.

                # VulnScans
                vulnscans = [
                    build_fake_vulnscan(org) for _ in range(FAKE_VULN_SCAN_COUNT)
                ]
                VulnScan.objects.bulk_create(vulnscans, batch_size=100)

                # PortScans
                portscans = [
                    build_fake_port_scan(org) for _ in range(FAKE_PORT_SCAN_COUNT)
                ]
                PortScan.objects.bulk_create(portscans, batch_size=100)

                # Hosts
                # hosts = [build_fake_host(org) for _ in range(FAKE_HOST_COUNT)]
                # Host.objects.bulk_create(hosts, batch_size=100)

                # Tickets
                tickets = [build_fake_ticket(org) for _ in range(FAKE_TICKET_COUNT)]
                Ticket.objects.bulk_create(tickets, batch_size=100)

                # TicketEvents — after tickets exist in DB
                created_tickets = Ticket.objects.filter(organization=org).order_by(
                    "-opened_timestamp"
                )[:FAKE_TICKET_COUNT]
                all_events = []
                for ticket in created_tickets:
                    all_events.extend(
                        build_fake_ticket_events(ticket, portscans, vulnscans)
                    )
                TicketEvent.objects.bulk_create(all_events, batch_size=100)

        except Exception as e:
            LOGGER.error("❌ Error while processing org %s: %s", org.name, e)
            continue

        # Progress bar
        percent = (idx / len(orgs)) * 100
        bar_length = 40
        filled = int(bar_length * idx // len(orgs))
        bar_template = "█" * filled + "-" * (bar_length - filled)
        sys.stdout.write(
            f"\rProgress: |{bar_template}| {percent:.1f}% ({idx}/{len(orgs)})"
        )
        sys.stdout.flush()

    # Fill CIDR Live Ips
    fill_cidr_live_ips_bulk_update()

    # Create or refresh materialized views
    result = refresh_materialized_views({})
    LOGGER.info(result)

    # Refresh VS Summaries for local
    refresh_vs_summaries({})

    LOGGER.info("✅ Done populating all data.")


def create_sample_user(organization):
    """Create a sample user linked to an organization."""
    user = User.objects.create(
        first_name="Sample",
        last_name="User",
        email="user{}@example.com".format(random.randint(1, 1000)),
        user_type=UserType.GLOBAL_ADMIN,
        state=random.choice(SAMPLE_STATES),
        region_id=random.choice(SAMPLE_REGION_IDS),
    )
    # Set user as the creator of the organization (optional)
    organization.created_by = user
    organization.save()
    return user


def create_test_user(organization):
    """Create a test user linked to an organization."""
    email = os.environ.get("PW_XFD_USERNAME")

    existing_user = User.objects.filter(email=email).first()

    if existing_user:
        return existing_user

    if not existing_user:
        user = User.objects.create(
            first_name="Test",
            last_name="User",
            email=os.environ.get("PW_XFD_USERNAME"),
            user_type=UserType.GLOBAL_ADMIN,
            state=random.choice(SAMPLE_STATES),
            region_id=random.choice(SAMPLE_REGION_IDS),
            organization=organization,
        )

    return user


def create_api_key_for_user(user):
    """Create a sample API key linked to a user."""
    # Generate a random 16-byte API key
    key = secrets.token_hex(16)

    # Hash the API key
    hashed_key = hashlib.sha256(key.encode()).hexdigest()

    # Create the API key record
    ApiKey.objects.create(
        hashed_key=hashed_key,
        last_four=key[-4:],
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Print the raw key for debugging or manual testing
    LOGGER.debug(
        "Created API key for user, keep this and enter at .env file CF_API_KEY %s: %s",
        user.email,
        key,
    )


def generate_random_name():
    """Generate a random organization name using an adjective and entity noun."""
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)
    entity = random.choice(["City", "County", "Agency", "Department"])
    return "{} {} {}".format(adjective.capitalize(), entity, noun.capitalize())


def create_sample_domain(organization):
    """Create a sample domain linked to an organization."""
    domain_name = "{}-{}.crossfeed.local".format(
        random.choice(adjectives), random.choice(nouns)
    ).lower()
    ip = ".".join(map(str, (random.randint(0, 255) for _ in range(4))))
    return Domain.objects.create(
        name=domain_name,
        ip=ip,
        fromRootDomain="crossfeed.local",
        subdomainSource="findomain",
        organization=organization,
    )


def create_sample_services_and_vulnerabilities(domain):
    """Create sample services and vulnerabilities for a domain."""
    # Add random services
    if random.random() < PROB_SAMPLE_SERVICES:
        Service.objects.create(
            domain=domain,
            port=random.choice([80, 443]),
            service="http",
            serviceSource="shodan",
            wappalyzerResults=[
                {"technology": {"cpe": random.choice(cpes)}, "version": ""}
            ],
        )

    # Add random vulnerabilities
    if random.random() < PROB_SAMPLE_VULNERABILITIES:
        state = random.choice(["open", "closed"])
        Vulnerability.objects.create(
            title="Sample Vulnerability "
            + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3)),
            domain=domain,
            service=None,
            description="Sample description",
            severity=random.choice(
                [
                    None,
                    "N/A",
                    "n/a",
                    "Null",
                    "null",
                    "Undefined",
                    "undefined",
                    "",
                    "Low",
                    "Medium",
                    "High",
                    "Critical",
                    "Other",
                    "!@#$%^&*()",
                    1234,
                    "low",
                    "medium",
                    "high",
                    "critical",
                    "other",
                ]
            ),
            cve="CVE-"
            + random.choice(
                [
                    "2024-47421",
                    "2021-22501",
                    "2024-53959",
                    "2024-47422",
                    "2024-47423",
                    "2020-28163",
                    "2020-29312",
                ]
            ),
            needsPopulation=True,
            state=state,
            substate=random.choice(["unconfirmed", "exploitable"])
            if state == "open"
            else random.choice(["false-positive", "accepted-risk", "remediated"]),
            source="sample_source",
            actions=[],
            structuredData={},
        )
