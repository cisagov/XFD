"""Sample PE data for local dnstwist / Shodan development."""

# Standard Python Libraries
from datetime import date
import hashlib
import ipaddress
import uuid

# Third-Party Libraries
from django.db import transaction
from home.models import (
    Cidrs,
    DataSource,
    Executives,
    Ips,
    IpsSubs,
    Organizations,
    RootDomains,
    SubDomains,
)

# Public hosts that Shodan crawls constantly, so they reliably return banners
# in the scan's 30-day window. This is local scan testing only — the IPs are
# not real agency assets, we just want rows to land in shodan_assets/vulns.
#
# Each org can list multiple Shodan hosts. scanme.nmap.org is kept because it
# also produces verified/potential vuln rows (Apache), while the big public
# DNS resolvers are crawled daily and guarantee fresh asset banners.
SAMPLE_ORGS = (
    {
        "name": "Department of Homeland Security (DHS)",
        "cyhy_db_name": "DHS",
        "report_on": True,
        "root_domain": "dhs.gov",
        "shodan_hosts": (
            {
                "ip": "8.8.8.8",
                "cidr": "8.8.8.8/32",
                "root": "google.com",
                "domain": "dns.google",
            },
            {
                "ip": "1.1.1.1",
                "cidr": "1.1.1.1/32",
                "root": "one.one.one.one",
                "domain": "one.one.one.one",
            },
        ),
    },
    {
        "name": "Cybersecurity and Infrastructure Security Agency (CISA)",
        "cyhy_db_name": "DHS_CISA",
        "report_on": True,
        "root_domain": "cisa.gov",
        "shodan_hosts": (
            {
                "ip": "45.33.32.156",
                "cidr": "45.33.32.156/32",
                "root": "nmap.org",
                "domain": "scanme.nmap.org",
            },
            {
                "ip": "9.9.9.9",
                "cidr": "9.9.9.9/32",
                "root": "quad9.net",
                "domain": "dns.quad9.net",
            },
        ),
    },
)


def _ip_hash(ip_str: str) -> str:
    """Return a SHA-256 hash for an IP address string."""
    return hashlib.sha256(ip_str.encode()).hexdigest()


def _ensure_shodan_sample(org, shodan_source, today, host_spec):
    """Create CIDR, domain, IP, and IpsSubs for one org's Shodan test host."""
    sample_ip = host_spec["ip"]
    sample_cidr = host_spec["cidr"]
    sample_root = host_spec["root"]
    sample_domain = host_spec["domain"]

    cidr, created = Cidrs.objects.get_or_create(
        organizations_uid=org,
        network=sample_cidr,
        defaults={
            "cidr_uid": uuid.uuid4,
            "data_source_uid": shodan_source,
            "first_seen": today,
            "last_seen": today,
            "current": True,
        },
    )
    if not created:
        Cidrs.objects.filter(pk=cidr.pk).update(
            data_source_uid=shodan_source,
            last_seen=today,
            current=True,
        )

    shodan_root, created = RootDomains.objects.get_or_create(
        organizations_uid=org,
        root_domain=sample_root,
        defaults={
            "root_domain_uid": uuid.uuid4,
            "ip_address": sample_ip,
            "data_source_uid": shodan_source,
            "enumerate_subs": False,
        },
    )
    if not created:
        RootDomains.objects.filter(pk=shodan_root.pk).update(
            ip_address=sample_ip,
            data_source_uid=shodan_source,
        )

    subdomain, created = SubDomains.objects.get_or_create(
        sub_domain=sample_domain,
        root_domain_uid=shodan_root,
        defaults={
            "sub_domain_uid": uuid.uuid4,
            "data_source_uid": shodan_source,
            "first_seen": today,
            "last_seen": today,
            "current": True,
            "identified": True,
            "status": True,
        },
    )
    if not created:
        SubDomains.objects.filter(pk=subdomain.pk).update(
            data_source_uid=shodan_source,
            last_seen=today,
            current=True,
            identified=True,
            status=True,
        )

    ip_obj, _ = Ips.objects.update_or_create(
        ip_hash=_ip_hash(sample_ip),
        defaults={
            "ip": sample_ip,
            "origin_cidr": cidr,
            "organizations_uid": org.organizations_uid,
            "shodan_results": True,
            "live": True,
            "current": True,
            "from_cidr": True,
            "first_seen": today,
            "last_seen": today,
        },
    )
    IpsSubs.objects.get_or_create(
        ip_hash=ip_obj,
        sub_domain_uid=subdomain,
        defaults={"ips_subs_uid": uuid.uuid4},
    )

    return {
        "org": org.cyhy_db_name,
        "ip": sample_ip,
        "domain": sample_domain,
    }


@transaction.atomic
def populate_sample_data():
    """Insert data sources, orgs, domains, and Shodan test IPs for local scans."""
    today = date.today()

    dnsmonitor_source, created = DataSource.objects.get_or_create(
        name="DNSMonitor",
        defaults={
            "data_source_uid": uuid.uuid4,
            "description": "DNSMonitor domain alerts scan",
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(pk=dnsmonitor_source.pk).update(
            description="DNSMonitor domain alerts scan",
            last_run=today,
        )

    dnstwist_source, created = DataSource.objects.get_or_create(
        name="DNSTwist",
        defaults={
            "data_source_uid": uuid.uuid4,
            "description": "DNSTwist domain permutation scan",
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(pk=dnstwist_source.pk).update(
            description="DNSTwist domain permutation scan",
            last_run=today,
        )

    flare_source, created = DataSource.objects.get_or_create(
        name="Flare",
        defaults={
            "data_source_uid": uuid.uuid4,
            "description": "Flare scan",
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(pk=flare_source.pk).update(
            description="Flare scan",
            last_run=today,
        )

    findomain_source, created = DataSource.objects.get_or_create(
        name="findomain",
        defaults={
            "data_source_uid": uuid.uuid4,
            "description": "findomain subdomain enumeration",
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(pk=findomain_source.pk).update(
            description="findomain subdomain enumeration",
            last_run=today,
        )

    shodan_source, created = DataSource.objects.get_or_create(
        name="Shodan",
        defaults={
            "data_source_uid": uuid.uuid4,
            "description": "Shodan internet-facing asset scan",
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(pk=shodan_source.pk).update(
            description="Shodan internet-facing asset scan",
            last_run=today,
        )

    whoisxml_source, created = DataSource.objects.get_or_create(
        name="WhoisXML",
        defaults={
            "data_source_uid": uuid.uuid4,
            "description": "WhoisXML IP and subdomain asset enumeration",
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(pk=shodan_source.pk).update(
            description="WhoisXML IP and subdomain asset enumeration",
            last_run=today,
        )

    org_names = []
    org_objs = {}
    shodan_samples = []

    for org_spec in SAMPLE_ORGS:
        root_domain = org_spec["root_domain"]
        org, created = Organizations.objects.get_or_create(
            cyhy_db_name=org_spec["cyhy_db_name"],
            defaults={
                "organizations_uid": uuid.uuid4,
                "name": org_spec["name"],
                "report_on": org_spec["report_on"],
            },
        )
        if not created:
            Organizations.objects.filter(pk=org.pk).update(
                name=org_spec["name"],
                report_on=org_spec["report_on"],
            )
        org_names.append(org_spec["cyhy_db_name"])
        org_objs[org_spec["cyhy_db_name"]] = org

        root, created = RootDomains.objects.get_or_create(
            organizations_uid=org,
            root_domain=root_domain,
            defaults={
                "root_domain_uid": uuid.uuid4,
                "data_source_uid": findomain_source,
                "enumerate_subs": True,
            },
        )
        if not created:
            RootDomains.objects.filter(pk=root.pk).update(
                data_source_uid=findomain_source,
                enumerate_subs=True,
            )

        for host_spec in org_spec["shodan_hosts"]:
            shodan_samples.append(
                _ensure_shodan_sample(org, shodan_source, today, host_spec)
            )

    # Create CIDRs/IPs
    cidr_list = [
        ("DHS_CISA", "8.8.8.8/32"),
        ("DHS_CISA", "192.168.1.31/32"),
        ("DHS", "192.0.2.1/32"),
        ("DHS", "9.9.9.9/32"),
    ]
    # For each CIDR
    for cidr_tup in cidr_list:
        # Create CIDR
        curr_org = org_objs.get(cidr_tup[0])
        curr_cidr = cidr_tup[1]
        cidr_obj, created = Cidrs.objects.get_or_create(
            organizations_uid=curr_org,
            network=curr_cidr,
            defaults={
                "cidr_uid": uuid.uuid4,
                "data_source_uid": whoisxml_source,
                "first_seen": today,
                "last_seen": today,
                "current": True,
            },
        )
        if not created:
            Cidrs.objects.filter(pk=cidr_obj.pk).update(
                data_source_uid=whoisxml_source,
                last_seen=today,
                current=True,
            )
        # Create IPs for CIDR
        network = ipaddress.ip_network(curr_cidr)
        ips_list = [str(ip) for ip in network]
        for curr_ip in ips_list:
            ip_obj, _ = Ips.objects.update_or_create(
                ip_hash=_ip_hash(curr_ip),
                defaults={
                    "ip": curr_ip,
                    "origin_cidr": cidr_obj,
                    "organizations_uid": curr_org.organizations_uid,
                    "shodan_results": True,
                    "live": True,
                    "current": True,
                    "from_cidr": True,
                    "first_seen": today,
                    "last_seen": today,
                },
            )

    # Create executives
    exec_list = [
        {
            "org_abbrv": "DHS_CISA",
            "org_uid": org_objs.get("DHS_CISA"),
            "prefix": "Mr.",
            "first_name": "John",
            "middle_initial": "A.",
            "last_name": "Smith",
            "suffix": "ii",
            "last_modified": today,
        },
        {
            "org_abbrv": "DHS",
            "org_uid": org_objs.get("DHS"),
            "prefix": "Ms.",
            "first_name": "Jane",
            "middle_initial": "B.",
            "last_name": "Doe",
            "suffix": "iii",
            "last_modified": today,
        },
    ]
    for exec in exec_list:
        exec_obj, created = Executives.objects.update_or_create(
            organizations_uid=exec.get("org_uid"),
            first_name=exec.get("first_name"),
            last_name=exec.get("last_name"),
            defaults={
                "executives_uid": uuid.uuid4,
                "prefix": exec.get("prefix"),
                "middle_initial": exec.get("middle_initial"),
                "suffix": exec.get("suffix"),
                "last_modified": exec.get("last_modified"),
                "sixgill_id": "",
            },
        )

    return {
        "data_sources": [
            dnsmonitor_source.name,
            dnstwist_source.name,
            findomain_source.name,
            flare_source.name,
            shodan_source.name,
            whoisxml_source.name,
        ],
        "organizations": org_names,
        "shodan_samples": shodan_samples,
        # Keep legacy keys for pesyncdb logging (DHS sample).
        "shodan_sample_ip": shodan_samples[0]["ip"] if shodan_samples else None,
        "shodan_sample_domain": (
            shodan_samples[0]["domain"] if shodan_samples else None
        ),
    }
