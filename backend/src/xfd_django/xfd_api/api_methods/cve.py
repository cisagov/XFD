"""Cve API."""
# Standard Python Libraries
import datetime
from typing import Optional

# Third-Party Libraries
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from fastapi import HTTPException, status
from xfd_mini_dl.models import Cve as CveModel

from ..auth import is_global_write_admin


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
