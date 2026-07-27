"""Sample PE data for local dnstwist development."""

# Standard Python Libraries
from datetime import date
import uuid

# Third-Party Libraries
from django.db import transaction
from home.models import DataSource, Organizations, RootDomains

SAMPLE_ORGS = (
    {
        "name": "Department of Homeland Security (DHS)",
        "cyhy_db_name": "DHS",
        "report_on": True,
        "root_domain": "dhs.gov",
    },
    {
        "name": "Cybersecurity and Infrastructure Security Agency (CISA)",
        "cyhy_db_name": "DHS_CISA",
        "report_on": True,
        "root_domain": "cisa.gov",
    },
)


@transaction.atomic
def populate_sample_data():
    """Insert data sources, orgs, and root domains needed to run dnstwist locally."""
    today = date.today()

    def ensure_data_source(name, description):
        source = DataSource.objects.filter(name=name).first()
        if source is None:
            return DataSource.objects.create(
                name=name,
                description=description,
                last_run=today,
            )
        source.description = description
        source.last_run = today
        source.save(update_fields=["description", "last_run"])
        return source

    dnsmonitor_source = ensure_data_source(
        "DNSMonitor", "DNSMonitor domain alerts scan"
    )
    dnstwist_source = ensure_data_source("DNSTwist", "DNSTwist domain permutation scan")
    findomain_source = ensure_data_source(
        "findomain", "findomain subdomain enumeration"
    )

    org_names = []
    for org_spec in SAMPLE_ORGS:
        root_domain = org_spec["root_domain"]

        org = Organizations.objects.filter(
            cyhy_db_name=org_spec["cyhy_db_name"]
        ).first()
        if org is None:
            org = Organizations.objects.create(
                organizations_uid=uuid.uuid4(),
                cyhy_db_name=org_spec["cyhy_db_name"],
                name=org_spec["name"],
                report_on=org_spec["report_on"],
            )

        org_names.append(org_spec["cyhy_db_name"])

        root = RootDomains.objects.filter(
            organizations_uid=org,
            root_domain=root_domain,
        ).first()
        if root is None:
            RootDomains.objects.create(
                root_domain_uid=uuid.uuid4(),
                organizations_uid=org,
                root_domain=root_domain,
                data_source_uid=findomain_source,
                enumerate_subs=True,
            )

    return {
        "data_sources": [
            dnsmonitor_source.name,
            dnstwist_source.name,
            findomain_source.name,
        ],
        "organizations": org_names,
    }
