"""Stakeholder lookup helpers for the WAS tracker."""

# Standard Python Libraries
from typing import Any

# First-Party Libraries
from was_reports.data.stakeholders import (
    StakeholderDetails,
    get_stakeholder_details_by_tag,
)


def get_customer_data(tag: str) -> StakeholderDetails:
    """Return stakeholder details from the WAS Postgres database."""
    stakeholder = get_stakeholder_details_by_tag(tag)
    if stakeholder is None and "_" in tag:
        stakeholder = get_stakeholder_details_by_tag(tag.split("_")[0])

    if stakeholder is None:
        raise KeyError("Stakeholder tag {} was not found.".format(tag))

    return stakeholder


def get_dynamo_value(stakeholder: StakeholderDetails, key: str) -> Any:
    """Return a legacy stakeholder value from Postgres-backed details."""
    key_map = {
        "WAS Report POC": stakeholder.was_report_poc,
        "Tech POC Email": stakeholder.tech_poc_email,
        "Distro Email": stakeholder.distro_email,
        "Comments": stakeholder.comments,
        "Report Password": stakeholder.report_password,
        "Manual Report": stakeholder.manual_report,
        "FCEB": stakeholder.fceb,
    }
    return key_map.get(key)
