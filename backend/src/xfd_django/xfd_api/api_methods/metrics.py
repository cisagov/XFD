"""API methods for Admin Metrics dashboard."""
# Standard Python Libraries
from collections import defaultdict
from datetime import timedelta

# Third-Party Libraries
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from fastapi import HTTPException
from xfd_api.auth import is_global_write_admin
from xfd_api.schema_models.metrics import (
    DailyCount,
    DailyStatusCount,
    GetScanDailyStatusCountsResponse,
    ListScansOrgCountByStatusResponse,
    OrgCountByStatus,
    ScanOrgCountByStatus,
)
from xfd_api.schema_models.scan import SCAN_SCHEMA
from xfd_mini_dl.models import Scan, ScanResult

# Default window for metrics in days; used by metrics endpoints in views.py
default_metrics_window = 7


def get_scan_daily_status_counts(scan_id: str, window_days: int, current_user):
    """Get daily HTTP status counts for a specific scan over a given time window."""
    if not is_global_write_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    cutoff = (timezone.now() - timedelta(days=window_days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    result = (
        ScanResult.objects.filter(scan_id=scan_id, scanned_at__gte=cutoff)
        .annotate(date=TruncDate("scanned_at"))
        .values("http_status", "date")
        .annotate(count=Count("id"))
        .order_by("http_status", "date")
    )

    return transform_daily_status_counts(result, scan_id, window_days)


def transform_daily_status_counts(queryset, scan_id, window_days):
    """Transform queryset into a structured response for daily status counts."""
    scan = Scan.objects.get(id=scan_id)
    status_map = defaultdict(list)
    for row in queryset:
        status_map[row["http_status"]].append(
            DailyCount(date=row["date"].strftime("%Y-%m-%d"), count=row["count"])
        )

    daily_status_counts = [
        DailyStatusCount(http_status=status, daily_counts=counts)
        for status, counts in status_map.items()
    ]

    return GetScanDailyStatusCountsResponse(
        id=str(scan_id),
        created_at=scan.created_at,
        updated_at=scan.updated_at,
        name=scan.name,
        frequency=scan.frequency,
        last_run=scan.last_run,
        total_orgs=scan.total_orgs,
        daily_status_counts=daily_status_counts,
        metrics_window_days=window_days,
    )


def list_scans_org_count_by_status(window_days, current_user):
    """List non-global scans and count distinct orgs for each http status in a given time window."""
    if not is_global_write_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    cutoff = (timezone.now() - timedelta(days=window_days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Generate set of non-global scan names from SCAN_SCHEMA
    non_global_scans = {
        name
        for name, schema in SCAN_SCHEMA.items()
        if hasattr(schema, "global_scan") and schema.global_scan is False
    }
    # Generate list of non-global scan IDs from the scan table
    non_global_scan_ids = list(
        Scan.objects.filter(name__in=non_global_scans).values_list("id", flat=True)
    )
    result = (
        ScanResult.objects.filter(
            scan_id__in=non_global_scan_ids,
            scanned_at__gte=cutoff,
        )
        .values("scan_id", "http_status")
        .annotate(count=Count("organization_id", distinct=True))
        .order_by("scan_id", "http_status")
    )
    return transform_org_counts_by_status(result, window_days)


def transform_org_counts_by_status(queryset, window_days):
    """Transform queryset into a structured response for scans and org counts by status."""
    scan_map = defaultdict(list)
    for row in queryset:
        scan_map[row["scan_id"]].append(
            OrgCountByStatus(http_status=row["http_status"], org_count=row["count"])
        )

    scans = Scan.objects.filter(id__in=scan_map.keys())
    scan_results = []
    for scan in scans:
        scan_results.append(
            ScanOrgCountByStatus(
                id=str(scan.id),
                created_at=scan.created_at,
                updated_at=scan.updated_at,
                name=scan.name,
                frequency=scan.frequency,
                last_run=scan.last_run,
                total_orgs=scan.total_orgs,
                org_counts_by_status=scan_map[scan.id],
            )
        )

    return ListScansOrgCountByStatusResponse(
        scans=scan_results, metrics_window_days=window_days
    )
