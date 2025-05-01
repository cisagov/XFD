"""
dmz_sync API module.

Defines the `/dmz_sync/cybersix_sync` endpoint and the supporting logic
to paginate and fetch data from the Sixgill tables, bundle it into a
standardized payload, and compute an X-Salted-Checksum for integrity.

Exports:
  - CybersixSyncParams: Pydantic model for page and page_size parameters.
  - fetch_cybersix_data: Async function that retrieves paginated slices of
    alerts, mentions, breaches, subdomains, exposures, and top CVEs.
"""
# Standard Python Libraries
import hashlib
import json

# Third-Party Libraries
from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    Mentions,
    SixgillAlerts,
    SubDomains,
    TopCves,
)

from ..auth import is_global_write_admin
from ..models import Organization

SALT = settings.CHECKSUM_SALT


# POST: /dmz_sync/sixgill_sync
class CybersixSyncParams(BaseModel):
    """
    Pagination parameters for the CyberSix sync endpoint.

    Attributes:
        page (int): 1-indexed page number to fetch. Must be ≥ 1.
        page_size (int): Number of items to include per page. Must be ≥ 1.
    """

    page: int = Field(..., ge=1, description="Which page to fetch (1-indexed)")
    page_size: int = Field(..., ge=1, description="How many items per page")
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access."
        )
    # 2️⃣ helper to paginate any Django model
    def _paginate(model_cls, ordering_field: str, org: Organization, since_timestamp: str | None = None):
        """
        Order by `ordering_field`, then paginate.

        Returns:
            num_pages (int),
            items (List[dict])  -- list of `model_cls.values()` dicts for that page
        """
        qs = model_cls.objects.filter(organization = org).order_by(ordering_field).values()
        if since_timestamp is not None:
            qs = qs.filter(Q(date__gte=since_timestamp))
        paginator = Paginator(qs, params.page_size)
        try:
            page = paginator.page(params.page)
            items = list(page)
        except PageNotAnInteger:
            page = paginator.page(1)
            items = list(page)
        except EmptyPage:
            items = []
        return paginator.num_pages, items

    # 3️⃣ pull each table
    try:
        alerts_pages, alerts = _paginate(SixgillAlerts, "date")
        mentions_pages, mentions = _paginate(Mentions, "date")
        topcves_pages, topcves = _paginate(TopCves, "date")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB error: {e}"
        )

    # 4️⃣ build the payload
    total_pages = max(
        alerts_pages,
        mentions_pages,
        topcves_pages,
    )
    payload = {
        "total_pages": total_pages,
        "current_page": params.page,
        "data": {
            "alerts": alerts,
            "mentions": mentions,

            "topcves": topcves,
        },
    }
    response_obj = {"status": "ok", "payload": payload}

    # 5️⃣ deterministic JSON + salted checksum
    json_str = json.dumps(response_obj, default=str, sort_keys=True)
    checksum = hashlib.sha256((SALT + json_str).encode()).hexdigest()

    return response_obj, checksum
