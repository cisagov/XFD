"""DmzSync API."""
import json
import hashlib
from datetime import timedelta
from typing import Dict, Any

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from asgiref.sync import sync_to_async
from fastapi import HTTPException, status

from pydantic import BaseModel, Field
from xfd_api.helpers.date_time_helpers import calculate_days_back
from xfd_mini_dl.models import (
    SixgillAlerts,
    Mentions,
    CredentialBreaches,
    SubDomains,
    CredentialExposures,
    TopCves,
)


SALT = settings.CHECKSUM_SALT

# POST: /dmz_sync/sixgill_sync
class CybersixSyncParams(BaseModel):
    page: int = Field(..., ge=1, description="Which page to fetch (1-indexed)")
    page_size: int = Field(..., ge=1, description="How many items per page")


async def fetch_cybersix_data(params: CybersixSyncParams):
    """
    Pull paginated slices of each Sixgill table (no date filtering).
    Returns (response_obj: dict, checksum: str)
    """

    def _paginate(model_cls, ordering_field: str):
        """
        Order by `ordering_field`, then paginate.
        Returns: (num_pages, list_of_dicts)
        """
        qs = model_cls.objects.order_by(ordering_field).values()
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

    try:
        alerts_pages, alerts = _paginate(SixgillAlerts,     "date")
        mentions_pages, mentions = _paginate(Mentions,      "date")
        breaches_pages, breaches = _paginate(CredentialBreaches, "added_date")
        subs_pages, subs = _paginate(SubDomains,            "first_seen")
        expo_pages, exposures = _paginate(CredentialExposures, "created_at")
        topcves_pages, topcves = _paginate(TopCves,         "date")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB error: {}".format(e),
        )

    total_pages = max(
        alerts_pages,
        mentions_pages,
        breaches_pages,
        subs_pages,
        expo_pages,
        topcves_pages,
    )

    payload = {
        "total_pages": total_pages,
        "current_page": params.page,
        "data": {
            "alerts": alerts,
            "mentions": mentions,
            "breaches": breaches,
            "subdomains": subs,
            "exposures": exposures,
            "topcves": topcves,
        },
    }
    response_obj = {"status": "ok", "payload": payload}

    # deterministic JSON + checksum
    json_str = json.dumps(response_obj, default=str, sort_keys=True)
    checksum = hashlib.sha256((SALT + json_str).encode()).hexdigest()

    return response_obj, checksum