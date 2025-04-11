"""Filter helpers."""
# Third-Party Libraries
from django.db.models.query import Q, QuerySet
from fastapi import HTTPException

from ..schema_models.vulnerability import VulnerabilityFilters

# Define the severity levels
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
NULL_VALUES = ["None", "Null", "N/A", "Undefined", ""]


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
        elif sort == "DSC":
            return "-" + order
        else:
            raise ValueError
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=500, detail="Invalid sort direction supplied")


def apply_domain_filters(domains, filters):
    """
    Apply filters to domains QuerySet directly.

    For partial matches (like ILIKE), we use __icontains.
    """
    q = Q()

    if filters.name:
        q &= Q(name__icontains=filters.name)

    # reverseName partial match
    if filters.reverseName:
        q &= Q(reverseName__icontains=filters.reverseName)

    # name partial match
    if hasattr(filters, "name") and filters.name:
        q &= Q(name__icontains=filters.name)

    # ip partial match
    if filters.ip:
        q &= Q(ip__icontains=filters.ip)

    # Organization exact match
    if filters.organization:
        q &= Q(organization_id=filters.organization)

    # OrganizationName partial match
    if filters.organizationName:
        q &= Q(organization__name__icontains=filters.organizationName)

    # Vulnerabilities partial match by title
    if filters.vulnerabilities:
        q &= Q(vulnerabilities__title__icontains=filters.vulnerabilities)

    # Ports filtering:
    if hasattr(filters, "ports") and filters.ports:
        try:
            port_int = int(filters.ports)
            q &= Q(services__port=port_int)
        except ValueError:
            # If not a valid integer, no match
            q &= Q(pk__in=[])

    # Service partial match in products or service field:
    if filters.service:
        q &= Q(services__products__icontains=filters.service)

    # Apply the final Q object filter
    filtered = domains.filter(q)

    # If the queryset is empty, return an empty queryset
    if not filtered.exists():
        return filtered.none()

    return filtered


def apply_vuln_filters(
    vulnerabilities: QuerySet, vulnerability_filters: VulnerabilityFilters
) -> QuerySet:
    """Filter vulnerabilities using Q objects for partial matches and exact matches."""
    q = Q()

    # Exact match on id
    if vulnerability_filters.id:
        q &= Q(id=vulnerability_filters.id)

    # Exact match on creattedAt
    if vulnerability_filters.createdAt:
        q &= Q(createdAt=vulnerability_filters.createdAt)

    # Partial match on title (ILIKE -> __icontains)
    if vulnerability_filters.title:
        q &= Q(title__icontains=vulnerability_filters.title)

    # Partial match on domain name
    if vulnerability_filters.domain:
        q &= Q(domain__name__icontains=vulnerability_filters.domain)

    # Partial match on severity
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

    # Partial match on cpe
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

    # Exact match on isKev (True/False)
    if vulnerability_filters.isKev is not None:
        q &= Q(isKev=vulnerability_filters.isKev)

    # Apply the final Q object filter
    filtered = vulnerabilities.filter(q)

    # If the queryset is empty, return an empty queryset
    if not filtered.exists():
        return filtered.none()

    return filtered
