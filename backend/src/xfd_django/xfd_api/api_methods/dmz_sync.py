"""DmzSync API."""
# Standard Python Libraries
from datetime import datetime
import hashlib
import json
import logging
import os
from typing import Optional

# Third-Party Libraries
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch, Q
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    DataSource,
    Ip,
    IpsSubs,
    Mentions,
    Organization,
    ShodanAssets,
    ShodanVulns,
    SixgillAlerts,
    SubDomains,
    TopCves,
)

from ..auth import is_global_write_admin
from ..schema_models.dmz_sync import (
    CredentialBreach,
    CredentialExposure,
    IpInsert,
    IpsSub,
    LooseSub,
)

LOGGER = logging.getLogger(__name__)

SALT = os.getenv("CHECKSUM_SALT", "default_salt")


# POST: /dmz_sync/sixgill_sync
class CybersixSyncParams(BaseModel):
    """
    Pagination parameters for the CyberSix sync endpoint.

    Attributes:
        page (int): 1-indexed page number to fetch. Must be ≥ 1.
        page_size (int): Number of items to include per page. Must be ≥ 1.
    """

    page: int = Field(1, ge=1, description="Which page to fetch (1-indexed)")
    page_size: int = Field(10, ge=1, description="How many items per page")
    acronym: str = "DHS"
    since_date: Optional[datetime] = None


async def fetch_cybersix_data(
    params: CybersixSyncParams,
    current_user,
) -> tuple[dict, str]:
    """
    Pull paginated slices of each Sixgill table (no date filtering).

    Only global write-admin users may call this.

    Args:
        params: pagination parameters (page, page_size).
        current_user: the authenticated User model instance.

    Raises:
        HTTPException 403 if the user is not a global write-admin.
        HTTPException 500 on any underlying DB errors.

    Returns:
        A tuple of:
          - response_obj (dict): { status: "ok", payload: { total_pages, current_page, data: {...} } }
          - checksum (str): SHA-256 of SALT + deterministic JSON of response_obj.
    """
    # 1️⃣ enforce permissions
    if not is_global_write_admin(current_user):
        LOGGER.warning("User is not a global write admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access."
        )

    try:
        org = Organization.objects.get(acronym=params.acronym)
        LOGGER.info("Found organization: %s (%s)", org.acronym, org.name)
    except Organization.DoesNotExist:
        LOGGER.warning(
            "Organization not found: %s, continuing without org filter",
            params.acronym,
        )
        org = None

    # 2️⃣ helper to paginate any Django model
    def _paginate(
        model_cls,
        ordering_field: str,
        org: Organization | None,
        since_date: datetime | None = None,
    ):
        """
        Order by `ordering_field`, then paginate.

        Returns:
            num_pages (int),
            items (List[dict])
        """
        qs = model_cls.objects.order_by(ordering_field).values()

        # Only filter by org if the model has an org FK field
        if org and hasattr(model_cls, "organization_uid"):
            qs = qs.filter(organization_uid=org)

        if since_date:
            qs = qs.filter(date__gte=since_date)

        paginator = Paginator(qs, params.page_size)

        try:
            page = paginator.page(params.page)
            items = list(page)

        except PageNotAnInteger:
            LOGGER.error("Page number is not an integer")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid page number (not an integer).",
            )
        except EmptyPage:
            LOGGER.warning(
                "Page %s is out of range for %s",
                params.page,
                model_cls.__name__,
            )
            items = []  # return an empty list instead of raising

        return paginator.num_pages, items

    # 3️⃣ pull each table
    try:
        alerts_pages, alerts = _paginate(
            SixgillAlerts, "date", org, since_date=params.since_date
        )

        mentions_pages, mentions = _paginate(
            Mentions, "date", org, since_date=params.since_date
        )

        if params.page == 1:
            topcves_pages, topcves = _paginate(
                TopCves, "date", org=None, since_date=params.since_date
            )
        else:
            topcves_pages, topcves = 1, []

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB error: {e}",
        )

    # 4️⃣ build the payload
    total_pages = max(
        alerts_pages,
        mentions_pages,
        topcves_pages,
    )

    payload = {
        "alerts": alerts,
        "mentions": mentions,
        "topcves": topcves,
        "breaches": [],
        "exposures": [],
        "subdomains": [],
        "total_pages": total_pages,
        "current_page": params.page,
    }

    response_obj = {"status": "ok", "payload": payload}

    # 5️⃣ deterministic JSON + salted checksum
    json_str = json.dumps(
        response_obj, default=str, sort_keys=True, separators=(",", ":")
    )
    checksum = hashlib.sha256((SALT + json_str).encode()).hexdigest()

    return response_obj, checksum


def list_data_sources(current_user):
    """Return all Data Sources."""
    try:
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")
        data_sources = DataSource.objects.values("name", "description", "last_run")
        return list(data_sources)

    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def dmz_asm_sync(asm_sync_data, current_user):
    """Return ASM asset data based on the passed org."""
    try:
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")
        data_dict = (
            asm_sync_data.dict() if hasattr(asm_sync_data, "dict") else asm_sync_data
        )

        acronym = data_dict.get("acronym")
        page_size = data_dict.get("page_size")
        page_num = data_dict.get("page")
        last_seen_after = data_dict.get("since_date")
        if last_seen_after is None:
            raise HTTPException(status_code=400, detail="since_date is required.")
        organization = Organization.objects.get(acronym=acronym)

        # Prefetch IpsSubs for IP-to-Subdomain relationship, apply filter to IpsSubs directly
        ips_subs_prefetch = Prefetch(
            "ipssubs",  # IpsSubs is the through table for IP -> Subdomain relationship
            queryset=IpsSubs.objects.filter(
                last_seen__gt=last_seen_after
            ).select_related(
                "sub_domain"
            ),  # Filter on last_seen
            to_attr="prefetched_ips_subs",
        )

        ips = (
            Ip.objects.filter(
                organization=organization, last_seen_timestamp__gte=last_seen_after
            )
            .order_by("ip")
            .prefetch_related(
                ips_subs_prefetch,  # Prefetch IpsSubs for linking Ips to SubDomains
                "origin_cidr",  # Prefetch the origin CIDR for the IPs
            )
        )

        # Paginate the result
        paginator = Paginator(ips, page_size)
        page = paginator.get_page(page_num)
        ip_page_count = paginator.num_pages
        ip_results = []
        if page_num <= ip_page_count:
            for ip in page:
                ip_dict = ip.__dict__
                ip_sub_list = []
                for ip_sub in ip_dict.get("prefetched_ips_subs"):
                    ip_sub_dict = ip_sub.__dict__
                    sub_dict = ip_sub.sub_domain.__dict__
                    ip_sub_list.append(
                        IpsSub(
                            ips_subs_uid=str(ip_sub_dict.get("ips_subs_uid")),
                            # ip_id: f68d5f74-0380-11f0-8054-0242ac120009
                            # sub_domain_id: f6a500d4-0380-11f0-8054-0242ac120009
                            link_first_seen=ip_sub_dict.get("first_seen"),
                            link_last_seen=ip_sub_dict.get("last_seen"),
                            link_current=ip_sub_dict.get("current"),
                            sub_domain_uid=str(sub_dict.get("sub_domain_uid")),
                            sub_domain=sub_dict.get("sub_domain"),
                            root_domain_id=str(sub_dict.get("root_domain_id")),
                            is_root_domain=sub_dict.get("is_root_domain"),
                            data_source_id=str(sub_dict.get("data_source_id")),
                            dns_record_id=sub_dict.get("dns_record_id"),
                            status=sub_dict.get("status"),
                            first_seen=sub_dict.get("first_seen"),
                            last_seen=sub_dict.get("last_seen"),
                            created_at=sub_dict.get("created_at"),
                            updated_at=sub_dict.get("updated_at"),
                            current=sub_dict.get("current"),
                            identified=sub_dict.get("identified"),
                            ip_address=sub_dict.get("ip_address"),
                            synced_at=sub_dict.get("synced_at"),
                            from_root_domain=sub_dict.get("from_root_domain"),
                            enumerate_subs=sub_dict.get("enumerate_subs"),
                            subdomain_source=sub_dict.get("subdomain_source"),
                            ip_only=sub_dict.get("ip_only"),
                            reverse_name=sub_dict.get("reverse_name"),
                            screenshot=sub_dict.get("screenshot"),
                            country=sub_dict.get("country"),
                            asn=sub_dict.get("asn"),
                            cloud_hosted=sub_dict.get("cloud_hosted"),
                            ssl=sub_dict.get("ssl"),
                            censys_certificates_results=sub_dict.get(
                                "censys_certificates_results"
                            ),
                            trustymail_results=sub_dict.get("trustymail_results"),
                        ).dict()
                    )

                ip_object = IpInsert(
                    id=str(ip_dict.get("id")),
                    ip_hash=ip_dict.get("ip_hash"),
                    organization_id=str(ip_dict.get("organization_id")),  # Not useful,
                    created_timestamp=ip_dict.get("created_timestamp"),
                    updated_timestamp=ip_dict.get("updated_timestamp"),
                    last_seen_timestamp=ip_dict.get("last_seen_timestamp"),
                    ip=ip_dict.get("ip"),
                    ip_version=ip_dict.get("ip_version"),
                    live=ip_dict.get("live"),
                    false_positive=ip_dict.get("false_positive"),
                    retired=ip_dict.get("retired"),
                    last_reverse_lookup=ip_dict.get("last_reverse_lookup"),
                    from_cidr=ip_dict.get("from_cidr"),
                    origin_cidr_network=str(ip.origin_cidr.network)
                    if ip.origin_cidr
                    else None,
                    has_shodan_results=ip_dict.get("has_shodan_results"),
                    current=ip_dict.get("current"),
                    conflict_alerts=json.dumps(ip_dict.get("conflict_alerts")),
                    ip_sub_list=ip_sub_list,
                ).dict()
                ip_results.append(ip_object)

        subdomains_without_current_ip = (
            SubDomains.objects.filter(organization=organization, current=True)
            .exclude(
                ipssubs__current=True  # Exclude subdomains that have a current IP-SubDomain relationship
            )
            .distinct()
            .order_by("sub_domain")
        )

        sub_paginator = Paginator(subdomains_without_current_ip, page_size)
        sub_page = sub_paginator.get_page(page_num)
        sub_page_count = sub_paginator.num_pages
        loose_sub_list = []
        if page_num <= sub_page_count:
            for sub in sub_page:
                sub_dict = sub.__dict__
                loose_sub_list.append(
                    LooseSub(
                        sub_domain_uid=str(sub_dict.get("sub_domain_uid")),
                        sub_domain=sub_dict.get("sub_domain"),
                        root_domain_id=str(sub_dict.get("root_domain_id")),
                        is_root_domain=sub_dict.get("is_root_domain"),
                        data_source_id=str(sub_dict.get("data_source_id")),
                        dns_record_id=str(sub_dict.get("dns_record_id")),
                        status=sub_dict.get("status"),
                        # first_seen = sub_dict.get('first_seen').isoformat() if isinstance(sub_dict.get('first_seen'), datetime) else sub_dict.get('first_seen'),
                        first_seen=sub_dict.get("first_seen"),
                        last_seen=sub_dict.get("last_seen"),
                        created_at=sub_dict.get("created_at"),
                        updated_at=sub_dict.get("updated_at"),
                        current=sub_dict.get("current"),
                        identified=sub_dict.get("identified"),
                        ip_address=sub_dict.get("ip_address"),
                        synced_at=sub_dict.get("synced_at"),
                        from_root_domain=sub_dict.get("from_root_domain"),
                        enumerate_subs=sub_dict.get("enumerate_subs"),
                        subdomain_source=sub_dict.get("subdomain_source"),
                        ip_only=sub_dict.get("ip_only"),
                        reverse_name=sub_dict.get("reverse_name"),
                        screenshot=sub_dict.get("screenshot"),
                        country=sub_dict.get("country"),
                        asn=sub_dict.get("asn"),
                        cloud_hosted=sub_dict.get("cloud_hosted"),
                        ssl=sub_dict.get("ssl"),
                        censys_certificates_results=sub_dict.get(
                            "censys_certificates_results"
                        ),
                        trustymail_results=sub_dict.get("trustymail_results"),
                    ).dict()
                )
        return {
            "total_pages": max(ip_page_count, sub_page_count),
            "current_page": page_num,
            "ip_data": ip_results,
            "loose_subs": loose_sub_list,
        }

    except HTTPException as http_exc:
        raise http_exc
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Parent organization not found")
    except Exception as e:
        LOGGER.error(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /dmz_sync/shodan_sync
def dmz_shodan_sync(shodan_data, current_user):
    """Return ASM asset data based on the passed org."""

    def serialize_page_objects(objects):
        return [
            {
                **{
                    field.name: getattr(obj, field.name)
                    for field in obj._meta.get_fields()
                    if field.name
                    not in [
                        "organization",
                        "data_source",
                        "ip",
                    ]  # Exclude all relationships since these will need to be reconnected
                },
                "organization_acronym": obj.organization.acronym
                if obj.organization
                else None,
                "data_source_name": obj.data_source.name if obj.data_source else None,
            }
            for obj in objects
        ]

    def get_paginated_queryset(
        model_cls,
        org_acronym,
        timestamp_field,
        since_date,
        page_size,
        page_num,
        ordering_field,
    ):  # pylint: disable=R0913
        queryset = model_cls.objects.filter(organization__acronym=org_acronym)

        if since_date:
            queryset = queryset.filter(
                Q(**{"{}__gte".format(timestamp_field): since_date})
            )

        queryset = queryset.order_by(ordering_field)
        paginator = Paginator(queryset, page_size)

        try:
            page = paginator.page(page_num)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = []
        return paginator, page

    try:
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        data = shodan_data.dict() if hasattr(shodan_data, "dict") else shodan_data
        acronym = data.get("acronym")
        page_size = data.get("page_size")
        page_num = data.get("page")
        since_date = data.get("since_date")

        if not since_date:
            raise HTTPException(status_code=400, detail="since_date is required.")

        try:
            organization = Organization.objects.get(acronym=acronym)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Parent organization not found")

        # ShodanAssets
        asset_paginator, asset_page = get_paginated_queryset(
            ShodanAssets,
            organization.acronym,
            "timestamp",
            since_date,
            page_size,
            page_num,
            "shodan_asset_uid",
        )
        shodan_assets_data = (
            serialize_page_objects(asset_page.object_list) if asset_page else []
        )

        # ShodanVulns
        vuln_paginator, vuln_page = get_paginated_queryset(
            ShodanVulns,
            organization.acronym,
            "timestamp",
            since_date,
            page_size,
            page_num,
            "shodan_vuln_uid",
        )
        shodan_vulns_data = (
            serialize_page_objects(vuln_page.object_list) if vuln_page else []
        )

        return {
            "total_pages": max(asset_paginator.num_pages, vuln_paginator.num_pages),
            "current_page": page_num,
            "data": {
                "shodan_assets": shodan_assets_data,
                "shodan_vulns": shodan_vulns_data,
            },
        }

    except HTTPException as http_exc:
        raise http_exc
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found")
    except Exception as e:
        # TODO: CRASM-2568 - Create a unified logger in python backend
        LOGGER.error("Unexpected error in dmz_shodan_sync: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /dmz_sync/censys_sync
def dmz_censys_sync(censys_data, current_user):
    """Return ASM asset data based on the passed org."""
    try:
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        data = censys_data.dict() if hasattr(censys_data, "dict") else censys_data
        acronym = data.get("acronym")
        page_size = data.get("page_size")
        page_num = data.get("page")
        since_date = data.get("since_date")

        if not since_date:
            raise HTTPException(status_code=400, detail="since_date is required.")

        try:
            org = Organization.objects.get(acronym=acronym)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Organization not found")

        queryset = SubDomains.objects.filter(
            organization=org, subdomain_source="censys", last_seen__gte=since_date
        ).order_by("sub_domain")
        paginator = Paginator(queryset, page_size)

        try:
            page = paginator.page(page_num)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = []

        page_data = [
            {
                "sub_domain_uid": obj.sub_domain_uid,
                "created_at": obj.created_at,
                "last_seen": obj.last_seen,
                "sub_domain": obj.sub_domain,
                "from_root_domain": obj.from_root_domain,
                "current": obj.current,
                "enumerate_subs": obj.enumerate_subs,
                "identified": obj.identified,
                "subdomain_source": obj.subdomain_source,
                "organization_acronym": obj.organization.acronym
                if obj.organization
                else None,
                "data_source_name": obj.data_source.name if obj.data_source else None,
            }
            for obj in page
        ]

        return {
            "total_pages": paginator.num_pages,
            "current_page": page_num,
            "data": {"censys_subdomains": page_data},
        }

    except HTTPException:
        raise
    except Exception as e:
        # TODO: CRASM-2568 - Create a unified logger in python backend
        LOGGER.error("Unexpected error in dmz_censys_sync: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def dmz_cred_sync(cred_sync_data, current_user):
    """Return ASM asset data based on the passed org."""
    try:
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")
        data_dict = (
            cred_sync_data.dict() if hasattr(cred_sync_data, "dict") else cred_sync_data
        )

        acronym = data_dict.get("acronym")
        page_size = data_dict.get("page_size")
        page_num = data_dict.get("page")
        last_seen_after = data_dict.get("since_date")
        if last_seen_after is None:
            raise HTTPException(status_code=400, detail="since_date is required.")

        cred_exposures = CredentialExposures.objects.filter(
            organization__acronym=acronym
        ).values(
            "credential_exposures_uid",
            "email",
            "root_domain",
            "sub_domain_string",
            "breach_name",
            "modified_date",
            "created_at",
            "name",
            "login_id",
            "phone",
            "password",
            "hash_type",
            "intelx_system_id",
            "data_source__name",
        )

        if last_seen_after is not None:
            cred_exposures = cred_exposures.filter(
                Q(modified_date__gte=last_seen_after)
            )

        cred_exposures = cred_exposures.order_by("credential_exposures_uid")
        paged_cred_exposures = Paginator(cred_exposures, page_size)

        # Pagination for Credential Exposures
        try:
            single_page_exposures = paged_cred_exposures.page(page_num)
        except PageNotAnInteger:
            single_page_exposures = paged_cred_exposures.page(1)
        except EmptyPage:
            single_page_exposures = []
        except Exception:
            single_page_exposures = []

        # Get the list of Credential Exposures for the current page
        exposure_list = []
        breach_set = set()
        if single_page_exposures:
            # cred_exposures_page_data = single_page_exposures.object_list
            for exposure_dict in single_page_exposures:
                # exposure_dict = exposure_dict.__dict__
                exposure_list.append(
                    CredentialExposure(
                        credential_exposures_uid=str(
                            exposure_dict.get("credential_exposures_uid")
                        ),
                        email=exposure_dict.get("email"),
                        root_domain=exposure_dict.get("root_domain"),
                        sub_domain_string=exposure_dict.get("sub_domain_string"),
                        breach_name=exposure_dict.get("breach_name"),
                        modified_date=exposure_dict.get("modified_date"),
                        created_at=exposure_dict.get("created_at"),
                        name=exposure_dict.get("name"),
                        login_id=exposure_dict.get("login_id"),
                        phone=exposure_dict.get("phone"),
                        password=exposure_dict.get("password"),
                        hash_type=exposure_dict.get("hash_type"),
                        intelx_system_id=exposure_dict.get("intelx_system_id"),
                        organization_acronym=acronym,
                        data_source_name=exposure_dict.get("data_source__name"),
                    ).dict()
                )
                breach_set.add(exposure_dict.get("breach_name"))
        else:
            exposure_list = []

        if len(breach_set) != 0:
            breaches = CredentialBreaches.objects.filter(
                breach_name__in=list(breach_set)
            ).values(
                "credential_breaches_uid",
                "breach_name",
                "description",
                "exposed_cred_count",
                "breach_date",
                "added_date",
                "modified_date",
                "data_classes",
                "password_included",
                "is_verified",
                "is_fabricated",
                "is_sensitive",
                "is_retired",
                "is_spam_list",
                "data_source__name",
            )

            breach_dicts = []
            for breach in breaches:
                breach_dicts.append(
                    CredentialBreach(
                        credential_breaches_uid=str(
                            breach.get("credential_breaches_uid")
                        ),
                        breach_name=breach.get("breach_name"),
                        description=breach.get("description"),
                        exposed_cred_count=breach.get("exposed_cred_count"),
                        breach_date=breach.get("breach_date"),
                        added_date=breach.get("added_date"),
                        modified_date=breach.get("modified_date"),
                        data_classes=breach.get("data_classes"),
                        password_included=breach.get("password_included"),
                        is_verified=breach.get("is_verified"),
                        is_fabricated=breach.get("is_fabricated"),
                        is_sensitive=breach.get("is_sensitive"),
                        is_retired=breach.get("is_retired"),
                        is_spam_list=breach.get("is_spam_list"),
                        data_source_name=breach.get("data_source__name"),
                    ).dict()
                )
        else:
            breach_dicts = []

        total_pages = paged_cred_exposures.num_pages

        result = {
            "total_pages": total_pages,
            "current_page": page_num,
            "credential_exposures": exposure_list,
            "credential_breaches": breach_dicts,
        }

        return result

    except HTTPException as http_exc:
        raise http_exc
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found")
    except Exception as e:
        LOGGER.error(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
