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


@transaction.atomic
def populate_sample_data():
    """Insert data sources, orgs, and root domains needed to run dnstwist locally."""
    today = date.today()

    dnsmonitor_source, _ = DataSource.objects.update_or_create(
        name="DNSMonitor",
        defaults={
            "data_source_uid": DNSMONITOR_SOURCE_UID,
            "description": "DNSMonitor domain alerts scan",
            "last_run": today,
        },
    )
    dnstwist_source, _ = DataSource.objects.update_or_create(
        name="DNSTwist",
        defaults={
            "data_source_uid": DNSTWIST_SOURCE_UID,
            "description": "DNSTwist domain permutation scan",
            "last_run": today,
        },
    )
    findomain_source, _ = DataSource.objects.update_or_create(
        name="findomain",
        defaults={
            "data_source_uid": FINDOMAIN_SOURCE_UID,
            "description": "findomain subdomain enumeration",
            "last_run": today,
        },
    )
    flare_source, _ = DataSource.objects.update_or_create(
        name="Flare",
        defaults={
            "data_source_uid": FLARE_SOURCE_UID,
            "description": "Flare dark web monitoring",
            "last_run": today,
        },
    )

    org_names = []
    for org_spec in SAMPLE_ORGS:
        root_domain = org_spec["root_domain"]
        root_domain_uid = org_spec["root_domain_uid"]
        org_defaults = {
            key: value
            for key, value in org_spec.items()
            if key not in {"root_domain", "root_domain_uid"}
        }
        Organizations.objects.update_or_create(
            cyhy_db_name=org_spec["cyhy_db_name"],
            defaults=org_defaults,
        )
        org_names.append(org_spec["cyhy_db_name"])
        org = Organizations.objects.get(cyhy_db_name=org_spec["cyhy_db_name"])
        RootDomains.objects.update_or_create(
            organizations_uid=org,
            root_domain=root_domain,
            defaults={
                "root_domain_uid": root_domain_uid,
                "data_source_uid": findomain_source,
                "enumerate_subs": True,
            },
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
