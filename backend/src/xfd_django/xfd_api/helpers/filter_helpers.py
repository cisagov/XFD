"""Filter helpers."""
# Standard Python Libraries
from datetime import datetime
import logging

# Third-Party Libraries
from django.db.models.query import Q, QuerySet
from fastapi import HTTPException, status

from ..schema_models.vulnerability import VulnerabilityFilters

# Define the severity levels
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
NULL_VALUES = ["None", "Null", "N/A", "Undefined", ""]

# Configure logging
LOGGER = logging.getLogger(__name__)


def format_severity(severity: str) -> str:
    """Format severity to classify as 'N/A', standard severity, or 'Other'."""
    if severity is None or severity in NULL_VALUES:
        return "N/A"
    elif severity.title() in SEVERITY_LEVELS:
        return severity.title()
    else:
        return "Other"


def sort_direction(sort, order):
    """
    Add the sort direction modifier.

    If sort =
        ASC - return order field unmodified to sort in ascending order.
        DSC - returns & prepend '-' to the order field to sort in descending order.
    """
    try:
        # Fetch all domains in list
        if sort == "ASC":
            return order
        elif sort == "asc":
            return order
        elif sort == "DSC":
            return "-" + order
        elif sort == "dsc":
            return "-" + order
        elif sort == "desc":
            return "-" + order
        else:
            raise ValueError
    except ValueError as e:
        LOGGER.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def convert_to_naive(dt: datetime) -> datetime:
    """
    Convert a timezone-aware datetime to naive by removing timezone info.

    Required for vulnerability materialized views created_at date being timestamp
    vs. timestamptz.
    """
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def apply_domain_filters(domains, filters):
    """
    Apply filters to domains QuerySet directly.

    For partial matches (like ILIKE), we use __icontains.
    """
    q = Q()

    if filters.name:
        q &= Q(name__icontains=filters.name)

    # reverse_name partial match
    if filters.reverse_name:
        q &= Q(reverse_name__icontains=filters.reverse_name)

    # name partial match
    if hasattr(filters, "name") and filters.name:
        q &= Q(name__icontains=filters.name)

    # ip partial match
    if filters.ip:
        q &= Q(ip__icontains=filters.ip)

    # Organization exact match
    if filters.organization:
        q &= Q(organization_id=filters.organization)

    # Organization_name partial match
    if filters.organization_name:
        q &= Q(organization_name__icontains=filters.organization_name)

    # Apply the final Q object filter
    filtered = domains.filter(q)

    # If the queryset is empty, return an empty queryset
    if not filtered.exists():
        return filtered.none()

    return filtered


def apply_vuln_filters(
    vulnerabilities: QuerySet, vulnerability_filters: VulnerabilityFilters
) -> QuerySet:
    # pylint: disable=R0912
    """Filter vulnerabilities using Q objects for partial matches and exact matches."""
    q = Q()

    # Exact match on id
    if vulnerability_filters.id:
        q &= Q(id=vulnerability_filters.id)

    # Partial match on title
    if vulnerability_filters.title:
        q &= Q(title__icontains=vulnerability_filters.title)

    # Partial match on domain name
    if vulnerability_filters.domain:
        q &= Q(domain__name__icontains=vulnerability_filters.domain)

    # Severity logic (includes N/A and Other categories)
    if vulnerability_filters.severity:
        severity_category = format_severity(vulnerability_filters.severity)

        if severity_category == "N/A":
            q &= (
                Q(severity=None)
                | Q(severity__icontains="none")
                | Q(severity__icontains="null")
                | Q(severity__icontains="n/a")
                | Q(severity__icontains="undefined")
                | Q(severity="")
            )
        elif severity_category == "Other":
            q &= ~(
                Q(severity=None)
                | Q(severity__icontains="none")
                | Q(severity__icontains="null")
                | Q(severity__icontains="undefined")
                | Q(severity="")
                | Q(severity__icontains="N/A")
                | Q(severity__icontains="Low")
                | Q(severity__icontains="Medium")
                | Q(severity__icontains="High")
                | Q(severity__icontains="Critical")
            )
        elif severity_category in SEVERITY_LEVELS:
            q &= Q(severity__icontains=severity_category)

    # CPE match
    if vulnerability_filters.cpe:
        q &= Q(cpe__icontains=vulnerability_filters.cpe)

    # Exact match on state
    if vulnerability_filters.state:
        q &= Q(state=vulnerability_filters.state)

    # Exact match on substate
    if hasattr(vulnerability_filters, "substate") and vulnerability_filters.substate:
        q &= Q(substate=vulnerability_filters.substate)

    # Exact match on organization
    if vulnerability_filters.organization:
        q &= Q(domain__organization_id=vulnerability_filters.organization)

    # Boolean flag for KEV
    if vulnerability_filters.false_positive is not None:
        q &= Q(false_positive=vulnerability_filters.false_positive)

    # Boolean flag for KEV
    if vulnerability_filters.is_kev is not None:
        q &= Q(is_kev=vulnerability_filters.is_kev)

    # Boolean flag for KEV Ransomware
    if vulnerability_filters.is_kev_ransomware is not None:
        q &= Q(is_kev_ransomware=vulnerability_filters.is_kev_ransomware)

    # Filter by earliest date (discovery window lower bound)
    if vulnerability_filters.earliest_date:
        # naive_earliest = convert_to_naive(vulnerability_filters.earliest_date)
        q &= Q(created_at__gte=vulnerability_filters.earliest_date)

    # # Filter by latest date (discovery window upper bound)
    if vulnerability_filters.latest_date:
        # naive_latest = convert_to_naive(vulnerability_filters.latest_date)
        q &= Q(created_at__lte=vulnerability_filters.latest_date)

    # Filter  by OS
    if vulnerability_filters.os and str(vulnerability_filters.os).lower() != "any":
        q &= Q(os__icontains=vulnerability_filters.os)

    # Filter by public ID (CVE or CWE)
    if (
        vulnerability_filters.public_id
        and vulnerability_filters.public_id.lower() != "any"
    ):
        q &= Q(
            Q(cve__icontains=vulnerability_filters.public_id)
            | Q(cwe__icontains=vulnerability_filters.public_id)
        )

    # Filter by scan type (source with case-insensitive match)
    if (
        vulnerability_filters.scan_type is not None
        and str(vulnerability_filters.scan_type).lower() != "any"
    ):
        q &= Q(source__iexact=vulnerability_filters.scan_type)

    # Filter by scan source (scan_source with case-insensitive match)
    if (
        getattr(vulnerability_filters, "scan_source", None) is not None
        and str(getattr(vulnerability_filters, "scan_source")).lower() != "any"
    ):
        q &= Q(scan_source__iexact=vulnerability_filters.scan_source)

    # Filter by IP or hostname
    if (
        vulnerability_filters.ip_or_host
        and vulnerability_filters.ip_or_host.lower() != "any"
    ):
        q &= Q(
            Q(ip_string__icontains=vulnerability_filters.ip_or_host)
            | Q(domain_string__icontains=vulnerability_filters.ip_or_host)
        )

    # Filter by port or service name
    if (
        vulnerability_filters.port_or_service
        and vulnerability_filters.port_or_service.lower() != "any"
    ):
        q &= Q(
            Q(port__icontains=vulnerability_filters.port_or_service)
            | Q(service_string__icontains=vulnerability_filters.port_or_service)
        )

    filtered = vulnerabilities.filter(q)

    return filtered.none() if not filtered.exists() else filtered


def apply_organization_filters(base_q, filters: dict):
    """Apply organization filters."""
    q = base_q
    name = filters.get("name")
    state = filters.get("state")
    region_id = filters.get("region_id")

    if name:
        q &= Q(name__icontains=str(name).strip())

    if state:
        if isinstance(state, list):
            vals = [str(s).strip().upper() for s in state if s]
            if vals:
                q &= Q(state__in=vals)
        else:
            q &= Q(state__iexact=str(state).strip())

    if region_id:
        if not isinstance(region_id, list):
            region_id = [region_id]
        q &= Q(region_id__in=[int(r) for r in region_id if r is not None and r != ""])

    return q
