"""Syncdb helpers."""
# File: xfd_api/utils/db_utils.py
# Standard Python Libraries
from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import ipaddress
from itertools import islice
import json
import os
import random
import secrets
import string
import sys
from typing import Optional
import uuid

# Third-Party Libraries
from django.apps import apps
from django.conf import settings
from django.db import IntegrityError, connections, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone
from faker import Faker
from psycopg2.errors import WrongObjectType
from xfd_api.helpers.regionStateMap import REGION_STATE_MAP
from xfd_api.models import Domain, Service, Vulnerability
from xfd_api.tasks.es_client import ESClient
from xfd_mini_dl.models import (
    ApiKey,
    Cidr,
    CidrOrgs,
    Cve,
    Host,
    HostSummary,
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

# Constants for sample data generation
SAMPLE_TAG_NAME = "Sample Data"
NUM_SAMPLE_ORGS = 10
NUM_SAMPLE_DOMAINS = 10
PROB_SAMPLE_SERVICES = 0.5
PROB_SAMPLE_VULNERABILITIES = 0.5
SAMPLE_STATES = ["Virginia", "California", "Colorado"]
SAMPLE_REGION_IDS = ["1", "2", "3"]
ORGANIZATION_CHUNK_SIZE = 50
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

# Elasticsearch client
es_client = ESClient()


def manage_elasticsearch_indices(dangerouslyforce):
    """Handle Elasticsearch index setup and teardown."""
    try:
        if dangerouslyforce:
            es_client.delete_all()
        es_client.sync_organizations_index()
        es_client.sync_domains_index()
        print("Elasticsearch indices synchronized.")
    except Exception as e:
        print("Error managing Elasticsearch indices: {}".format(e))


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

    print(f"⚠️ Failed to generate IP from any CIDR for org: {org}")
    return None


def build_fake_cve() -> Cve:
    """Build a fake CVE object."""
    year = random.randint(2000, 2024)
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


def build_fake_host_summaries():
    """Build a fake Ticket for a pssed org."""
    all_orgs = Organization.objects.all()

    for org in all_orgs:
        try:
            summary_date = timezone.now().date()
            start_date = timezone.now() - timedelta(
                days=random.randint(25, 60), seconds=random.randint(0, 86400)
            )
            end_date = timezone.now() - timedelta(
                days=random.randint(1, 5), seconds=random.randint(0, 86400)
            )
            host_done_count = random.randint(3000, 5000)
            host_waiting_count = random.randint(0, 50)
            host_running_count = random.randint(0, 50)
            host_ready_count = random.randint(0, 50)
            total_count = (
                host_done_count
                + host_waiting_count
                + host_running_count
                + host_ready_count
            )
            up_host_count = total_count - random.randint(0, 1500)
            down_host_count = total_count - up_host_count

            HostSummary.objects.update_or_create(
                organization=org,
                summary_date=summary_date,
                defaults={
                    "start_date": start_date,
                    "end_date": end_date,
                    "host_done_count": host_done_count,
                    "host_waiting_count": host_waiting_count,
                    "host_running_count": host_running_count,
                    "host_ready_count": host_ready_count,
                    "up_host_count": up_host_count,
                    "down_host_count": down_host_count,
                    "scanned_asset_count": total_count,
                },
            )
        except Exception as e:
            print("\n❌ Error while creating host_summary for org %s: %s", org.name, e)
            continue


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
        false_positive=False,
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
        is_kev=random.choice([True, True, False]),
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
    print(f"Generating {num_orgs} organizations...")
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
    print(f"Generated {len(orgs)} organizations.")
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
                    current=random.choice([True, False]),
                    conflict_alerts=[],
                    synced_at=timezone.now(),
                )

        except ValueError:
            print(f"Skipping invalid CIDR: {cidr_str}")


def populate_sample_data():
    """Populate the database with sample data."""
    orgs = Organization.objects.all()

    if len(orgs) == 0:
        gen_orgs(FAKE_ORG_COUNT)
        orgs = Organization.objects.all()

    for org in orgs:
        cidrs = generate_cidr_blocks()
        create_cidrs_for_org(org, cidrs)

    print("Populating vuln_scans, port_scans, tickets, and ticket_events...")
    for idx, org in enumerate(orgs, start=1):
        try:
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
            print(f"\n❌ Error while processing org {org.name}: {e}")
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

    print("\n✅ Done populating all data.")


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
    print(
        "Created API key for user, keep this and enter at .env file CF_API_KEY {}: {}".format(
            user.email, key
        )
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


def table_exists_in_db(table_name, database):
    """Check table exists."""
    with connections[database].cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s);", [table_name])
        return cursor.fetchone()[0] is not None


def synchronize(target_app_label=None, using=None):
    """
    Synchronize the database schema with Django models.

    Handles creation, update, and removal of tables and fields dynamically,
    including Many-to-Many linking tables.
    """
    allowed_labels = ["xfd_mini_dl", "xfd_api"]
    db_mapping = {
        "xfd_mini_dl": "mini_data_lake",
        "xfd_api": "default",
    }

    if target_app_label is None:
        raise ValueError(
            "The 'target_app_label' parameter is required to synchronize specific models. "
            "Please provide an app label."
        )

    if target_app_label not in allowed_labels:
        raise ValueError(
            "Invalid 'target_app_label' provided. Must be one of: {}.".format(
                ", ".join(allowed_labels)
            )
        )

    # Get database name for 'connections':
    # The 'connections' object gets all databases defined in settings.py
    database = db_mapping.get(target_app_label, "default")
    # Used only for syncing a duplicate database that mirrors the xfd_mini_dl schema
    if using:
        database = using
    print(
        "Synchronizing database schema for app '{}' in database '{}'...".format(
            target_app_label, database
        )
    )

    # Warning: Cursor automatically closes after use of 'with'
    with connections[database].schema_editor() as schema_editor:
        ordered_models = get_ordered_models(target_app_label)
        # Compute allowed table names from the models we are syncing.
        allowed_tables = {m._meta.db_table for m in ordered_models}
        for model in ordered_models:
            print("Processing model: {}".format(model.__name__))
            process_model(schema_editor, model, database, allowed_tables)

        print("Processing Many-to-Many tables...")
        process_m2m_tables(schema_editor, ordered_models, database)

        if target_app_label == "xfd_mini_dl":
            create_domain_view(database)
            create_service_view(database)
            create_vuln_normal_views(database)
            create_vuln_materialized_views(database)

        cleanup_stale_tables(ordered_models, database)

    print("Database synchronization complete.")


def get_ordered_models(target_app_label):
    """
    Get models in dependency order to ensure foreign key constraints are respected.

    Only consider dependencies among models within the same app, and break cycles
    deterministically (alphabetically by model name).
    """
    # Get all models for the app and create a set for quick membership checks.
    models = [
        m for m in apps.get_app_config(target_app_label).get_models() if m._meta.managed
    ]
    model_set = set(models)

    # Build dependency graph, but only include dependencies to models within the app.
    dependencies = defaultdict(set)
    dependents = defaultdict(set)
    for model in models:
        for field in model._meta.get_fields():
            # Only add a dependency if the related model is in our app's set.
            if field.is_relation and field.related_model in model_set:
                dependencies[model].add(field.related_model)
                dependents[field.related_model].add(model)

    # Start with models that have no dependencies.
    ordered = []
    independent_models = deque([model for model in models if not dependencies[model]])

    while independent_models:
        model = independent_models.popleft()
        ordered.append(model)
        # Remove this model as a dependency from its dependents.
        for dependent in list(dependents[model]):
            dependencies[dependent].discard(model)
            dependents[model].discard(dependent)
            if not dependencies[dependent]:
                independent_models.append(dependent)

    # Any models not yet added are in a dependency cycle.
    remaining = [model for model in models if model not in ordered]
    if remaining:
        print(
            "Circular dependencies detected among: {}".format(
                ", ".join(m.__name__ for m in remaining)
            )
        )
        # Sort them deterministically (alphabetically) so that, for example, 'User' comes before 'Organization'
        remaining_sorted = sorted(remaining, key=lambda m: m.__name__)
        ordered.extend(remaining_sorted)

    return ordered


def process_model(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Process a single model: create or update its table."""
    table_name = model._meta.db_table

    with connections[database].cursor() as cursor:
        try:
            # Check if the table exists
            cursor.execute("SELECT to_regclass(%s);", [table_name])
            table_exists = cursor.fetchone()[0] is not None

            if table_exists:
                print("Updating table for model: {}".format(model.__name__))
                update_table(schema_editor, model, database, allowed_tables)
            else:
                print("Creating table for model: {}".format(model.__name__))
                schema_editor.create_model(model)
        except Exception as e:
            print("Error processing model {}: {}".format(model.__name__, e))


def process_m2m_tables(schema_editor: BaseDatabaseSchemaEditor, models, database):
    """Handle creation of Many-to-Many linking tables."""
    with connections[database].cursor() as cursor:
        for model in models:
            for field in model._meta.local_many_to_many:
                m2m_table_name = field.m2m_db_table()

                # Check if the M2M table exists
                cursor.execute("SELECT to_regclass('{}');".format(m2m_table_name))
                table_exists = cursor.fetchone()[0] is not None

                if not table_exists:
                    print("Creating Many-to-Many table: {}".format(m2m_table_name))
                    schema_editor.create_model(field.remote_field.through)
                else:
                    print(
                        "Many-to-Many table {} already exists. Skipping.".format(
                            m2m_table_name
                        )
                    )


def update_table(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Update an existing table for the given model. Ensure columns match fields."""
    table_name = model._meta.db_table
    db_fields = {field.column for field in model._meta.fields}

    with connections[database].cursor() as cursor:
        # Get existing columns
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            [table_name],
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        # Add missing columns
        missing_columns = db_fields - existing_columns
        for field in model._meta.fields:
            if field.column in missing_columns:
                if hasattr(field, "remote_field") and field.remote_field:
                    related_table = field.remote_field.model._meta.db_table
                    # If the related table isn't in allowed_tables or doesn't exist yet, skip adding this field.
                    if related_table not in allowed_tables or not table_exists_in_db(
                        related_table, database
                    ):
                        print(
                            "Skipping addition of foreign key field '{}' on model '{}' because referenced table '{}' does not exist yet.".format(
                                field.column, model.__name__, related_table
                            )
                        )
                        continue
                print(
                    "Adding column '{}' to table '{}'".format(field.column, table_name)
                )
                schema_editor.add_field(model, field)

        # Remove extra columns
        extra_columns = existing_columns - db_fields
        for column in extra_columns:
            print(
                "Removing extra column '{}' from table '{}'".format(column, table_name)
            )
            try:
                safe_table_name = connections[database].ops.quote_name(table_name)
                safe_column_name = connections[database].ops.quote_name(column)
                query = "ALTER TABLE {} DROP COLUMN IF EXISTS {};".format(
                    safe_table_name, safe_column_name
                )
                cursor.execute(query)
            except Exception as e:
                print(
                    "Error dropping column '{}' from table '{}': {}".format(
                        column, table_name, e
                    )
                )


def cleanup_stale_tables(models, database):
    """Remove tables that no longer correspond to any Django model or Many-to-Many relationship."""
    print("Checking for stale tables...")

    with connections[database].cursor() as cursor:
        model_tables = {model._meta.db_table for model in models if model._meta.managed}
        # [m for m in apps.get_app_config(target_app_label).get_models() if m._meta.managed]
        m2m_tables = {
            field.m2m_db_table()
            for model in models
            # if model._meta.managed
            for field in model._meta.local_many_to_many
        }
        expected_tables = model_tables.union(m2m_tables)

        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        existing_tables = {row[0] for row in cursor.fetchall()}

        # Get regular views
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public';
        """
        )
        regular_views = {row[0] for row in cursor.fetchall()}

        # Get materialized views
        cursor.execute(
            """
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'public';
        """
        )
        materialized_views = {row[0] for row in cursor.fetchall()}

        # Combine both
        all_views = regular_views.union(materialized_views)
        existing_tables = existing_tables - all_views
        stale_tables = existing_tables - expected_tables
        for table in stale_tables:
            print("Removing stale table: {}".format(table))
            try:
                # Use `quote_ident` to safely handle table names with special characters or reserved words
                cursor.execute(
                    "DROP TABLE {} CASCADE;".format(
                        connections[database].ops.quote_name(table)
                    )
                )
            except OperationalError as e:
                print("Error dropping stale table {}: {}".format(table, e))
            except WrongObjectType as e:
                print("Tried to drop a non table entity {}: {}".format(table, e))
            except ProgrammingError as e:
                print("Issue dropping entity {}: {}".format(table, e))


def drop_all_tables(app_label=None):
    """Drop all tables in the database. Used with `dangerouslyforce`."""
    allowed_labels = ["xfd_mini_dl", "xfd_api"]
    db_mapping = {
        "xfd_mini_dl": "mini_data_lake",
        "xfd_api": "default",
    }

    if app_label is None:
        raise ValueError(
            "The 'app_label' parameter is required to synchronize specific models."
        )

    if app_label not in allowed_labels:
        raise ValueError(
            "Invalid 'app_label' provided. Must be one of: {}.".format(
                ", ".join(allowed_labels)
            )
        )

    database = db_mapping.get(app_label, "default")
    print(
        "Resetting database schema for app '{}' in database '{}'...".format(
            app_label, database
        )
    )

    with connections[database].cursor() as cursor:
        try:
            # Drop all constraints first to avoid foreign key dependency issues
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute(
                "GRANT ALL ON SCHEMA public TO {};".format(os.getenv("DB_USERNAME"))
            )
            cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        except Exception as e:
            print("Error resetting schema: {}".format(e))

    print("Database schema reset successfully.")


def chunked_iterable(iterable, size):
    """Yield successive chunks of size `size` from `iterable`."""
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            break
        yield chunk


def update_organization_chunk(es_client, organizations):
    """Update a chunk of organizations."""
    es_client.update_organizations(organizations)


def sync_es_organizations():
    """Sync elastic search organizations."""
    try:
        # Fetch all organization IDs
        organization_ids = list(Organization.objects.values_list("id", flat=True))
        print("Found {} organizations to sync.".format(len(organization_ids)))

        if organization_ids:
            # Split IDs into chunks
            for organization_chunk in chunked_iterable(
                organization_ids, ORGANIZATION_CHUNK_SIZE
            ):
                # Fetch full organization data for the current chunk
                organizations = list(
                    Organization.objects.filter(id__in=organization_chunk).values(
                        "id",
                        "name",
                        "country",
                        "state",
                        "region_id",
                        "tags",
                    )
                )
                print("Syncing {} organizations...".format(len(organizations)))

                # Attempt to update Elasticsearch
                update_organization_chunk(es_client, organizations)

            print("Organization sync complete.")
        else:
            print("No organizations to sync.")

    except Exception as e:
        print("Error syncing organizations: {}".format(e))
        raise e


def create_vuln_normal_views(database):
    """Create vuln normal views."""
    with connections[database].cursor() as cursor:
        print("Creating normal views...")
        cursor.execute(
            """
            DROP VIEW IF EXISTS vw_ticket_vulns CASCADE;
        """
        )

        cursor.execute(
            """
            DROP VIEW IF EXISTS vw_shodan_vulns CASCADE;
        """
        )

        cursor.execute(
            """
            DROP VIEW IF EXISTS vw_credential_breaches CASCADE;
        """
        )
        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_ticket_vulns AS
            -- Query for VS Ticket Vulns
            SELECT
                'vuln_scanning_tickets' as scan_source,
                t.id as vuln_id,
                t.opened_timestamp::timestamp as created_at,
                t.updated_timestamp::timestamp as updated_at,
                coalesce(t.closed_timestamp::timestamp, t.updated_timestamp::timestamp) as last_seen,
                t.cve_string as cve,
                t.vuln_name as title,
                vs.cpe as product,
                t.ip_string as domain_string,
                COALESCE(sub_link.sub_domain_id, t.ip_id) AS domain_id,
                t.port_protocol as protocol,
                t.vuln_port::text as port,
                t.cvss_base_score,
                --COALESCE(t.cvss_severity::text, 'N/A') as severity,
                CASE
                    WHEN t.cvss_severity = 0 THEN 'N/A'
                    WHEN t.cvss_severity = 1 THEN 'Low'
                    WHEN t.cvss_severity = 2 THEN 'Medium'
                    WHEN t.cvss_severity = 3 THEN 'High'
                    WHEN t.cvss_severity = 4 THEN 'Critical'
                    ELSE 'N/A'
                END AS severity,
                t.organization_id,
                CASE
                    WHEN t.is_open THEN 'open'
                    ELSE 'closed'
                END AS state,
                t.vuln_source as data_source,
                COALESCE(vs.description, te.reason, 'N/A') as description,
                t.is_kev::bool as is_kev,
                t.service_name as service_string,
                t.is_risky::bool as is_risky_service,
                --null as os, --t.os as os --Not seeing this in the ticket
                t.operating_system as os,
                null as cwe,
                vs.cpe as cpe,
                null as references,
                'unconfirmed' as substate,
                null as needs_population,
                null as actions,
                null as structured_data,
                null as kev_results,
                --Additional fields requested:
                t.ip_string,
                vs.cvss_vector,
                t.cvss_severity as severity_int,
                vs.plugin_id,
                vs.solution,
                vs.synopsis,
                vs.plugin_output as results
            FROM ticket t
            LEFT JOIN LATERAL (
                SELECT te.*
                FROM ticket_event te
                WHERE te.ticket_id = t.id
                ORDER BY te.event_timestamp DESC, te.id DESC
                LIMIT 1
            ) te ON TRUE
            LEFT JOIN vuln_scan vs ON vs.id = te.vuln_scan_id
            LEFT JOIN LATERAL (
                SELECT sub_domain_id
                FROM ips_subs ipsubs
                WHERE ipsubs.ip_id = t.ip_id
                ORDER BY sub_domain_id
                LIMIT 1
            ) sub_link ON TRUE
            """
        )

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_shodan_vulns AS
            -- Query for ShodanVulns
            SELECT
                'shodan_vulnerability' as scan_source,
                sv.shodan_vuln_uid::text as vuln_id,
                sv."created_at"::timestamp as created_at,
                sv."timestamp"::timestamp as updated_at,
                sv."timestamp"::timestamp as last_seen,
                sv.cve as cve,
                sv.name as title,
                array_to_string(sv.cpe, ', ') as product,
                sv.ip_string as domain,
                COALESCE(sub_link.sub_domain_id, sv.ip_uid) AS domain_id,
                sv.protocol as protocol,
                sv.port as port,
                sv.cvss as cvss_base_score,
                COALESCE(sv.severity, 'N/A') as severity,
                sv.organization_uid as organization_id,
                'open' as state,
                'Shodan' as data_source,
                COALESCE(sv.summary, sv.mitigation, 'N/A') as description,
                null::bool as is_kev,
                null as service_string,
                null::bool as is_risky_service,
                null as os, --t.os as os --Not seeing this in the ticket
                null as cwe,
                array_to_string(sv.cpe, ', ') as cpe,
                null as references,
                'unconfirmed' as substate,
                null as needs_population,
                null as actions,
                null as structured_data,
                null as kev_results,
                --Additional Data requested
                sv.ip_string,
                null AS cvss_vector,
                null::int AS severity_int,
                null as plugin_id,
                null AS solution,
                null AS synopsis,
                null AS results
            FROM shodan_vulns as sv
            LEFT JOIN LATERAL (
                SELECT sub_domain_id
                FROM ips_subs ipsubs
                WHERE ipsubs.ip_id = sv.ip_uid
                ORDER BY sub_domain_id -- or ORDER BY created_at if that column exists
                LIMIT 1
            ) AS sub_link ON TRUE
        """
        )

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_credential_breaches AS
            SELECT
                scan_source,
                vuln_id,
                created_at,
                updated_at,
                last_seen,
                cve,
                title,
                product,
                domain,
                domain_id,
                protocol,
                port,
                cvss_base_score,
                severity,
                organization_id,
                state,
                data_source,
                description,
                null::bool as is_kev,
                null as service_string,
                null::bool as is_risky_service,
                null as os, --t.os as os --Not seeing this in the ticket
                null as cwe,
                null as cpe,
                null as references,
                'unconfirmed' as substate,
                null as needs_population,
                null as actions,
                null as structured_data,
                null as kev_results,
                --Additional Data requested
                null AS ip_string,
                null AS cvss_vector,
                null::int AS severity_int,
                null as plugin_id,
                null AS solution,
                null AS synopsis,
                null AS results
                FROM (
                SELECT
                    ce.credential_exposures_uid::text AS vuln_id,
                    'credential_breach' AS scan_source,
                    cb.breach_date AS created_at,
                    cb.modified_date AS updated_at,
                    cb.modified_date AS last_seen,
                    NULL AS cve,
                    cb.breach_name AS title,
                    NULL AS product,
                    COALESCE(sd.from_root_domain, sd.sub_domain) AS domain,
                    COALESCE(sd.root_domain_id, sd.sub_domain_uid) AS domain_id,
                    'SMTP,IMAP,POP3' AS protocol,
                    NULL AS port,
                    NULL::float AS cvss_base_score,
                    'N/A' AS severity,
                    ce.organization_id,
                    'open' AS state,
                    ds.name AS data_source,
                    cb.description,
                    ROW_NUMBER() OVER (
                        PARTITION BY cb.credential_breaches_uid, ce.sub_domain_id
                        ORDER BY ce.credential_exposures_uid
                    ) AS row_num
                FROM credential_breaches cb
                JOIN credential_exposures ce ON cb.credential_breaches_uid = ce.credential_breach_id
                JOIN sub_domains sd ON ce.sub_domain_id = sd.sub_domain_uid
                JOIN data_source ds ON ds.data_source_uid = cb.data_source_uid
            ) t
            WHERE row_num = 1;
        """
        )
        print("Normal views created.")


def create_vuln_materialized_views(database):
    """Create vuln materialized views."""
    with connections[database].cursor() as cursor:
        print("Creating materialized views...")

        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mat_vw_combined_vulns;")

        # Example materialized view
        cursor.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mat_vw_combined_vulns AS
            SELECT * from vw_ticket_vulns
            union
            SELECT * from vw_shodan_vulns
            union
            SELECT * from vw_credential_breaches
        """
        )

        # Create unique index required for CONCURRENTLY
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_mat_vw_combined_vulns_uid
            ON mat_vw_combined_vulns (vuln_id)
        """
        )

        # Optional refresh
        cursor.execute("REFRESH MATERIALIZED VIEW mat_vw_combined_vulns;")

        print("Materialized views created.")


def create_domain_view(database):
    """Create vw_domain view."""
    with connections[database].cursor() as cursor:
        print("Creating domain view...")
        cursor.execute("DROP VIEW IF EXISTS vw_domain;")

        # Example materialized view
        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_domain AS

            -- Subdomains (with or without linked IP)
            SELECT
                sub.sub_domain_uid AS id,
                sub.created_at,
                sub.updated_at,
                sub.synced_at,
                COALESCE(string_agg(DISTINCT host(ip.ip), ', '), NULL) AS ip,
                sub.from_root_domain,
                sub.subdomain_source,
                sub.ip_only,
                sub.reverse_name,
                sub.sub_domain AS name,
                sub.screenshot,
                sub.country,
                sub.asn,
                sub.cloud_hosted,
                ip.from_cidr,
                sub.ssl,
                sub.censys_certificates_results,
                sub.trustymail_results,
                NULL AS discovered_by_id,
                sub.organization_uid AS organization_id,
                'subdomain' as source

            FROM
                sub_domains sub
            LEFT JOIN
                ips_subs link ON sub.sub_domain_uid = link.sub_domain_id
            LEFT JOIN
                ip ON ip.id = link.ip_id
            GROUP BY
                sub.sub_domain_uid, sub.created_at, sub.updated_at, sub.synced_at,
                sub.from_root_domain, sub.subdomain_source, sub.ip_only,
                sub.reverse_name, sub.sub_domain, sub.screenshot, sub.country,
                sub.asn, sub.cloud_hosted, sub.ssl,
                sub.censys_certificates_results, sub.trustymail_results,
                sub.organization_uid, ip.from_cidr


            UNION ALL

            -- IPs with no linked subdomain
            SELECT
                ip.id,
                ip.created_timestamp AS created_at,
                ip.updated_timestamp AS updated_at,
                ip.synced_at AS synced_at,
                host(ip.ip) AS ip,
                NULL AS from_root_domain,
                NULL AS subdomain_source,
                TRUE AS ip_only,
                NULL AS reverse_name,
                host(ip.ip) AS name,
                NULL AS screenshot,
                NULL AS country,
                NULL AS asn,
                NULL AS cloud_hosted,
                ip.from_cidr,
                NULL AS ssl,
                NULL AS censys_certificates_results,
                NULL AS trustymail_results,
                NULL AS discovered_by_id,
                ip.organization_id,
                'ip' as source

            FROM
                ip
            WHERE
                ip.id NOT IN (SELECT ip_id FROM ips_subs);
        """
        )
        print("Domain view created.")


def create_service_view(database):
    """Create or replace the unified 'service' view (starting with Shodan data)."""
    with connections[database].cursor() as cursor:
        print("Creating 'service' view from ShodanAssets...")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS vw_service CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS vw_service CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS vw_shodan_service CASCADE;")
        cursor.execute("DROP VIEW IF EXISTS vw_portscan_service CASCADE;")

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_shodan_service AS
            SELECT
                s.shodan_asset_uid::text AS id,
                s.created_at AS "created_at",
                s.timestamp AS "updated_at",
                'shodan' AS "service_source",
                s.port,
                COALESCE(s.product, s.server) AS service,
                s.server AS banner,
                jsonb_build_array(
                jsonb_build_object(
                        'name', COALESCE(s.product, s.server),
                        'cpe', NULL,
                        'tags', COALESCE(s.tags, '[]'::jsonb),
                        'vendor',
                            CASE
                                WHEN s.product ILIKE 'apache%' THEN 'apache'
                                WHEN s.product ILIKE 'microsoft%' THEN 'microsoft'
                                WHEN s.product ILIKE 'nginx%' THEN 'nginx'
                                WHEN s.product ILIKE 'jquery%' THEN 'jquery'
                                ELSE split_part(lower(s.product), ' ', 1)
                            END
                    )
                ) AS products,
                NULL::jsonb AS "censys_metadata",
                NULL::jsonb AS "censys_ipv4_results",
                NULL::jsonb AS "intrigue_ident_results",
                NULL::jsonb AS "shodan_results",
                NULL::jsonb AS "wappalyzer_results",
                s.timestamp AS "last_seen",
                s.ip_string AS "ip_string",
                COALESCE(sub_link.sub_domain_id,s.ip_uid) AS domain_id,
                NULL::uuid AS discovered_by_id
            FROM shodan_assets s
            LEFT JOIN LATERAL (
                SELECT sub_domain_id
                FROM ips_subs ipsubs
                WHERE ipsubs.ip_id = s.ip_uid
                ORDER BY sub_domain_id -- or ORDER BY created_at if that column exists
                LIMIT 1
            ) AS sub_link ON TRUE
            WHERE s.port IS NOT NULL AND
            (s.product IS NOT NULL OR s.server IS NOT NULL);
        """
        )

        print("Creating 'service' view from PortScans...")

        cursor.execute(
            """
            CREATE OR REPLACE VIEW vw_portscan_service AS
            SELECT
                ps.id AS id,
                ps.time_scanned AS created_at,
                ps.time_scanned AS updated_at,
                'portscan' AS service_source,
                ps.port,
                ps.service_name AS service,
                ps.service_product AS banner,
                jsonb_build_array(
                    jsonb_build_object(
                        'name', ps.service_name,
                        'cpe', ps.service_cpe,
                        'tags', '[]'::jsonb,
                        'vendor',
                            CASE
                                WHEN ps.service_name ILIKE 'apache%' THEN 'apache'
                                WHEN ps.service_name ILIKE 'microsoft%' THEN 'microsoft'
                                WHEN ps.service_name ILIKE 'nginx%' THEN 'nginx'
                                WHEN ps.service_name ILIKE 'jquery%' THEN 'jquery'
                                ELSE split_part(lower(ps.service_name), ' ', 1)
                            END
                    )
                ) AS products,
                NULL::jsonb AS censys_metadata,
                NULL::jsonb AS censys_ipv4_results,
                NULL::jsonb AS intrigue_ident_results,
                NULL::jsonb AS shodan_results,
                NULL::jsonb AS wappalyzer_results,
                ps.time_scanned AS last_seen,
                ps.ip_string AS ip_string,
                COALESCE(sub_link.sub_domain_id, ps.ip_id) AS domain_id,
                NULL::uuid AS discovered_by_id
            FROM port_scan ps
            LEFT JOIN LATERAL (
                SELECT sub_domain_id
                FROM ips_subs ipsubs
                WHERE ipsubs.ip_id = ps.ip_id
                ORDER BY sub_domain_id
                LIMIT 1
            ) sub_link ON TRUE
            WHERE ps.latest = TRUE
            AND ps.port IS NOT NULL
            AND ps.service_name IS NOT NULL;
        """
        )

        print("Creating materialized 'vw_service' from union...")
        cursor.execute(
            """
            CREATE MATERIALIZED VIEW vw_service AS
            SELECT * FROM vw_shodan_service
            UNION ALL
            SELECT * FROM vw_portscan_service;
            """
        )

        print("Creating unique index for concurrent refresh...")
        cursor.execute(
            """
            CREATE UNIQUE INDEX idx_vw_service_id ON vw_service (id);
            """
        )

        print("View 'vw_service' created.")
