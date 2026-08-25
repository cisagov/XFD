"""Sample PE data for local dnstwist, Shodan, and report development."""

# Standard Python Libraries
from datetime import date
import hashlib
import ipaddress
import uuid

# Third-Party Libraries
from django.db import IntegrityError, transaction
from home.models import (
    Cidrs,
    DataSource,
    DomainAlerts,
    Executives,
    FlareEvents,
    FlareEventTypes,
    Ips,
    IpsSubs,
    Organizations,
    ReportSummaryStats,
    RootDomains,
    SubDomains,
    TopCves,
    TopCvesShodan,
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


def _ensure_top_cve_sample(shodan_source, today, cve_spec):
    """Insert or refresh a sample top_cves row (idempotent on cve_id + date)."""
    lookup = {"cve_id": cve_spec["cve_id"], "date": today}
    updates = {
        "dynamic_rating": cve_spec["dynamic_rating"],
        "nvd_base_score": cve_spec["nvd_base_score"],
        "summary": cve_spec["summary"],
        "data_source_uid": shodan_source,
    }
    row = TopCves.objects.filter(**lookup).first()
    if row is None:
        try:
            TopCves.objects.create(
                top_cves_uid=uuid.uuid4(),
                **lookup,
                **updates,
            )
        except IntegrityError:
            TopCves.objects.filter(**lookup).update(**updates)
        return
    TopCves.objects.filter(pk=row.pk).update(**updates)


def _ensure_top_cves_shodan_sample(shodan_source, today, cve_spec):
    """Insert or refresh a sample top_cves_shodan row (idempotent on cve_id + date)."""
    lookup = {"cve_id": cve_spec["cve_id"], "collection_date": today}
    updates = {
        "epss_score": cve_spec["epss_score"],
        "nvd_base_score": cve_spec["nvd_base_score"],
        "summary": cve_spec["summary"],
        "data_source_uid": shodan_source,
    }
    row = TopCvesShodan.objects.filter(**lookup).first()
    if row is None:
        try:
            TopCvesShodan.objects.create(
                top_cves_shodan_uid=uuid.uuid4(),
                **lookup,
                **updates,
            )
        except IntegrityError:
            TopCvesShodan.objects.filter(**lookup).update(**updates)
        return
    TopCvesShodan.objects.filter(pk=row.pk).update(**updates)


def _ensure_flare_event_type(event_type, definition):
    """Insert or refresh a flare_event_types row."""
    row = FlareEventTypes.objects.filter(event_type=event_type).first()
    if row is None:
        FlareEventTypes.objects.create(
            flare_event_type_uid=uuid.uuid4(),
            event_type=event_type,
            definition=definition,
            used_in_report=True,
        )
        return
    FlareEventTypes.objects.filter(pk=row.pk).update(
        definition=definition,
        used_in_report=True,
    )


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
    """Insert data sources, orgs, domains, and Shodan test IPs for local dev."""
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
    for cve_spec in (
        {
            "cve_id": "CVE-2024-3400",
            "epss_score": "0.91",
            "dynamic_rating": "0.91",
            "nvd_base_score": "10.0",
            "summary": "Sample high-EPSS CVE for local dark-web report tables.",
        },
        {
            "cve_id": "CVE-2023-4966",
            "epss_score": "0.72",
            "dynamic_rating": "0.72",
            "nvd_base_score": "9.4",
            "summary": "Sample CVE row for top_cves_shodan local report data.",
        },
    ):
        _ensure_top_cve_sample(shodan_source, today, cve_spec)
        _ensure_top_cves_shodan_sample(shodan_source, today, cve_spec)

    for event_type, definition in (
        ("chat_message", "Dark web or forum chat message mentioning the organization."),
        ("forum_post", "Forum post discussing the organization or its assets."),
        ("listing", "Marketplace or dark-web listing related to the organization."),
        ("stealer_log", "Stealer log offering credentials or access."),
        ("leaked_credential", "Leaked credential associated with the organization."),
        ("domain", "Domain-related alert for an organizational asset."),
        ("bot", "Botnet or automated activity involving organizational assets."),
    ):
        _ensure_flare_event_type(event_type, definition)

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

    # Create domain alert sample data
    org_inst = Organizations.objects.get(cyhy_db_name="DHS")
    root_inst = RootDomains.objects.get(
        root_domain="google.com", organizations_uid=org_inst.organizations_uid
    )
    sub_inst = SubDomains.objects.get(
        sub_domain="dns.google", root_domain_uid=root_inst.root_domain_uid
    )
    data_src_inst = DataSource.objects.get(name="DNSMonitor")
    dom_alert_obj, created = DomainAlerts.objects.update_or_create(
        organizations_uid=org_inst,
        message="The tracked domain dhs.gov has a new dnsA record, 12.345.678.910",
        date="2026-07-12",
        defaults={
            "sub_domain_uid": sub_inst,
            "data_source_uid": data_src_inst,
            "alert_type": "New Variant Record",
            "previous_value": "",
            "new_value": "12.345.678.910",
        },
    )

    # Create report summary stats table data
    rss_obj, created = ReportSummaryStats.objects.update_or_create(
        organizations_uid=org_inst,
        start_date="2026-06-01",
        end_date="2026-06-15",
        defaults={
            "ip_count": 0,
            "root_count": 0,
            "sub_count": 0,
            "ports_count": 0,
            "creds_count": 0,
            "breach_count": 0,
            "cred_password_count": 0,
            "domain_alert_count": 0,
            "suspected_domain_count": 0,
            "insecure_port_count": 0,
            "verified_vuln_count": 0,
            "suspected_vuln_count": 0,
            "suspected_vuln_addrs_count": 0,
            "threat_actor_count": 0,
            "dark_web_alerts_count": 0,
            "dark_web_mentions_count": 0,
            "dark_web_executive_alerts_count": 0,
            "pe_number_score": "NA",
            "pe_letter_grade": "NA",
            "pe_percent_score": 0.5,
            "cidr_count": 0,
            "port_protocol_count": 0,
            "software_count": 0,
            "foreign_ips_count": 0,
        },
    )

    # Create Flare alert (event) data
    flare_src_inst = DataSource.objects.get(name="Flare")
    long_content = "This is a really long content field... " + ("blah " * 6560)
    flare_event_obj, created = FlareEvents.objects.update_or_create(
        organizations_uid=org_inst,
        flare_uid="service/driller_shodan/www.v-consultancy.com/cloudfront/443",
        defaults={
            "event_type": "service",
            "event_date": "2026-07-12",
            "collection_date": "2026-07-14",
            "title": "sample title service event",
            "content": long_content,
            "content_hash": "a33be926d6508158b62aaf126aec1f87b4671462",
            "actor": "test_actor",
            "category": "HTTPS Service",
            "source": "driller_shodan",
            "url": "test_url.com",
            "risk_scores": "{'score': 2}",
            "related_identifiers": ["12345678"],
            "data_source_uid": flare_src_inst,
            "severity": "low",
            "related_identifiers_txt": ["test_ident"],
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
