"""Sample PE data for local dnstwist development."""

# Standard Python Libraries
from datetime import date
import uuid

# Third-Party Libraries
from django.db import transaction
from home.models import DataSource, Organizations, RootDomains

DNSMONITOR_SOURCE_UID = uuid.uuid4
DNSTWIST_SOURCE_UID = uuid.uuid4
FINDOMAIN_SOURCE_UID = uuid.uuid4
FLARE_SOURCE_UID = uuid.uuid4
DHS_ORG_UID = uuid.uuid4
DHS_CISA_ORG_UID = uuid.uuid4
DHS_ROOT_UID = uuid.uuid4
CISA_ROOT_UID = uuid.uuid4

SAMPLE_ORGS = (
    {
        "organizations_uid": DHS_ORG_UID,
        "name": "Department of Homeland Security (DHS)",
        "cyhy_db_name": "DHS",
        "report_on": True,
        "root_domain": "dhs.gov",
        "root_domain_uid": DHS_ROOT_UID,
    },
    {
        "organizations_uid": DHS_CISA_ORG_UID,
        "name": "Cybersecurity and Infrastructure Security Agency (CISA)",
        "cyhy_db_name": "DHS_CISA",
        "report_on": True,
        "root_domain": "cisa.gov",
        "root_domain_uid": CISA_ROOT_UID,
    },
)


def _new_uuid(uid_factory):
    """Instantiate a UUID from a uuid.uuid4 factory."""
    return uid_factory()


def _ensure_data_source(name, source_uid_factory, description):
    """Create or refresh a data source without changing an existing primary key."""
    today = date.today()
    source, created = DataSource.objects.get_or_create(
        name=name,
        defaults={
            "data_source_uid": _new_uuid(source_uid_factory),
            "description": description,
            "last_run": today,
        },
    )
    if not created:
        DataSource.objects.filter(name=name).update(
            description=description,
            last_run=today,
        )
        source = DataSource.objects.get(name=name)
    return source


def _ensure_org(org_spec):
    """Create or refresh a sample org without changing an existing organizations_uid."""
    cyhy_db_name = org_spec["cyhy_db_name"]
    org, created = Organizations.objects.get_or_create(
        cyhy_db_name=cyhy_db_name,
        defaults={
            "organizations_uid": _new_uuid(org_spec["organizations_uid"]),
            "name": org_spec["name"],
            "report_on": org_spec["report_on"],
        },
    )
    if not created:
        Organizations.objects.filter(cyhy_db_name=cyhy_db_name).update(
            name=org_spec["name"],
            report_on=org_spec["report_on"],
        )
        org = Organizations.objects.get(cyhy_db_name=cyhy_db_name)
    return org


@transaction.atomic
def populate_sample_data():
    """Insert data sources, orgs, and root domains for local PE scans (dnstwist, flare_events, ...)."""
    dnsmonitor_source = _ensure_data_source(
        "DNSMonitor",
        DNSMONITOR_SOURCE_UID,
        "DNSMonitor domain alerts scan",
    )
    dnstwist_source = _ensure_data_source(
        "DNSTwist",
        DNSTWIST_SOURCE_UID,
        "DNSTwist domain permutation scan",
    )
    findomain_source = _ensure_data_source(
        "findomain",
        FINDOMAIN_SOURCE_UID,
        "findomain subdomain enumeration",
    )
    flare_source = _ensure_data_source(
        "Flare",
        FLARE_SOURCE_UID,
        "Flare dark web monitoring",
    )

    org_names = []
    for org_spec in SAMPLE_ORGS:
        root_domain = org_spec["root_domain"]
        root_domain_uid = org_spec["root_domain_uid"]
        org = _ensure_org(org_spec)
        org_names.append(org_spec["cyhy_db_name"])
        _, created = RootDomains.objects.get_or_create(
            organizations_uid=org,
            root_domain=root_domain,
            defaults={
                "root_domain_uid": _new_uuid(root_domain_uid),
                "data_source_uid": findomain_source,
                "enumerate_subs": True,
            },
        )
        if not created:
            RootDomains.objects.filter(
                organizations_uid=org,
                root_domain=root_domain,
            ).update(
                data_source_uid=findomain_source,
                enumerate_subs=True,
            )

    return {
        "data_sources": [
            dnsmonitor_source.name,
            dnstwist_source.name,
            findomain_source.name,
            flare_source.name,
        ],
        "organizations": org_names,
    }
