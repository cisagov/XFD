"""DmzSync API."""
# Standard Python Libraries
from datetime import datetime
import hashlib
import json
import logging
import os
from typing import List, Optional, Tuple

# Third-Party Libraries
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch, Q
from django.utils.dateparse import parse_datetime
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
) -> Tuple[dict, str]:
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
        org: Optional[Organization],
        since_date: Optional[datetime] = None,
    ) -> Tuple[int, List[dict]]:
        """
        Order by `ordering_field`, then paginate.

        Returns:
            (num_pages, items)
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


# ------------------------
# Cursor helpers
# ------------------------
def encode_cursor(last_seen: datetime, obj_id: str) -> str:
    """Encode cursor as last_seen + id."""
    return f"{last_seen.isoformat()}|{obj_id}"


def decode_cursor(cursor: str) -> Tuple[datetime, str]:
    """Decode cursor string into (last_seen, id)."""
    last_seen_str, obj_id = cursor.split("|")
    last_seen = parse_datetime(last_seen_str)
    return last_seen, obj_id


def dmz_asm_sync(asm_sync_data, current_user):  # pylint: disable=R0915
    """Return ASM asset data using cursor-based pagination for IPs and unlinked subdomains."""
    try:
        # ------------------------
        # Authorization
        # ------------------------
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        data_dict = (
            asm_sync_data.dict() if hasattr(asm_sync_data, "dict") else asm_sync_data
        )
        acronym = data_dict.get("acronym")
        page_size = data_dict.get("page_size") or 25
        cursor_ips = data_dict.get("cursor_ips")
        cursor_loose_subs = data_dict.get("cursor_loose_subs")
        since_date = data_dict.get("since_date")
        if not since_date:
            raise HTTPException(status_code=400, detail="since_date is required.")

        try:
            organization = Organization.objects.get(acronym=acronym)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Organization not found")

        # ------------------------
        # Query IPs with independent cursor
        # ------------------------
        ips_qs = Ip.objects.filter(
            organization=organization, last_seen_timestamp__gt=since_date
        ).order_by("last_seen_timestamp", "id")

        if cursor_ips:
            last_seen_cursor, last_id_cursor = decode_cursor(cursor_ips)
            ips_qs = ips_qs.filter(
                Q(last_seen_timestamp__gt=last_seen_cursor)
                | Q(last_seen_timestamp=last_seen_cursor, id__gt=last_id_cursor)
            )

        ips_subs_prefetch = Prefetch(
            "ipssubs",
            queryset=IpsSubs.objects.filter(
                last_seen__gt=since_date  # Only new/updated links
            ).select_related("sub_domain"),
            to_attr="prefetched_ips_subs",
        )

        ips_qs = ips_qs.prefetch_related(ips_subs_prefetch, "origin_cidr")

        ips_page = list(ips_qs[:page_size])

        # ------------------------
        # Process IPs
        # ------------------------
        ip_results = []
        for ip in ips_page:
            ip_sub_list = []
            for ip_sub in getattr(ip, "prefetched_ips_subs", []):
                sub = getattr(ip_sub, "sub_domain", None)
                if not sub:
                    continue
                ip_sub_list.append(
                    IpsSub(
                        ips_subs_uid=str(getattr(ip_sub, "ips_subs_uid")),
                        link_first_seen=getattr(ip_sub, "first_seen"),
                        link_last_seen=getattr(ip_sub, "last_seen"),
                        link_current=getattr(ip_sub, "current"),
                        sub_domain_uid=str(getattr(sub, "sub_domain_uid")),
                        sub_domain=getattr(sub, "sub_domain"),
                        root_domain_id=str(getattr(sub, "root_domain_id", None)),
                        is_root_domain=getattr(sub, "is_root_domain"),
                        data_source_id=str(getattr(sub, "data_source_id", None)),
                        dns_record_id=getattr(sub, "dns_record_id"),
                        status=getattr(sub, "status"),
                        first_seen=getattr(sub, "first_seen"),
                        last_seen=getattr(sub, "last_seen"),
                        created_at=getattr(sub, "created_at"),
                        updated_at=getattr(sub, "updated_at"),
                        current=getattr(sub, "current"),
                        identified=getattr(sub, "identified"),
                        ip_address=getattr(sub, "ip_address"),
                        synced_at=getattr(sub, "synced_at"),
                        from_root_domain=getattr(sub, "from_root_domain"),
                        enumerate_subs=getattr(sub, "enumerate_subs"),
                        subdomain_source=getattr(sub, "subdomain_source"),
                        ip_only=getattr(sub, "ip_only"),
                        reverse_name=getattr(sub, "reverse_name"),
                        screenshot=getattr(sub, "screenshot"),
                        country=getattr(sub, "country"),
                        asn=getattr(sub, "asn"),
                        cloud_hosted=getattr(sub, "cloud_hosted"),
                        ssl=getattr(sub, "ssl", {}),
                        censys_certificates_results=getattr(
                            sub, "censys_certificates_results", {}
                        ),
                        trustymail_results=getattr(sub, "trustymail_results", {}),
                    ).dict()
                )

            ip_results.append(
                IpInsert(
                    id=str(getattr(ip, "id")),
                    ip_hash=getattr(ip, "ip_hash"),
                    organization_id=str(getattr(ip, "organization_id")),
                    created_timestamp=getattr(ip, "created_timestamp"),
                    updated_timestamp=getattr(ip, "updated_timestamp"),
                    last_seen_timestamp=getattr(ip, "last_seen_timestamp"),
                    ip=getattr(ip, "ip"),
                    ip_version=getattr(ip, "ip_version"),
                    live=getattr(ip, "live"),
                    false_positive=getattr(ip, "false_positive"),
                    retired=getattr(ip, "retired"),
                    last_reverse_lookup=getattr(ip, "last_reverse_lookup"),
                    from_cidr=getattr(ip, "from_cidr"),
                    origin_cidr_network=str(
                        getattr(getattr(ip, "origin_cidr", None), "network", None)
                    ),
                    has_shodan_results=getattr(ip, "has_shodan_results"),
                    current=getattr(ip, "current"),
                    conflict_alerts=json.dumps(getattr(ip, "conflict_alerts", [])),
                    ip_sub_list=ip_sub_list,
                ).dict()
            )

        # ------------------------
        # Query loose subdomains with independent cursor
        # ------------------------
        subs_qs = (
            SubDomains.objects.filter(organization=organization, current=True)
            .exclude(ipssubs__current=True)
            .order_by("last_seen", "id")
        )

        if cursor_loose_subs:
            last_seen_cursor, last_id_cursor = decode_cursor(cursor_loose_subs)
            subs_qs = subs_qs.filter(
                Q(last_seen__gt=last_seen_cursor)
                | Q(last_seen=last_seen_cursor, id__gt=last_id_cursor)
            )

        subs_page = list(subs_qs[:page_size])
        loose_sub_list = []
        for sub in subs_page:
            loose_sub_list.append(
                LooseSub(
                    sub_domain_uid=str(getattr(sub, "sub_domain_uid")),
                    sub_domain=getattr(sub, "sub_domain"),
                    root_domain_id=str(getattr(sub, "root_domain_id", None)),
                    is_root_domain=getattr(sub, "is_root_domain"),
                    data_source_id=str(getattr(sub, "data_source_id", None)),
                    dns_record_id=str(getattr(sub, "dns_record_id", None)),
                    status=getattr(sub, "status"),
                    first_seen=getattr(sub, "first_seen"),
                    last_seen=getattr(sub, "last_seen"),
                    created_at=getattr(sub, "created_at"),
                    updated_at=getattr(sub, "updated_at"),
                    current=getattr(sub, "current"),
                    identified=getattr(sub, "identified"),
                    ip_address=getattr(sub, "ip_address"),
                    synced_at=getattr(sub, "synced_at"),
                    from_root_domain=getattr(sub, "from_root_domain"),
                    enumerate_subs=getattr(sub, "enumerate_subs"),
                    subdomain_source=getattr(sub, "subdomain_source"),
                    ip_only=getattr(sub, "ip_only"),
                    reverse_name=getattr(sub, "reverse_name"),
                    screenshot=getattr(sub, "screenshot"),
                    country=getattr(sub, "country"),
                    asn=getattr(sub, "asn"),
                    cloud_hosted=getattr(sub, "cloud_hosted"),
                    ssl=getattr(sub, "ssl", {}),
                    censys_certificates_results=getattr(
                        sub, "censys_certificates_results", {}
                    ),
                    trustymail_results=getattr(sub, "trustymail_results", {}),
                ).dict()
            )

        # ------------------------
        # Build next cursors and has_more flags
        # ------------------------
        next_cursor_ips = None
        if ips_page and getattr(ips_page[-1], "last_seen_timestamp", None):
            next_cursor_ips = encode_cursor(
                ips_page[-1].last_seen_timestamp, str(ips_page[-1].id)
            )
        has_more_ips = len(ips_page) == page_size

        next_cursor_loose_subs = None
        if subs_page and getattr(subs_page[-1], "last_seen", None):
            next_cursor_loose_subs = encode_cursor(
                subs_page[-1].last_seen, str(subs_page[-1].id)
            )
        has_more_loose_subs = len(subs_page) == page_size

        # ------------------------
        # Return
        # ------------------------
        return {
            "ip_data": ip_results,
            "loose_subs": loose_sub_list,
            "next_cursor_ips": next_cursor_ips,
            "next_cursor_loose_subs": next_cursor_loose_subs,
            "has_more_ips": has_more_ips,
            "has_more_loose_subs": has_more_loose_subs,
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        LOGGER.error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# POST: /dmz_sync/shodan_sync
def dmz_shodan_sync(shodan_data, current_user):
    """Return Shodan assets and vulns using cursor-based pagination."""
    try:
        # ------------------------
        # Authorization
        # ------------------------
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        data = shodan_data.dict() if hasattr(shodan_data, "dict") else shodan_data
        acronym = data.get("acronym")
        page_size = data.get("page_size") or 25
        since_date = data.get("since_date")
        cursor_assets = data.get("cursor_assets")
        cursor_vulns = data.get("cursor_vulns")

        if not since_date:
            raise HTTPException(status_code=400, detail="since_date is required.")

        try:
            organization = Organization.objects.get(acronym=acronym)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Organization not found")

        # ------------------------
        # Query ShodanAssets
        # ------------------------
        assets_qs = ShodanAssets.objects.filter(organization=organization)
        if since_date:
            assets_qs = assets_qs.filter(timestamp__gte=since_date)
        if cursor_assets:
            last_ts, last_id = decode_cursor(cursor_assets)
            assets_qs = assets_qs.filter(
                Q(timestamp__gt=last_ts)
                | Q(timestamp=last_ts, shodan_asset_uid__gt=last_id)
            )
        assets_qs = assets_qs.order_by("timestamp", "shodan_asset_uid")[:page_size]

        shodan_assets_data = [
            {
                **{
                    field.name: getattr(obj, field.name)
                    for field in obj._meta.get_fields()
                    if field.name not in ["organization", "data_source", "ip"]
                },
                "organization_acronym": obj.organization.acronym
                if obj.organization
                else None,
                "data_source_name": obj.data_source.name if obj.data_source else None,
            }
            for obj in assets_qs
        ]

        # Compute next cursor for assets
        next_cursor_assets = (
            encode_cursor(assets_qs[-1].timestamp, str(assets_qs[-1].shodan_asset_uid))
            if assets_qs
            else None
        )
        has_more_assets = len(assets_qs) == page_size

        # ------------------------
        # Query ShodanVulns
        # ------------------------
        vulns_qs = ShodanVulns.objects.filter(organization=organization)
        if since_date:
            vulns_qs = vulns_qs.filter(timestamp__gte=since_date)
        if cursor_vulns:
            last_ts, last_id = decode_cursor(cursor_vulns)
            vulns_qs = vulns_qs.filter(
                Q(timestamp__gt=last_ts)
                | Q(timestamp=last_ts, shodan_vuln_uid__gt=last_id)
            )
        vulns_qs = vulns_qs.order_by("timestamp", "shodan_vuln_uid")[:page_size]

        shodan_vulns_data = [
            {
                **{
                    field.name: getattr(obj, field.name)
                    for field in obj._meta.get_fields()
                    if field.name not in ["organization", "data_source", "ip"]
                },
                "organization_acronym": obj.organization.acronym
                if obj.organization
                else None,
                "data_source_name": obj.data_source.name if obj.data_source else None,
            }
            for obj in vulns_qs
        ]

        # Compute next cursor for vulns
        next_cursor_vulns = (
            encode_cursor(vulns_qs[-1].timestamp, str(vulns_qs[-1].shodan_vuln_uid))
            if vulns_qs
            else None
        )
        has_more_vulns = len(vulns_qs) == page_size

        # ------------------------
        # Return
        # ------------------------
        return {
            "shodan_assets": shodan_assets_data,
            "shodan_vulns": shodan_vulns_data,
            "next_cursor_assets": next_cursor_assets,
            "next_cursor_vulns": next_cursor_vulns,
            "has_more_assets": has_more_assets,
            "has_more_vulns": has_more_vulns,
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        LOGGER.error("Unexpected error in dmz_shodan_sync: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error in Shodan sync",
        )


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
            for exposure_dict in single_page_exposures:
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
