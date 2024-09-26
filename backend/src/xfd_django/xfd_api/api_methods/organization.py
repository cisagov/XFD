"""
Organizations API.

"""
# Standard Python Libraries
from typing import List, Optional

# Third-Party Libraries
from fastapi import HTTPException, Query

from ..models import Organization


def read_orgs():
    """
    Call API endpoint to get all organizations.
    Returns:
        list: A list of all organizations.
    """
    try:
        organizations = Organization.objects.all()
        return [
            {
                "id": organization.id,
                "name": organization.name,
                "acronym": organization.acronym,
                "rootDomains": organization.rootDomains,
                "ipBlocks": organization.ipBlocks,
                "isPassive": organization.isPassive,
                "country": organization.country,
                "state": organization.state,
                "regionId": organization.regionId,
                "stateFips": organization.stateFips,
                "stateName": organization.stateName,
                "county": organization.county,
                "countyFips": organization.countyFips,
                "type": organization.type,
                "parentId": organization.parentId.id if organization.parentId else None,
                "createdById": organization.createdById.id
                if organization.createdById
                else None,
                "createdAt": organization.createdAt,
                "updatedAt": organization.updatedAt,
            }
            for organization in organizations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_organizations(
    state: Optional[List[str]] = Query(None),
    regionId: Optional[List[str]] = Query(None),
):
    """
    List all organizations with query parameters.
    Args:
        state (Optional[List[str]]): List of states to filter organizations by.
        regionId (Optional[List[str]]): List of region IDs to filter organizations by.

    Raises:
        HTTPException: If the user is not authorized or no organizations are found.

    Returns:
        List[Organizations]: A list of organizations matching the filter criteria.
    """

    # if not current_user:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    # Prepare filter parameters
    filter_params = {}
    if state:
        filter_params["state__in"] = state
    if regionId:
        filter_params["regionId__in"] = regionId

    organizations = Organization.objects.filter(**filter_params)

    if not organizations.exists():
        raise HTTPException(status_code=404, detail="No organizations found")

    # Return the Pydantic models directly by calling from_orm
    return organizations
