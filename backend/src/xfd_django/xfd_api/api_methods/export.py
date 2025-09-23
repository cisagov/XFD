"""Export API."""

# Standard Python Libraries
import csv
from datetime import date, datetime
from decimal import Decimal
import io
import logging
from typing import Any

# Third-Party Libraries
from django.contrib.postgres.aggregates import JSONBAgg
from django.db.models import F, OuterRef, Q, Subquery
from django.db.models.functions import JSONObject
from fastapi import HTTPException
from xfd_api.schema_models.export import (
    DEFAULT_SUMMARY_COLS,
    DEFAULT_VULNERABILITY_COLS,
)
from xfd_mini_dl.models import Role, Ticket, TicketEvent, User, VulnScanSummary

from ..api_methods.search import is_valid_org, is_valid_region
from ..schema_models.export import ExportPayload

LOGGER = logging.getLogger(__name__)

SEVERITY_MAP = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def _sanitize_cell(value):
    """Sanitize cell value to prevent CSV injection."""
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal, bool, date, datetime)):
        return value

    s = str(value)

    # Neutralize cells that could be interpreted as formulas or commands
    if s and (s[0] in DANGEROUS_PREFIXES or s[0].isspace()):
        return "'" + s
    return s


def serialize_exported_data(data, mode, columns):
    """Serialize exported data to CSV or JSON based on mode and selected columns, safely."""
    fields = [col.value for col in columns]

    if mode == "json":
        # For JSON we return plain values; browsers won't execute formulas here.
        return list(data.values(*fields))

    if mode == "csv":
        buf = io.StringIO(newline="")
        writer = csv.writer(
            buf,
            quoting=csv.QUOTE_MINIMAL,  # quoting handles commas/newlines safely
            lineterminator="\r\n",  # friendlier for Excel on Windows
        )

        writer.writerow(fields)
        for row in data.values_list(*fields):
            writer.writerow([_sanitize_cell(v) for v in row])

        # Optional: add BOM so Excel auto-detects UTF-8
        text = buf.getvalue()
        return "\ufeff" + text

    return None


def validate_org_filter(filters, current_user):
    """Validate org filter if provided."""
    if filters["org_id"] is None:
        return
    if "org_id" in filters and not is_valid_org(filters["org_id"], current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")


def validate_region_filter(filters, current_user: User):
    """Validate region filter if provided."""
    if filters["region_id"] is None:
        return
    if "region_id" in filters and not is_valid_region(
        filters["region_id"], current_user
    ):
        raise HTTPException(status_code=403, detail="Unauthorized")


def summary_export(filters, current_user: User):
    """Handle querying VulnScanSummary model after filters are built."""
    query_filters = build_summary_filters(filters, current_user)
    try:
        summary_data = VulnScanSummary.objects.filter(query_filters)
        return summary_data
    except Exception as e:
        LOGGER.error(f"Error fetching summary data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def build_summary_filters(filters, current_user):
    """Build Django Q Object based on filters from input."""
    query = Q()
    if filters.org_id:
        query &= Q(organization_id=filters.org_id)
    else:
        if current_user.user_type == "standard":
            # Standard users can only request for their own organization
            role = Role.objects.filter(user=current_user).first()
            query &= Q(organization_id=role.organization_id)
    if filters.region_id:
        if isinstance(filters.region_id, list):
            query &= Q(organization__region_id__in=filters.region_id)
        elif isinstance(filters.region_id, str):
            query &= Q(organization__region_id=filters.region_id)
    else:
        # If not region_id is passed
        if current_user.user_type == "standard":
            # Lock standard user to their own region
            query &= Q(organization__region_id=current_user.region_id)
        if current_user.user_type == "regional_admin":
            # Default to regional admin's region
            query &= Q(organization__region_id=current_user.region_id)
    if filters.begin_date:
        query &= Q(summary_date__gte=filters.begin_date)
    if filters.end_date:
        query &= Q(summary_date__lte=filters.end_date)
    return query


def build_vulnerability_filters(filters, current_user):
    """Build Django Q Object based on filters from input."""
    query = Q()
    if filters.org_id:
        query &= Q(organization_id=filters.org_id)
    else:
        if current_user.user_type == "standard":
            role = Role.objects.filter(user=current_user).first()
            query &= Q(organization_id=role.organization_id)
    if filters.region_id:
        if isinstance(filters.region_id, list):
            query &= Q(organization__region_id__in=filters.region_id)
        elif isinstance(filters.region_id, str):
            query &= Q(organization__region_id=filters.region_id)
    else:
        if current_user.user_type == "standard":
            query &= Q(organization__region_id=current_user.region_id)
        if current_user.user_type == "regional_admin":
            query &= Q(organization__region_id=current_user.region_id)
    if filters.ticket_open is not None:
        query &= Q(is_open=filters.ticket_open)
    if filters.ticket_false_positive is not None:
        query &= Q(false_positive=filters.ticket_false_positive)
    if filters.severity is not None:
        severity_mapped = [
            SEVERITY_MAP[s.lower()]
            for s in filters.severity
            if s.lower() in SEVERITY_MAP
        ]
        query &= Q(severity__in=severity_mapped)
    return query


def vulnerability_export(filters, current_user: User):
    """Handle querying Ticket model after filters are built."""
    query_filters = build_vulnerability_filters(filters, current_user)

    events_json = JSONBAgg(
        JSONObject(
            action=F("ticket_events__action"),
            at=F("ticket_events__event_timestamp"),
            reason=F("ticket_events__reason"),
            reference=F("ticket_events__reference"),
        ),
        ordering="ticket_events__event_timestamp",
    )

    latest_ev_with_vuln = TicketEvent.objects.filter(
        ticket_id=OuterRef("pk"), vuln_scan__isnull=False
    ).order_by("-event_timestamp")

    vs_port = Subquery(latest_ev_with_vuln.values("vuln_scan__port")[:1])
    vs_protocol = Subquery(latest_ev_with_vuln.values("vuln_scan__port_protocol")[:1])
    vs_plugin_id = Subquery(latest_ev_with_vuln.values("vuln_scan__plugin_id")[:1])
    vs_plugin_output = Subquery(
        latest_ev_with_vuln.values("vuln_scan__plugin_output")[:1]
    )
    vs_description = Subquery(latest_ev_with_vuln.values("vuln_scan__description")[:1])
    vs_severity = Subquery(latest_ev_with_vuln.values("vuln_scan__severity")[:1])
    vs_solution = Subquery(latest_ev_with_vuln.values("vuln_scan__solution")[:1])
    vs_synopsis = Subquery(latest_ev_with_vuln.values("vuln_scan__synopsis")[:1])

    qs = (
        Ticket.objects.order_by()
        .annotate(
            events=events_json,
            port=vs_port,
            protocol=vs_protocol,
            plugin_id=vs_plugin_id,
            plugin_output=vs_plugin_output,
            description=vs_description,
            severity=vs_severity,
            solution=vs_solution,
            synopsis=vs_synopsis,
        )
        .filter(query_filters)
        .values(
            "port",
            "protocol",
            "plugin_id",
            "plugin_output",
            "description",
            "severity",
            "solution",
            "synopsis",
        )
    )
    return qs


def export(request_body: ExportPayload, current_user: User):
    """Handle export logic for /export endpoint."""
    mode = request_body.mode
    filters = request_body.filters
    collection = request_body.collection
    columns = []
    collected_data: Any = None
    # Validate org and region filters based on user access - uses user.user_type
    validate_org_filter(filters.dict(), current_user)
    validate_region_filter(filters.dict(), current_user)

    if collection == "summary":
        columns = request_body.columns if request_body.columns else DEFAULT_SUMMARY_COLS
        summary_data = summary_export(filters, current_user)
        collected_data = summary_data

        LOGGER.info(f"Exported {summary_data.count()} summary records.")
    elif collection == "vulnerability":
        columns = (
            request_body.columns if request_body.columns else DEFAULT_VULNERABILITY_COLS
        )
        vulnerability_data = vulnerability_export(filters, current_user)
        LOGGER.info(vulnerability_data.values("id")[:5])
        collected_data = vulnerability_data
    return {
        "mode": mode,
        "collection": collection,
        "data": serialize_exported_data(collected_data, mode, columns),
    }
