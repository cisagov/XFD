"""FastAPI endpoints required by the dnstwist scan worker."""

# Standard Python Libraries
from datetime import datetime as dt
import logging
import os
from typing import List
import uuid

# Third-Party Libraries
from dataAPI import schemas
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from home.models import (
    DataSource,
    DNSMonitorDomainMap,
    DomainAlerts,
    DomainPermutations,
    Organizations,
    RootDomains,
    SubDomains,
)

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
    # Extract root domain from input domain
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
    # Look up domain in subdomains table
    sub_domain_results = SubDomains.objects.filter(
        sub_domain=data.domain,
        root_domain_uid__organizations_uid=data.pe_org_uid,
    )
    if not sub_domain_results.exists():
        # If it doesn't exist in subdomains table, check if root domain exists
        findomain_inst = DataSource.objects.get(name="findomain")
        root_results = RootDomains.objects.filter(
            organizations_uid=data.pe_org_uid, root_domain=curr_root
        )
        if not root_results.exists():
            # If root domain doesn't exist, create new record
            RootDomains.objects.create(
                root_domain_uid=uuid.uuid4(),
                organizations_uid=Organizations.objects.get(
                    organizations_uid=data.pe_org_uid
                ),
                root_domain=curr_root,
                data_source_uid=findomain_inst,
                enumerate_subs=False,
            )
        # Retrieve root domain record
        root_inst = RootDomains.objects.get(
            organizations_uid=data.pe_org_uid, root_domain=curr_root
        )
        # Create new subdomain record using root domain uid
        SubDomains.objects.create(
            sub_domain_uid=uuid.uuid4(),
            sub_domain=data.domain,
            root_domain_uid=root_inst,
            data_source_uid=findomain_inst,
            first_seen=curr_date,
            last_seen=curr_date,
            identified=False,
        )
        create_ct += 1
    else:
        # If it already exists in subdomains table, update fields
        SubDomains.objects.filter(
            sub_domain=data.domain,
            root_domain_uid__organizations_uid=data.pe_org_uid,
        ).update(
            last_seen=curr_date,
            identified=False,
        )
        update_ct += 1
    # Log stats
    return (
        f"{create_ct} records created, {update_ct} records updated "
        f"in the sub_domains table for {org_name}"
    )


@api_router.post(
    "/dnsmonitor_mapping_by_date",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.DNSMonitorDomainMapTable],
    tags=["dnsmonitor"],
)
def dnsmonitor_mapping_by_date(
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """Retrieve DNSMonitor domain to organization mapping based on specified date."""
    del tokens
    latest_date = DNSMonitorDomainMap.objects.aggregate(Max("date"))[
        "date__max"
    ].strftime("%Y-%m-%d")
    rows = list(
        DNSMonitorDomainMap.objects.filter(
            date=latest_date,
        ).values()
    )
    for row in rows:
        row["dnsmonitor_domain_map_uid"] = convert_uuid_to_string(
            row["dnsmonitor_domain_map_uid"]
        )
        row["date"] = convert_date_to_string(row["date"])
    return rows


@api_router.put(
    "/domain_permu_insert",
    dependencies=[Depends(verify_api_key)],
    tags=["dnsmonitor"],
)
def domain_permu_insert(
    data: schemas.DomainPermuInsertInput,
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """Insert multiple DNSMonitor records into the domain_permutations table through the API."""
    del tokens
    create_ct = 0
    update_ct = 0
    try:
        # Iterate over each record to insert
        for record in data.insert_data:
            record_dict = dict(record)
            # Fetch related instances
            try:
                curr_org_inst = Organizations.objects.get(
                    organizations_uid=record_dict["organizations_uid"]
                )
                curr_source_inst = DataSource.objects.get(
                    data_source_uid=record_dict["data_source_uid"]
                )
                curr_subdomain_inst = SubDomains.objects.get(
                    sub_domain_uid=record_dict["sub_domain_uid"]
                )
            except ObjectDoesNotExist as error:
                LOGGER.error(
                    "Error fetching related instances for record: %s, Error: %s",
                    record_dict,
                    error,
                )
                continue
            # Check if the record already exists in DomainPermutations
            try:
                DomainPermutations.objects.get(
                    organizations_uid=curr_org_inst,
                    domain_permutation=record_dict["domain_permutation"],
                )
                # If it does, update existing record
                DomainPermutations.objects.filter(
                    organizations_uid=curr_org_inst,
                    domain_permutation=record_dict["domain_permutation"],
                ).update(
                    ipv4=record_dict["ipv4"],
                    ipv6=record_dict["ipv6"],
                    date_observed=record_dict["date_observed"],
                    mail_server=record_dict["mail_server"],
                    name_server=record_dict["name_server"],
                    sub_domain_uid=curr_subdomain_inst,
                    data_source_uid=curr_source_inst,
                )
                update_ct += 1
            except DomainPermutations.DoesNotExist:
                # If it doesn't, Create a new record
                DomainPermutations.objects.create(
                    organizations_uid=curr_org_inst,
                    domain_permutation=record_dict["domain_permutation"],
                    ipv4=record_dict["ipv4"],
                    ipv6=record_dict["ipv6"],
                    date_observed=record_dict["date_observed"],
                    mail_server=record_dict["mail_server"],
                    name_server=record_dict["name_server"],
                    sub_domain_uid=curr_subdomain_inst,
                    data_source_uid=curr_source_inst,
                )
                create_ct += 1
        # Log completion and return
        LOGGER.info(
            "Completed data insertion for domain_permutations. Created: %d, Updated: %d",
            create_ct,
            update_ct,
        )
        return f"New DNSMonitor domain_permutations data: {create_ct} created, {update_ct} updated."
    except Exception as error:
        LOGGER.error("Error inserting into domain_permutations table: %s", error)
        return f"Error inserting into domain_permutations table: {error}"


@api_router.put(
    "/domain_alerts_insert",
    dependencies=[Depends(verify_api_key)],
    tags=["dnsmonitor"],
)
def domain_alerts_insert(
    data: schemas.DomainAlertsInsertInput,
    tokens: str = Depends(verify_api_key),  # noqa: B008
):
    """Insert multiple DNSMonitor records into the domain_alerts table through the API."""
    del tokens
    try:
        # Iterate over each record to insert
        create_ct = 0
        for record in data.insert_data:
            record_dict = dict(record)
            # Fetch related instances
            try:
                curr_org_inst = Organizations.objects.get(
                    organizations_uid=record_dict["organizations_uid"]
                )
                curr_sub_inst = SubDomains.objects.get(
                    sub_domain_uid=record_dict["sub_domain_uid"]
                )
                curr_source_inst = DataSource.objects.get(
                    data_source_uid=record_dict["data_source_uid"]
                )
            except ObjectDoesNotExist as error:
                LOGGER.error(
                    "Error fetching related instances for record: %s, Error: %s",
                    record_dict,
                    error,
                )
                continue
            # Check if the record already exists in DomainPermutations
            try:
                DomainAlerts.objects.get(
                    alert_type=record_dict["alert_type"],
                    sub_domain_uid=record_dict["sub_domain_uid"],
                    date=record_dict["date"],
                    new_value=record_dict["new_value"],
                )
                # If record already exists, do nothing
            except DomainAlerts.DoesNotExist:
                # Otherwise, create new record
                DomainAlerts.objects.create(
                    domain_alert_uid=uuid.uuid4(),
                    organizations_uid=curr_org_inst,
                    sub_domain_uid=curr_sub_inst,
                    data_source_uid=curr_source_inst,
                    alert_type=record_dict["alert_type"],
                    message=record_dict["message"],
                    previous_value=record_dict["previous_value"],
                    new_value=record_dict["new_value"],
                    date=record_dict["date"],
                )
                create_ct += 1
        # Log completion and return
        LOGGER.info(
            "Completed data insertion for domain_alerts. Created: %d", create_ct
        )
        return f"New DNSMonitor domain_alerts data: {create_ct} created."
    except Exception as error:
        LOGGER.error("Error inserting into domain_alerts table: %s", error)
        return f"Error inserting into domain_alerts table: {error}"
