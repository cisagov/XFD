"""Sample PE data for local dnstwist / Shodan development."""

# Standard Python Libraries
from datetime import date
import hashlib
import uuid

# Third-Party Libraries
from django.db import transaction
from home.models import (
    Cidrs,
    DataSource,
    Ips,
    IpsSubs,
    Organizations,
    RootDomains,
    SubDomains,
)

# Public "please scan me" hosts — safe for local API testing (not agency IPs).
SAMPLE_ORGS = (
    {
        "name": "Department of Homeland Security (DHS)",
        "cyhy_db_name": "DHS",
        "report_on": True,
        "root_domain": "dhs.gov",
        # Shodan's official test host
        "shodan_ip": "198.20.70.201",
        "shodan_cidr": "198.20.70.201/32",
        "shodan_root": "shodan.io",
        "shodan_domain": "scanme.shodan.io",
    },
    {
        "name": "Cybersecurity and Infrastructure Security Agency (CISA)",
        "cyhy_db_name": "DHS_CISA",
        "report_on": True,
        "root_domain": "cisa.gov",
        # Nmap's official test host
        "shodan_ip": "45.33.32.156",
        "shodan_cidr": "45.33.32.156/32",
        "shodan_root": "nmap.org",
        "shodan_domain": "scanme.nmap.org",
    },
)


def _ip_hash(ip_str: str) -> str:
    """Return a SHA-256 hash for an IP address string."""
    return hashlib.sha256(ip_str.encode()).hexdigest()


def _ensure_shodan_sample(org, shodan_source, today, org_spec):
    """Create CIDR, domain, IP, and IpsSubs for one org's Shodan test host."""
    sample_ip = org_spec["shodan_ip"]
    sample_cidr = org_spec["shodan_cidr"]
    sample_root = org_spec["shodan_root"]
    sample_domain = org_spec["shodan_domain"]

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

    org_names = []
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

        shodan_samples.append(
            _ensure_shodan_sample(org, shodan_source, today, org_spec)
        )

    return {
        "data_sources": [
            dnsmonitor_source.name,
            dnstwist_source.name,
            findomain_source.name,
            shodan_source.name,
        ],
        "organizations": org_names,
        "shodan_samples": shodan_samples,
        # Keep legacy keys for pesyncdb logging (DHS sample).
        "shodan_sample_ip": shodan_samples[0]["ip"] if shodan_samples else None,
        "shodan_sample_domain": (
            shodan_samples[0]["domain"] if shodan_samples else None
        ),
    }
