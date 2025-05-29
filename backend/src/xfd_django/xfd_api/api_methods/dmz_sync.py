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
from datetime import datetime
import hashlib
import json
import logging
import os
from typing import Optional

# Third-Party Libraries
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from xfd_mini_dl.models import Mentions, Organization, SixgillAlerts, TopCves

from ..auth import is_global_write_admin

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
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
        LOGGER.warning("User is not a global write admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access."
        )

    try:
        org = Organization.objects.get(acronym=params.acronym)  # <<< ADDED
        LOGGER.info(f"Found organization: {org.acronym} ({org.name})")

    except Organization.DoesNotExist:
        LOGGER.error(f"Organization not found: {params.acronym}")

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{params.acronym}' not found.",
        )

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
                f"Page {params.page} is out of range for {model_cls.__name__}"
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
