"""FastAPI endpoints required by the dnstwist scan worker."""

# Standard Python Libraries
from datetime import datetime as dt
from datetime import timedelta
from datetime import timezone as dt_timezone
import logging
import os
from typing import Any, List, Optional, Union
import uuid

# Third-Party Libraries
from dataAPI import schemas
from decouple import config
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from dmz_mini_dl.models import DataSource as MDL_DataSource
from dmz_mini_dl.models import Organization as MDL_Organization
from dmz_mini_dl.models import ShodanAssets as MDL_ShodanAssets
from dmz_mini_dl.models import ShodanVulns as MDL_ShodanVulns
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

# Import api database models
from home.models import (
    DataSource,
    DNSMonitorDomainMap,
    DomainAlerts,
    DomainPermutations,
    Ips,
    Organizations,
    RootDomains,
    ShodanAssets,
    ShodanVulns,
    SubDomains,
    apiUser,
)
from jose import exceptions, jwt
from starlette.status import HTTP_403_FORBIDDEN

LOGGER = logging.getLogger(__name__)
api_router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
ALGORITHM = "HS256"
JWT_SECRET_KEY = config("JWT_SECRET_KEY")  # should be kept secret
JWT_REFRESH_SECRET_KEY = config("JWT_REFRESH_SECRET_KEY")  # should be kept secret

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


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create access token."""
    if expires_delta is not None:
        expires_date = dt.now(dt_timezone.utc) + expires_delta
    else:
        expires_date = dt.now(dt_timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expires_date, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def userapiTokenUpdate(expiredaccessToken, user_refresh, theapiKey, user_id):
    """When api apiKey is expired a new key is created and updated in the database."""
    LOGGER.info(f"The expired access token is {expiredaccessToken}")
    theusername = ""
    user_record = list(User.objects.filter(id=f"{user_id}"))

    # user_record = User.objects.get(id=user_id)

    for u in user_record:
        theusername = u.username
        theuserid = u.id
    LOGGER.info(f"The username is {theusername} with a user of {theuserid}")

    updateapiuseraccessToken = apiUser.objects.get(apiKey=expiredaccessToken)
    # updateapiuserrefreshToken = apiUser.objects.get(refresh_token=expiredrefreshToken)

    updateapiuseraccessToken.apiKey = f"{create_access_token(theusername)}"
    # updateapiuserrefreshToken.refresh_token = f"{create_refresh_token(theusername)}"
    # LOGGER.info(updateapiuseraccessToken.apiKey)

    updateapiuseraccessToken.save(update_fields=["apiKey"])
    # updateapiuserrefreshToken.save(update_fields=['refresh_token'])
    LOGGER.info(
        f"The user api key and refresh token have been updated from: {theapiKey} to: {updateapiuseraccessToken.apiKey}."
    )


def userapiTokenverify(theapiKey):
    """Check to see if api key is expired."""
    tokenRecords = list(apiUser.objects.filter(apiKey=theapiKey))
    LOGGER.info(f"The user provided key is {theapiKey}")
    user_key = ""
    user_refresh = ""
    user_id = ""

    for u in tokenRecords:
        user_refresh = u.refresh_token
        user_key = u.apiKey
        user_id = u.id
    LOGGER.info(f"The user key is {user_key}")
    LOGGER.info(f"The user refresh key is {user_refresh}")
    LOGGER.info(f"the token being verified at verify {theapiKey}")

    try:
        jwt.decode(
            theapiKey,
            config("JWT_REFRESH_SECRET_KEY"),
            algorithms=ALGORITHM,
            options={"verify_signature": False},
        )
        LOGGER.info(f"The api key was alright {theapiKey}")

    except exceptions.JWTError:
        LOGGER.warning("The access token has expired and will be updated")
        userapiTokenUpdate(user_key, user_refresh, theapiKey, user_id)


async def get_api_key(
    # api_key_query: str = Security(api_key_query),
    api_key_header: str = Security(api_key_header),
    # api_key_cookie: str = Security(api_key_cookie),
):
    """Get api key from header."""
    if api_key_header != "":
        return api_key_header

    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )


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


# --- Shodan API endpoints --- #


@api_router.get(
    "/query_shodan_ips/{org_uid}",
    dependencies=[
        Depends(verify_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    # response_model=List[schemas.OrgsReportOnContacts],
    tags=["Get all ips to run through Shodan."],
)
def query_shodan_ips(org_uid: str, tokens: dict = Depends(verify_api_key)):
    """Create API endpoint to get all ips to run through Shodan.."""
    # Check for API key
    LOGGER.info(f"The api key submitted {tokens}")
    if tokens:
        try:
            userapiTokenverify(theapiKey=tokens)
            # If API key valid, make query
            ips_from_cidrs = Ips.objects.filter(
                origin_cidr__organizations_uid=org_uid,
                origin_cidr__isnull=False,
                shodan_results=True,
                current=True,
            ).values_list("ip", flat=True)

            ips_from_subs = Ips.objects.filter(
                ipssubs__sub_domain_uid__root_domain_uid__organizations_uid=org_uid,  # Correct relationship traversal
                shodan_results=True,  # 'shodan_results' is True
                ipssubs__sub_domain_uid__current=True,  # 'current' is True for subdomains
                current=True,  # 'current' is True for Ips
            ).values_list("ip", flat=True)

            # Convert the QuerySet to sets
            in_first = set(ips_from_cidrs)
            in_second = set(ips_from_subs)

            # Find IPs that are in the second query but not in the first
            in_second_but_not_in_first = in_second - in_first

            # Combine the results
            ips = list(ips_from_cidrs) + list(in_second_but_not_in_first)

            return ips
        except ObjectDoesNotExist:
            LOGGER.info("API key expired please try again")
    else:
        return {"message": "No api key was submitted"}


# --- insert_shodan_assets(), Issue 016 atc-framework ---
@api_router.put(
    "/shodan_assets_insert",
    dependencies=[
        Depends(get_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    tags=["Insert Shodan data into the shodan_assets table."],
)
def shodan_assets_insert(
    data: schemas.ShodanAssetsInsertInput, tokens: dict = Depends(get_api_key)
):
    """Insert Shodan data into the shodan_assets table using the API endpoint."""
    # Check for API key
    LOGGER.info(f"The api key submitted {tokens}")
    if tokens:
        try:
            userapiTokenverify(theapiKey=tokens)
            # If API key valid, insert intelx data
            update_create_count = 0
            try:
                mdl_data_source = MDL_DataSource.objects.get(name="Shodan")

            except MDL_DataSource.DoesNotExist:
                LOGGER.warning("DataSource 'Shodan' not found.")
                mdl_data_source = None  # Set to None if DataSource is not found

            for row in data.asset_data:
                row_dict = row.__dict__
                try:
                    org_instance = Organizations.objects.get(
                        organizations_uid=row_dict["organizations_uid"]
                    )

                    acronym = org_instance.cyhy_db_name

                    mdl_org = MDL_Organization.objects.get(acronym=acronym)

                    mdl_asset_fields = {
                        "asn": row_dict.get("asn"),
                        "domains": row_dict.get("domains", []),
                        "hostnames": row_dict.get("hostnames", []),
                        "isp": row_dict.get("isn"),
                        "organization_name": row_dict.get("organization"),
                        "product": row_dict.get("product"),
                        "tags": row_dict.get("tags", []),
                        "country_code": row_dict.get("country_code"),
                        "location": row_dict.get("location"),
                        "data_source": mdl_data_source,
                    }

                    mdl_obj, created = MDL_ShodanAssets.objects.update_or_create(
                        organization=mdl_org,  # Directly use organizations_uid
                        ip=row_dict["ip"],
                        port=row_dict["port"],
                        protocol=row_dict["protocol"],
                        timestamp=timezone.make_aware(
                            parse_datetime(row_dict["timestamp"]), timezone.timezone.utc
                        ),
                        defaults=mdl_asset_fields,
                    )
                except Exception as e:
                    LOGGER.warning(f"Shodan Asset failed to save to MDL: {e}")

                try:
                    asset_fields = {
                        "asn": row_dict.get("asn"),
                        "domains": row_dict.get("domains", []),
                        "hostnames": row_dict.get("hostnames", []),
                        "isn": row_dict.get("isn"),
                        "organization": row_dict.get("organization"),
                        "product": row_dict.get("product"),
                        "tags": row_dict.get("tags", []),
                        "country_code": row_dict.get("country_code"),
                        "location": row_dict.get("location"),
                        "data_source_uid_id": row_dict.get("data_source_uid"),
                    }

                    # Use 'update_or_create' to either create or update the record
                    obj, created = ShodanAssets.objects.update_or_create(
                        organizations_uid=org_instance,  # Directly use organizations_uid
                        ip=row_dict["ip"],
                        port=row_dict["port"],
                        protocol=row_dict["protocol"],
                        timestamp=timezone.make_aware(
                            dt.strptime(row_dict["timestamp"], "%Y-%m-%dT%H:%M:%S.%f"),
                            timezone.timezone.utc,
                        ),
                        defaults=asset_fields,
                    )
                    if created:
                        update_create_count += 1
                except Exception as e:
                    LOGGER.warning(f"Shodan Asset failed to save to PE DB: {e}")
                    continue

            # Return success message
            return {
                "message": f"{update_create_count} records created/updated in the shodan_assets table."
            }
        except ObjectDoesNotExist:
            LOGGER.info("API key expired please try again")
        except Exception as e:
            LOGGER.error(f"Error: {str(e)}")
            return {"message": "An error occurred while processing the request."}
    else:
        return {"message": "No api key was submitted"}


# --- insert_shodan_vulns(), Issue 017 atc-framework ---
@api_router.put(
    "/shodan_vulns_insert",
    dependencies=[
        Depends(get_api_key)
    ],  # Depends(RateLimiter(times=200, seconds=60))],
    tags=["Insert Shodan data into the shodan_vulns table."],
)
def shodan_vulns_insert(
    data: schemas.ShodanVulnsInsertInput, tokens: dict = Depends(get_api_key)
):
    """Insert Shodan data into the shodan_vulns table using the API endpoint."""
    # Check for API key
    LOGGER.info(f"The api key submitted {tokens}")
    if tokens:
        try:
            userapiTokenverify(theapiKey=tokens)
            # If API key valid, insert intelx data
            create_cnt = 0
            try:
                mdl_data_source = MDL_DataSource.objects.get(name="Shodan")
            except DataSource.DoesNotExist:
                LOGGER.warning("DataSource for 'Shodan' not found.")
                mdl_data_source = None  # Set to None if DataSource is not found

            for row in data.vuln_data:
                row_dict = row.__dict__
                try:
                    org_instance = Organizations.objects.get(
                        organizations_uid=row_dict["organizations_uid"]
                    )
                    acronym = org_instance.cyhy_db_name

                    mdl_org = MDL_Organization.objects.get(acronym=acronym)

                    mdl_vuln_data = {
                        "organization_name": row_dict.get("organization"),
                        "cve": row_dict.get("cve"),
                        "severity": row_dict.get("severity"),
                        "cvss": row_dict.get("cvss"),
                        "summary": row_dict.get("summary"),
                        "product": row_dict.get("product"),
                        "attack_vector": row_dict.get("attack_vector"),
                        "av_description": row_dict.get("av_description"),
                        "attack_complexity": row_dict.get("attack_complexity"),
                        "ac_description": row_dict.get("ac_description"),
                        "confidentiality_impact": row_dict.get(
                            "confidentiality_impact"
                        ),
                        "ci_description": row_dict.get("ci_description"),
                        "integrity_impact": row_dict.get("integrity_impact"),
                        "ii_description": row_dict.get("ii_description"),
                        "availability_impact": row_dict.get("availability_impact"),
                        "ai_description": row_dict.get("ai_description"),
                        "tags": row_dict.get("tags"),
                        "domains": row_dict.get("domains"),
                        "hostnames": row_dict.get("hostnames"),
                        "isp": row_dict.get("isn"),
                        "asn": row_dict.get("asn"),
                        "data_source": mdl_data_source,
                        "type": row_dict.get("type"),
                        "name": row_dict.get("name"),
                        "potential_vulns": row_dict.get("potential_vulns"),
                        "mitigation": row_dict.get("mitigation"),
                        "server": row_dict.get("server"),
                        "is_verified": row_dict.get("is_verified"),
                        "banner": row_dict.get("banner"),
                        "version": row_dict.get("version"),
                        "cpe": row_dict.get("cpe"),
                    }

                    mdl_obj, created = MDL_ShodanVulns.objects.update_or_create(
                        organization=mdl_org,  # Directly use organizations_uid
                        ip=row_dict["ip"],
                        port=row_dict["port"],
                        protocol=row_dict["protocol"],
                        timestamp=timezone.make_aware(
                            parse_datetime(row_dict["timestamp"])
                        ),
                        defaults=mdl_vuln_data,
                    )

                except Exception as e:
                    LOGGER.warning(f"Shodan Vuln failed to save to MDL: {e}")

                try:
                    vuln_data = {
                        "organization": row_dict.get("organization"),
                        "cve": row_dict.get("cve"),
                        "severity": row_dict.get("severity"),
                        "cvss": row_dict.get("cvss"),
                        "summary": row_dict.get("summary"),
                        "product": row_dict.get("product"),
                        "attack_vector": row_dict.get("attack_vector"),
                        "av_description": row_dict.get("av_description"),
                        "attack_complexity": row_dict.get("attack_complexity"),
                        "ac_description": row_dict.get("ac_description"),
                        "confidentiality_impact": row_dict.get(
                            "confidentiality_impact"
                        ),
                        "ci_description": row_dict.get("ci_description"),
                        "integrity_impact": row_dict.get("integrity_impact"),
                        "ii_description": row_dict.get("ii_description"),
                        "availability_impact": row_dict.get("availability_impact"),
                        "ai_description": row_dict.get("ai_description"),
                        "tags": row_dict.get("tags"),
                        "domains": row_dict.get("domains"),
                        "hostnames": row_dict.get("hostnames"),
                        "isn": row_dict.get("isn"),
                        "asn": row_dict.get("asn"),
                        "data_source_uid_id": row_dict.get("data_source_uid"),
                        "type": row_dict.get("type"),
                        "name": row_dict.get("name"),
                        "potential_vulns": row_dict.get("potential_vulns"),
                        "mitigation": row_dict.get("mitigation"),
                        "server": row_dict.get("server"),
                        "is_verified": row_dict.get("is_verified"),
                        "banner": row_dict.get("banner"),
                        "version": row_dict.get("version"),
                        "cpe": row_dict.get("cpe"),
                    }

                    obj, created = ShodanVulns.objects.update_or_create(
                        organizations_uid=org_instance,  # Directly use organizations_uid
                        ip=row_dict["ip"],
                        port=row_dict["port"],
                        protocol=row_dict["protocol"],
                        timestamp=timezone.make_aware(
                            dt.strptime(row_dict["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
                        ),
                        defaults=vuln_data,
                    )
                    if created:
                        create_cnt += 1
                except Exception as e:
                    LOGGER.warning(f"Shodan Vuln failed to save to PE DB: {e}")
                    continue
            # Return success message
            return str(create_cnt) + " records created in the shodan vulns table"
        except ObjectDoesNotExist:
            LOGGER.info("API key expired please try again")
    else:
        return {"message": "No api key was submitted"}


# --- get_data_source_uid(), Issue 700 pe-reports ---
# @api_router.post(
#     "/data_source_by_name",
#     dependencies=[
#         Depends(get_api_key)
#     ],  # Depends(RateLimiter(times=200, seconds=60))],
#     response_model=List[schemas.DataSourceFullTable],
#     tags=["Retrieve data for specified data source name."],
# )
# def data_source_by_name(
#     data: schemas.DataSourceByNameInput, tokens: dict = Depends(get_api_key)
# ):
#     """Call API endpoint to get data for specified data source name."""
# Check for API key
# LOGGER.info(f"The api key submitted {tokens}")
# if tokens:
#     try:
#         userapiTokenverify(theapiKey=tokens)
#         # If API key valid, make query
#         data_source_by_name_data = list(
#             DataSource.objects.filter(name=data.name).values()
#         )
#         # also update data source record
#         today = dt.today().strftime("%Y-%m-%d")
#         DataSource.objects.filter(name=data.name).update(last_run=today)
#         # Convert data types to match response model
#         for row in data_source_by_name_data:
#             row["data_source_uid"] = convert_uuid_to_string(row["data_source_uid"])
#             row["last_run"] = convert_date_to_string(row["last_run"])
#         return data_source_by_name_data
#     except ObjectDoesNotExist:
#         LOGGER.info("API key expired please try again")
# else:
#     return {"message": "No api key was submitted"}
