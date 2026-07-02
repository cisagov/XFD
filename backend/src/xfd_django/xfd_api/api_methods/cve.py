"""Cve API."""
# Standard Python Libraries
import datetime
import logging
from typing import Any, Dict, Optional

# Third-Party Libraries
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from fastapi import HTTPException, status
from xfd_mini_dl.models import Cve as CveModel
from xfd_mini_dl.models import User, UserType

from ..auth import (
    get_org_memberships,
    is_global_view_admin,
    is_global_write_admin,
    is_regional_admin,
)
from ..tasks.es_client import ESClient

LOGGER = logging.getLogger(__name__)


def escape_wildcard_query(search_term: str) -> str:
    """Escape wildcard metacharacters in search term for wildcard queries.

    Only escape backslash, asterisk, and question mark which have special meaning
    in Elasticsearch wildcard queries. Everything else (including dashes) is literal.
    Makes search case-insensitive by converting to uppercase to match stored CVE names.
    """
    # Convert to uppercase to match stored CVE names (CVE-2016-... format)
    search_term = search_term.upper()
    # Escape backslash first to avoid double-escaping
    result = search_term.replace("\\", "\\\\")
    # Escape wildcard characters
    result = result.replace("*", "\\*")
    result = result.replace("?", "\\?")
    return result


def get_cves_by_id(cve_id):
    """
    Get Cve by id.

    Returns:
        object: a single Cve object.
    """
    try:
        cve = CveModel.objects.get(id=cve_id)
        return cve
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_cves_by_name(cve_name):
    """
    Get Cve by name.

    Returns:
        object: a single Cpe object.
    """
    try:
        cve = CveModel.objects.get(name=cve_name)
        return cve
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_cves(
    current_user,
    *,
    page: int = 1,
    per_page: int = 100,
    since_timestamp: Optional[datetime.datetime] = None,
) -> tuple[int, list[CveModel]]:
    """
    Return (total_pages, list_of_CveModel) for the given filters.

    Raise HTTPException(403) if the user is not an admin, or HTTPException(500) on DB errors.
    """
    if not is_global_write_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access.",
        )

    try:
        # 1) base queryset
        qs = CveModel.objects.all()

        # 2) optional date filter
        if since_timestamp is not None:
            qs = qs.filter(Q(modified_at__gte=since_timestamp))

        # 3) deterministic ordering
        qs = qs.order_by("modified_at", "id")

        # 4) paginate
        paginator = Paginator(qs, per_page)
        try:
            page_obj = paginator.page(page)
            objects = list(page_obj.object_list)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            objects = list(page_obj.object_list)
        except EmptyPage:
            objects = []

        return paginator.num_pages, objects

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB error: {e}",
        )


def search_cves_task(search_body, current_user: User):
    """
    Search CVEs in Elasticsearch.

    Args:
        search_body (dict): The search query body.
        current_user: The current user object.

    Returns:
        dict: The CVE search results with Organization IDs from Elasticsearch.
    """
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not (
            is_global_view_admin(current_user) or is_regional_admin(current_user)
        ) and not get_org_memberships(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Initialize Elasticsearch client
        client = ESClient()

        # Construct the Elasticsearch query
        query_body: Dict[str, Any] = {"query": {"bool": {"must": [], "filter": []}}}

        # Use match_all if searchTerm is empty
        if search_body.search_term.strip():
            # Use wildcard query on name.keyword (non-tokenized) to preserve dashes in CVE names
            # Only escape wildcard metacharacters (* and ?), leave dashes and other chars literal
            sanitized_search_term = escape_wildcard_query(search_body.search_term)
            query_body["query"]["bool"]["must"].append(
                {"wildcard": {"name.keyword": "*{}*".format(sanitized_search_term)}}
            )
        else:
            query_body["query"]["bool"]["must"].append({"match_all": {}})

        # For standard users, only show CVEs affecting their organization
        if current_user.user_type == UserType.STANDARD:
            org_ids = get_org_memberships(current_user)
            if not org_ids:
                raise HTTPException(status_code=403, detail="Unauthorized")
            query_body["query"]["bool"]["filter"].append(
                {"terms": {"organization_ids": org_ids}}
            )

        # Log the query for debugging
        LOGGER.info("CVE Search Query: %s", query_body)
        LOGGER.info("Search term: %s", search_body.search_term)

        # Execute the search
        search_results = client.search_cves(query_body)
        LOGGER.info(
            "CVE Search Results: %d hits",
            len(search_results.get("hits", {}).get("hits", [])),
        )

        return {"body": search_results}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        LOGGER.exception("Error occurred while searching CVEs: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
