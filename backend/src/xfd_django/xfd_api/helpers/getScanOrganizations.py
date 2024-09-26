"""Get scan organizations methods."""

# cisagov Libraries
from ..models import Organization, Scan

# Standard Python Libraries
from typing import List


def get_scan_organizations(scan: Scan) -> List[Organization]:
    """
    Returns the organizations that a scan should be run on.
    A scan should be run on an organization if the scan is
    enabled for that organization or for one of its tags.
    """
    organizations_to_run = {}

    # Add organizations associated with tags
    for tag in scan.tags.all():
        for organization in tag.organizations.all():
            organizations_to_run[organization.id] = organization

    # Add directly associated organizations
    for organization in scan.organizations.all():
        organizations_to_run[organization.id] = organization

    return list(organizations_to_run.values())
