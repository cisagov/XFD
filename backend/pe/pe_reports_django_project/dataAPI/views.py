"""FastAPI endpoints required by the dnstwist scan worker."""

# Standard Python Libraries
from datetime import datetime as dt
import logging
import os
from typing import List

# Third-Party Libraries
from dataAPI import schemas
from django.db.models import Q
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from home.models import DataSource, Organizations, RootDomains, SubDomains

LOGGER = logging.getLogger(__name__)
api_router = APIRouter()

API_KEY_NAME = "access_token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def convert_uuid_to_string(value):
    """Serialize a UUID value as a string for API responses."""
    if value is not None:
        return str(value)
    return value


def convert_date_to_string(value):
    """Serialize a date value as YYYY-MM-DD for API responses."""
    if value is not None:
        return value.strftime("%Y-%m-%d")
    return value


def verify_api_key(api_key: str = Security(api_key_header)) -> str:  # noqa: B008
    """Validate the PE API access token header."""
    expected = os.environ.get("PE_API_KEY", "")
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return api_key


@api_router.get("/health", tags=["health"])
def health():
    """Return a simple health check payload."""
    return {"status": "ok"}


@api_router.get(
    "/organizations_demo_or_report_on",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.OrganizationsFullTable],
    tags=["organizations"],
)
def organizations_demo_or_report_on(
    tokens: str = Depends(verify_api_key),
):  # noqa: B008
    """List organizations flagged as demo or report_on."""
    del tokens
    rows = list(Organizations.objects.filter(Q(demo=True) | Q(report_on=True)).values())
    for row in rows:
        row["organizations_uid"] = convert_uuid_to_string(row["organizations_uid"])
        row["org_type_uid"] = convert_uuid_to_string(row.get("org_type_uid"))
        row["parent_org_uid"] = convert_uuid_to_string(row.get("parent_org_uid"))
        row["cyhy_period_start"] = convert_date_to_string(row.get("cyhy_period_start"))
        row["date_first_reported"] = convert_date_to_string(
            row.get("date_first_reported")
        )
    return rows


@api_router.post(
    "/data_source_by_name",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.DataSourceFullTable],
    tags=["data_sources"],
)
def data_source_by_name(
    data: schemas.DataSourceByNameInput,
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """Look up a data source row by name and refresh its last_run date."""
    del tokens
    rows = list(DataSource.objects.filter(name=data.name).values())
    today = dt.today().strftime("%Y-%m-%d")
    DataSource.objects.filter(name=data.name).update(last_run=today)
    for row in rows:
        row["data_source_uid"] = convert_uuid_to_string(row["data_source_uid"])
        row["last_run"] = convert_date_to_string(row.get("last_run"))
    return rows


@api_router.post(
    "/subdomain_uid_by_domain",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.SubdomainUIDByDomain],
    tags=["subdomains"],
)
def subdomain_by_domain(
    data: schemas.SubdomainUIDByDomainInput,
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """Return the sub_domain_uid for a subdomain string."""
    del tokens
    rows = list(
        SubDomains.objects.filter(sub_domain=data.domain).values("sub_domain_uid")
    )
    for row in rows:
        row["sub_domain_uid"] = convert_uuid_to_string(row["sub_domain_uid"])
    return rows


@api_router.post(
    "/rootdomains_by_org_uid",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.RootDomainsTable],
    tags=["root_domains"],
)
def rootdomains_by_org_uid(
    data: schemas.RootdomainsByOrgUIDInput,
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """List root domains for an organization that have enumerate_subs enabled."""
    del tokens
    rows = list(
        RootDomains.objects.filter(
            organizations_uid=data.org_uid,
            enumerate_subs=True,
        ).values()
    )
    for row in rows:
        row["root_domain_uid"] = convert_uuid_to_string(row["root_domain_uid"])
        row["organizations_uid_id"] = convert_uuid_to_string(
            row.get("organizations_uid_id")
        )
        row["data_source_uid_id"] = convert_uuid_to_string(
            row.get("data_source_uid_id")
        )
    return rows


@api_router.put(
    "/sub_domains_single_insert",
    dependencies=[Depends(verify_api_key)],
    tags=["subdomains"],
)
def sub_domains_single_insert(
    data: schemas.SubDomainsSingleInsertInput,
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """Insert or update a sub_domains row for dnstwist and related scans."""
    del tokens
    if data.root:
        curr_root = data.domain
    else:
        curr_root = data.domain.split(".")[-2]
        curr_root = ".".join(curr_root)

    curr_date = dt.today().strftime("%Y-%m-%d")
    org_name = Organizations.objects.filter(organizations_uid=data.pe_org_uid).values(
        "cyhy_db_name"
    )[0]["cyhy_db_name"]
    create_ct = 0
    update_ct = 0

    sub_domain_results = SubDomains.objects.filter(
        sub_domain=data.domain,
        root_domain_uid__organizations_uid=data.pe_org_uid,
    )
    if not sub_domain_results.exists():
        findomain_inst = DataSource.objects.get(name="findomain")
        root_results = RootDomains.objects.filter(
            organizations_uid=data.pe_org_uid, root_domain=curr_root
        )
        if not root_results.exists():
            RootDomains.objects.create(
                organizations_uid=Organizations.objects.get(
                    organizations_uid=data.pe_org_uid
                ),
                root_domain=curr_root,
                data_source_uid=findomain_inst,
                enumerate_subs=False,
            )
        root_inst = RootDomains.objects.get(
            organizations_uid=data.pe_org_uid, root_domain=curr_root
        )
        SubDomains.objects.create(
            sub_domain=data.domain,
            root_domain_uid=root_inst,
            data_source_uid=findomain_inst,
            first_seen=curr_date,
            last_seen=curr_date,
            identified=False,
        )
        create_ct += 1
    else:
        SubDomains.objects.filter(
            sub_domain=data.domain,
            root_domain_uid__organizations_uid=data.pe_org_uid,
        ).update(
            last_seen=curr_date,
            identified=False,
        )
        update_ct += 1

    return (
        f"{create_ct} records created, {update_ct} records updated "
        f"in the sub_domains table for {org_name}"
    )
