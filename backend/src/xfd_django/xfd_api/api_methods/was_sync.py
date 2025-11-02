"""WAS Sync API Methods."""
# Standard Python Libraries
from datetime import date
import logging
import math
from typing import Iterable, Tuple

# Third-Party Libraries
from django.db.models import QuerySet
from xfd_mini_dl.models import WasFindings, WasScanSummary

LOGGER = logging.getLogger(__name__)

READ_ONLY_FIELDS = (
    "finding_uid",
    "finding_type",
    "webapp_id",
    "was_org_id",
    "owasp_category",
    "severity",
    "times_detected",
    "base_score",
    "temporal_score",
    "fstatus",
    "last_detected",
    "first_detected",
    "is_remediated",
    "potential",
    "webapp_url",
    "webapp_name",
    "name",
    "cvss_v3_attack_vector",
    "cwe_list",
    "wasc_list",
    "last_tested",
    "fixed_date",
    "is_ignored",
    "url",
    "qid",
    "response",
    "cve_id",
    "sub_domain_id",
)


async def get_all_was_scan_summaries(
    page: int, per_page: int
) -> tuple[int, list[WasScanSummary]]:
    """Retrieve paginated WAS scan summaries."""
    qs = WasScanSummary.objects.all().order_by("-start_date")
    total_count = qs.count()
    total_pages = max(1, math.ceil(total_count / per_page))  # <- proper ceil

    offset = (page - 1) * per_page
    records = list(qs[offset : offset + per_page])
    return total_pages, records


def get_was_findings_queryset(since_date: date | None) -> QuerySet:
    """
    Build the base queryset for WAS findings with optional since_date filter.

    Args:
        since_date: If provided, restrict results by first_detected/last_detected >= since_date.

    Returns:
        A Django queryset optimized for read operations.
    """
    queryset = WasFindings.objects.all()
    if since_date:
        queryset = queryset.filter(
            # choose the most restrictive practical filter; adjust per your semantics
            last_detected__gte=since_date
        )
    return queryset.only(*READ_ONLY_FIELDS).order_by("finding_uid")


def paginate_queryset(
    queryset: QuerySet, page: int, per_page: int
) -> Tuple[int, Iterable[WasFindings]]:
    """
    Paginate a queryset.

    Args:
        queryset: The queryset to paginate.
        page: 1-indexed page number.
        per_page: Items per page, validated by the route.

    Returns:
        Tuple of (total_pages, page_records iterable).
    """
    total_count = queryset.count()
    if total_count == 0:
        return 1, []
    total_pages = (total_count + per_page - 1) // per_page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    page_records = queryset[start_index:end_index]
    LOGGER.info(
        "WAS findings page=%s per_page=%s total_pages=%s", page, per_page, total_pages
    )
    return total_pages, page_records
