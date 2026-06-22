"""Sample PE data for local dnstwist development."""

# Standard Python Libraries
from datetime import date
import uuid

# Third-Party Libraries
from django.db import transaction
from home.models import DataSource, Organizations, RootDomains

DNSTWIST_SOURCE_UID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
FINDOMAIN_SOURCE_UID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DHS_ORG_UID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DHS_CISA_ORG_UID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DHS_ROOT_UID = uuid.UUID("33333333-3333-3333-3333-333333333333")
CISA_ROOT_UID = uuid.UUID("44444444-4444-4444-4444-444444444444")

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
        "data_sources": [dnstwist_source.name, findomain_source.name],
        "organizations": org_names,
    }
