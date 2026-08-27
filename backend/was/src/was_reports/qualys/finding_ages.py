"""Retrieve maximum critical and urgent WAS finding ages from Qualys."""

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Third-Party Libraries
from dateutil.parser import isoparse
from lxml import etree, objectify
from lxml.builder import E

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, QualysRequest

FINDING_SEARCH_ENDPOINT = "search/was/finding"
ACTIVE_FINDING_STATUSES = "ACTIVE, NEW, REOPENED"
CRITICAL_SEVERITY = "4"
URGENT_SEVERITY = "5"


@dataclass(frozen=True)
class FindingAges:
    """Maximum age values displayed on the report card."""

    critical_days: int
    urgent_days: int


def build_oldest_finding_payload(stakeholder_tag: str, severity: str) -> str:
    """Build the preserved one-result Qualys finding search payload."""
    root = E.ServiceRequest(
        E.filters(
            E.Criteria(
                stakeholder_tag,
                field="webApp.tags.name",
                operator="EQUALS",
            ),
            E.Criteria(
                ACTIVE_FINDING_STATUSES,
                field="status",
                operator="IN",
            ),
            E.Criteria(severity, field="severity", operator="EQUALS"),
            E.Criteria(
                "FALSE_POSITIVE",
                field="ignoredReason",
                operator="NOT EQUALS",
            ),
        ),
        E.preferences(E.limitResults("1")),
    )
    objectify.deannotate(root, xsi_nil=True, pytype=True, xsi=True)
    return etree.tostring(root).decode()


def parse_first_detected(response_xml: str) -> Optional[datetime]:
    """Return the first finding's detection timestamp when one exists."""
    root = objectify.fromstring(response_xml.encode())
    date_elements = root.xpath("./data/Finding/firstDetectedDate")
    if not date_elements:
        return None
    detected_at = isoparse(str(date_elements[0]))
    if detected_at.tzinfo is None:
        return detected_at.replace(tzinfo=timezone.utc)
    return detected_at.astimezone(timezone.utc)


def finding_age_days(
    first_detected: Optional[datetime],
    current_time: datetime,
) -> int:
    """Return whole elapsed UTC days or zero when no finding exists."""
    if first_detected is None:
        return 0
    resolved_current_time = current_time
    if resolved_current_time.tzinfo is None:
        resolved_current_time = resolved_current_time.replace(tzinfo=timezone.utc)
    return (
        resolved_current_time.astimezone(timezone.utc) - first_detected
    ).days


def retrieve_finding_ages(
    client: QualysClient,
    stakeholder_tag: str,
    current_time: Optional[datetime] = None,
) -> FindingAges:
    """Retrieve maximum critical and urgent finding ages for a stakeholder."""
    resolved_current_time = current_time or datetime.now(timezone.utc)
    critical_response = client.request(
        QualysRequest(
            endpoint=FINDING_SEARCH_ENDPOINT,
            payload=build_oldest_finding_payload(
                stakeholder_tag,
                CRITICAL_SEVERITY,
            ),
        )
    )
    urgent_response = client.request(
        QualysRequest(
            endpoint=FINDING_SEARCH_ENDPOINT,
            payload=build_oldest_finding_payload(
                stakeholder_tag,
                URGENT_SEVERITY,
            ),
        )
    )
    return FindingAges(
        critical_days=finding_age_days(
            parse_first_detected(critical_response),
            resolved_current_time,
        ),
        urgent_days=finding_age_days(
            parse_first_detected(urgent_response),
            resolved_current_time,
        ),
    )
