"""API methods to support Organization endpoints."""

# Standard Python Libraries
import json
import logging
import re
from typing import Any, Dict, List

# Third-Party Libraries
from django.core.paginator import Paginator
from django.db.models import Q
from fastapi import HTTPException, status
from xfd_mini_dl.models import (
    Organization,
    OrganizationTag,
    Role,
    Scan,
    ScanTask,
    User,
    UserType,
)

from ..api_methods.search import is_valid_region
from ..auth import (
    get_org_memberships,
    is_global_view_admin,
    is_global_write_admin,
    is_org_admin,
    is_regional_admin,
    is_regional_admin_for_organization,
    matches_user_region,
)
from ..helpers.filter_helpers import apply_organization_filters
from ..helpers.regionStateMap import REGION_STATE_MAP
from ..helpers.uuid_helpers import is_valid_uuid
from ..schema_models import organization_schema
from ..tasks.es_client import ESClient
from ..tools.serializers import serialize_role

LOGGER = logging.getLogger(__name__)


# GET: /organizations
def list_organizations(current_user):
    """List organizations that the user is a member of or has access to."""
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user) and not get_org_memberships(
            current_user
        ):
            return []

        # Define filter for organizations based on admin status
        org_filter = {}
        if not is_global_view_admin(current_user):
            org_filter["id__in"] = get_org_memberships(current_user)
        org_filter["parent"] = None

        # Fetch organizations with related userRoles and tags
        organizations = (
            Organization.objects.prefetch_related("tags", "user_roles")
            .filter(**org_filter)
            .order_by("name")
        )

        # Serialize organizations using list comprehension
        organization_list = [
            {
                "id": str(org.id),
                "created_at": org.created_at.isoformat(),
                "updated_at": org.updated_at.isoformat(),
                "acronym": org.acronym,
                "name": org.name,
                "root_domains": org.root_domains,
                "ip_blocks": org.ip_blocks,
                "is_passive": org.is_passive,
                "pending_domains": org.pending_domains,
                "country": org.country,
                "state": org.state,
                "region_id": org.region_id,
                "state_fips": org.state_fips,
                "state_name": org.state_name,
                "county": org.county,
                "county_fips": org.county_fips,
                "type": org.type,
                "user_roles": [
                    {"id": str(role.id), "role": role.role, "approved": role.approved}
                    for role in org.user_roles.all()
                ],
                "tags": [
                    {
                        "id": str(tag.id),
                        "created_at": tag.created_at.isoformat(),
                        "updated_at": tag.updated_at.isoformat(),
                        "name": tag.name,
                    }
                    for tag in org.tags.all()
                ],
            }
            for org in organizations
        ]

        return organization_list

    except Exception as e:
        LOGGER.error("Error occurred while listing organizations: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# GET: /organizations/tags
def get_tags(current_user):
    """Fetch all possible organization tags."""
    try:
        # Check if user is a global admin
        if not is_global_view_admin(current_user):
            return []

        # Fetch organization tags
        tags = OrganizationTag.objects.all().values("id", "name")

        # Return the list of tags
        return list(tags)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET: /organizations/{organization_id}
def get_organization(organization_id, current_user):
    """Get information about a particular organization."""
    try:
        # Authorization checks
        if not (
            is_org_admin(current_user, organization_id)
            or is_global_view_admin(current_user)
            or is_regional_admin_for_organization(current_user, organization_id)
        ):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Fetch organization with relations
        organization = (
            Organization.objects.select_related("parent")
            .prefetch_related("user_roles__user", "granular_scans", "tags", "children")
            .filter(id=organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Fetch scan tasks related to the organization, limited to 10 most recent
        scan_tasks = (
            ScanTask.objects.filter(organizations__id=organization_id)
            .select_related("scan")
            .order_by("-created_at")[:10]
        )

        if isinstance(organization.pending_domains, str):
            pending_domains = json.loads(organization.pending_domains)
        elif isinstance(organization.pending_domains, list):
            pending_domains = organization.pending_domains
        else:
            pending_domains = []

        # Serialize organization details along with scan tasks
        org_data = {
            "id": str(organization.id),
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
            "acronym": organization.acronym,
            "name": organization.name,
            "root_domains": organization.root_domains,
            "ip_blocks": organization.ip_blocks,
            "is_passive": organization.is_passive,
            "pending_domains": pending_domains,
            "country": organization.country,
            "state": organization.state,
            "region_id": organization.region_id,
            "state_ips": organization.state_fips,
            "state_name": organization.state_name,
            "county": organization.county,
            "county_fips": organization.county_fips,
            "type": organization.type,
            "created_by": {
                "id": str(organization.created_by.id),
                "first_name": organization.created_by.first_name,
                "last_name": organization.created_by.last_name,
                "email": organization.created_by.email,
            }
            if organization.created_by
            else None,
            "user_roles": [
                {
                    "id": str(role.id),
                    "role": role.role,
                    "approved": role.approved,
                    "user": {
                        "id": str(role.user.id),
                        "email": role.user.email,
                        "first_name": role.user.first_name,
                        "last_name": role.user.last_name,
                        "full_name": role.user.full_name,
                    },
                }
                for role in organization.user_roles.all()
            ],
            "granular_scans": [
                {
                    "id": str(scan.id),
                    "created_at": scan.created_at.isoformat(),
                    "updated_at": scan.updated_at.isoformat(),
                    "name": scan.name,
                    "arguments": scan.arguments,
                    "frequency": scan.frequency,
                    "last_run": scan.last_run.isoformat() if scan.last_run else None,
                    "is_granular": scan.is_granular,
                    "is_user_modifiable": scan.is_user_modifiable,
                    "is_single_scan": scan.is_single_scan,
                    "manual_run_pending": scan.manual_run_pending,
                }
                for scan in organization.granular_scans.all()
            ],
            "tags": [
                {
                    "id": str(tag.id),
                    "created_at": tag.created_at.isoformat(),
                    "updated_at": tag.updated_at.isoformat(),
                    "name": tag.name,
                }
                for tag in organization.tags.all()
            ],
            "parent": {
                "id": str(organization.parent.id),
                "name": organization.parent.name,
            }
            if organization.parent
            else None,
            "children": [
                {"id": str(child.id), "name": child.name}
                for child in organization.children.all()
            ],
            "scan_tasks": [
                {
                    "id": str(task.id),
                    "created_at": task.created_at.isoformat(),
                    "scan": {"id": str(task.scan.id), "name": task.scan.name}
                    if task.scan
                    else None,
                }
                for task in scan_tasks
            ],
        }

        return org_data

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception("An error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# GET: /organizations/state/{state}
def get_by_state(state, current_user):
    """List organizations with specific state."""
    # Check if the current user is a regional admin
    if not is_regional_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch organizations based on the provided state
    organizations = Organization.objects.filter(state=state).values(
        "id",
        "created_at",
        "updated_at",
        "acronym",
        "name",
        "root_domains",
        "ip_blocks",
        "is_passive",
        "pending_domains",
        "country",
        "state",
        "region_id",
        "state_fips",
        "state_name",
        "county",
        "county_fips",
        "type",
    )

    if not organizations:
        raise HTTPException(
            status_code=404, detail="No organizations found for the given state"
        )

    # Return the serialized list of organizations
    return list(organizations)


# GET: /organizations/region_id/{region_id}
def get_by_region(region_id, current_user):
    """List organizations with specific region_id."""
    # Check if the current user is a regional admin
    if not is_regional_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch organizations based on the provided state
    organizations = Organization.objects.filter(region_id=region_id).values(
        "id",
        "created_at",
        "updated_at",
        "acronym",
        "name",
        "root_domains",
        "ip_blocks",
        "is_passive",
        "pending_domains",
        "country",
        "state",
        "region_id",
        "state_fips",
        "state_name",
        "county",
        "county_fips",
        "type",
    )

    if not organizations:
        raise HTTPException(
            status_code=404, detail="No organizations found for the given region"
        )

    # Return the serialized list of organizations
    return list(organizations)


# GET: /regions
def get_all_regions(current_user):
    """Get all regions."""
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user) and not get_org_memberships(
            current_user
        ):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Fetch distinct region_id values
        regions = (
            Organization.objects.exclude(region_id__isnull=True)
            .values("region_id")
            .distinct()
        )

        # Convert to a list and return the regions
        return list(regions)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def find_or_create_tags(
    tags: List[organization_schema.TagSchema],
) -> List[OrganizationTag]:
    """Find or create organization tags."""
    final_tags = []

    for tag_data in tags:
        tag_name = tag_data.name

        # Check if a tag with the given name exists
        existing_tag = OrganizationTag.objects.filter(name=tag_name).first()
        if existing_tag:
            final_tags.append(existing_tag)
        else:
            # If not found, create a new tag
            created_tag = OrganizationTag.objects.create(name=tag_name)
            final_tags.append(created_tag)

    return final_tags


# POST: /organizations
def create_organization(organization_data, current_user):
    """Create a new organization."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Prepare the organization data for creation
        organization_data_dict = organization_data.dict(
            exclude_unset=True, exclude={"tags", "parent"}
        )
        organization_data_dict["created_by"] = current_user

        # Set region_id based on stateName if available
        organization_data_dict["region_id"] = REGION_STATE_MAP.get(
            organization_data.state_name, None
        )

        # Create the organization object
        organization = Organization.objects.create(**organization_data_dict)

        # Link parent organization if provided
        if organization_data.parent:
            organization.parent_id = organization_data.parent
            organization.save()

        # Link tags (using the find_or_create_tags function)
        if organization_data.tags:
            tags = find_or_create_tags(organization_data.tags)
            organization.tags.add(*tags)

        if isinstance(organization.pending_domains, str):
            pending_domains = json.loads(organization.pending_domains)
        elif isinstance(organization.pending_domains, list):
            pending_domains = organization.pending_domains
        else:
            pending_domains = []

        # Return the organization details in response
        return {
            "id": str(organization.id),
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
            "acronym": organization.acronym,
            "name": organization.name,
            "root_domains": organization.root_domains,
            "ip_blocks": organization.ip_blocks,
            "is_passive": organization.is_passive,
            "pending_domains": pending_domains,
            "country": organization.country,
            "state": organization.state,
            "region_id": organization.region_id,
            "state_fips": organization.state_fips,
            "state_name": organization.state_name,
            "county": organization.county,
            "county_fips": organization.county_fips,
            "type": organization.type,
            "created_by": {
                "id": str(current_user.id),  # Simplify to just the user ID
            },
            "tags": [
                {
                    "id": str(tag.id),
                    "created_at": tag.created_at.isoformat(),
                    "updated_at": tag.updated_at.isoformat(),
                    "name": tag.name,
                }
                for tag in organization.tags.all()
            ],
            "parent": {
                "id": str(organization.parent.id),
                "name": organization.parent.name,
            }
            if organization.parent
            else {},
        }

    except HTTPException as http_exc:
        raise http_exc
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Parent organization not found")
    except Exception as e:
        LOGGER.error("Error occurred while creating organization: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /organizations_upsert
def upsert_organization(organization_data, current_user):
    """Create a new organization or update it if it already exists."""
    try:
        # Check if the user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Unauthorized access. View logs for details."
            )

        # Prepare the organization data for creation
        organization_data_dict = organization_data.dict(
            exclude_unset=True, exclude={"tags", "parent"}
        )
        organization_data_dict["created_by"] = current_user

        # Set region_id based on stateName if available
        organization_data_dict["region_id"] = REGION_STATE_MAP.get(
            organization_data.state_name, None
        )

        # Try to update or create a new organization
        organization, created = Organization.objects.update_or_create(
            acronym=organization_data.acronym,  # Conflict target is the acronym
            defaults=organization_data_dict,  # Fields to update if organization exists
        )

        # Link parent organization if provided
        if organization_data.parent:
            organization.parent_id = organization_data.parent
            organization.save()

        # Link tags (using the find_or_create_tags function)
        if organization_data.tags:
            tags = find_or_create_tags(organization_data.tags)
            organization.tags.add(*tags)

        if isinstance(organization.pending_domains, str):
            pending_domains = json.loads(organization.pending_domains)
        elif isinstance(organization.pending_domains, list):
            pending_domains = organization.pending_domains
        else:
            pending_domains = []

        # Return the organization details in response
        return {
            "id": str(organization.id),
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
            "acronym": organization.acronym,
            "name": organization.name,
            "root_domains": organization.root_domains,
            "ip_blocks": organization.ip_blocks,
            "is_passive": organization.is_passive,
            "pending_domains": pending_domains,
            "country": organization.country,
            "state": organization.state,
            "region_id": organization.region_id,
            "state_fips": organization.state_fips,
            "state_name": organization.state_name,
            "county": organization.county,
            "county_fips": organization.county_fips,
            "type": organization.type,
            "created_by": {
                "id": str(organization.created_by.id),
                "first_name": organization.created_by.first_name,
                "last_name": organization.created_by.last_name,
                "email": organization.created_by.email,
            }
            if organization.created_by
            else None,
            "tags": [
                {
                    "id": str(tag.id),
                    "created_at": tag.created_at.isoformat(),
                    "updated_at": tag.updated_at.isoformat(),
                    "name": tag.name,
                }
                for tag in organization.tags.all()
            ],
            "parent": {
                "id": str(organization.parent.id),
                "name": organization.parent.name,
            }
            if organization.parent
            else {},
        }

    except HTTPException as http_exc:
        raise http_exc
    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Parent organization not found")
    except Exception as e:
        LOGGER.error("Error occurred while upserting organization: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /update_organization/{organization_id}
def update_organization(organization_id: str, organization_data, current_user):
    """Update an organization by its ID."""
    try:
        # Validate the organization ID and ensure it's a valid UUID
        if not organization_id or not is_valid_uuid(organization_id):
            raise HTTPException(status_code=404, detail="Not a valid organization id.")

        # Ensure the current user has permission to update the organization
        if not is_org_admin(current_user, organization_id):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Fetch the existing organization with userRoles and granularScans relations
        try:
            organization = Organization.objects.prefetch_related(
                "user_roles", "granular_scans"
            ).get(id=organization_id)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Update only the fields that are provided
        if organization_data.name is not None:
            organization.name = organization_data.name
        if organization_data.acronym is not None:
            organization.acronym = organization_data.acronym
        if organization_data.root_domains is not None:
            organization.root_domains = organization_data.root_domains
        if organization_data.ip_blocks is not None:
            organization.ip_blocks = organization_data.ip_blocks
        if organization_data.state_name is not None:
            organization.state_name = organization_data.state_name
        if organization_data.state is not None:
            organization.state = organization_data.state
        if organization_data.is_passive is not None:
            organization.is_passive = organization_data.is_passive

        # Handle parent organization if provided
        if organization_data.parent:
            organization.parent_id = organization_data.parent

        # Handle tags (using the find_or_create_tags function)
        tags = find_or_create_tags(organization_data.tags)
        organization.tags.set(tags)

        # Save the updated organization object
        organization.save()

        if isinstance(organization.pending_domains, str):
            pending_domains = json.loads(organization.pending_domains)
        elif isinstance(organization.pending_domains, list):
            pending_domains = organization.pending_domains
        else:
            pending_domains = []

        # Return the updated organization details in response
        return {
            "id": str(organization.id),
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
            "acronym": organization.acronym,
            "name": organization.name,
            "root_domains": organization.root_domains,
            "ip_blocks": organization.ip_blocks,
            "is_passive": organization.is_passive,
            "pending_domains": pending_domains,
            "country": organization.country,
            "state": organization.state,
            "region_id": organization.region_id,
            "state_fips": organization.state_fips,
            "state_name": organization.state_name,
            "county": organization.county,
            "county_fips": organization.county_fips,
            "type": organization.type,
            "created_by": {
                "id": str(organization.created_by.id),
                "first_name": organization.created_by.first_name,
                "last_name": organization.created_by.last_name,
                "email": organization.created_by.email,
            }
            if organization.created_by
            else None,
            "tags": [
                {
                    "id": str(tag.id),
                    "created_at": tag.created_at.isoformat(),
                    "updated_at": tag.updated_at.isoformat(),
                    "name": tag.name,
                }
                for tag in organization.tags.all()
            ],
            "user_roles": [
                {
                    "id": str(role.id),
                    "role": role.role,
                    "approved": role.approved,
                    "user": {
                        "id": str(role.user.id),
                        "email": role.user.email,
                        "first_name": role.user.first_name,
                        "last_name": role.user.last_name,
                        "full_name": role.user.full_name,
                    },
                }
                for role in organization.user_roles.all()
            ],
            "granular_scans": [
                {
                    "id": str(scan.id),
                    "created_at": scan.created_at.isoformat(),
                    "updated_at": scan.updated_at.isoformat(),
                    "name": scan.name,
                    "arguments": scan.arguments,
                    "frequency": scan.frequency,
                    "last_run": scan.last_run.isoformat() if scan.last_run else None,
                    "is_granular": scan.is_granular,
                    "is_user_modifiable": scan.is_user_modifiable,
                    "is_single_scan": scan.is_single_scan,
                    "manual_run_pending": scan.manual_run_pending,
                }
                for scan in organization.granular_scans.all()
            ],
        }

    except HTTPException as http_exc:
        raise http_exc

    except Organization.DoesNotExist:
        raise HTTPException(status_code=404, detail="Organization not found")
    except Exception as e:
        LOGGER.error("Error occurred while updating organization details: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# DELETE: /organizations/{organization_id}
def delete_organization(org_id: str, current_user):
    """Delete a particular organization."""
    try:
        # Validate the organization ID format (UUID)
        if not is_valid_uuid(org_id):
            raise HTTPException(status_code=404, detail="Invalid organization ID.")

        # Check if the current user is a GlobalWriteAdmin
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Fetch the organization by ID to ensure it exists
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Organization not found.")

        # Delete the organization
        organization.delete()

        # Return success response
        return {
            "status": "success",
            "message": "Organization {} has been deleted successfully.".format(org_id),
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.error("Error occurred while deleting organization: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /v2/organizations/{organization_id}/users
def add_user_to_org_v2(organization_id: str, user_data, current_user):
    """Add a user to a particular organization."""
    try:
        # Check if the current user has regional admin permissions
        if not is_regional_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Validate the organization ID format (UUID)
        if not is_valid_uuid(organization_id):
            raise HTTPException(status_code=404, detail="Invalid organization ID.")

        # Fetch the organization by ID
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Organization not found.")

        # Validate the user ID in the body
        user_id = user_data.user_id
        if not is_valid_uuid(user_id):
            raise HTTPException(status_code=404, detail="Invalid user ID.")

        # Fetch the user by ID
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found.")

        # Check if the current user's region matches the user's region
        if not matches_user_region(current_user, user.region_id):
            raise HTTPException(
                status_code=403, detail="Unauthorized access due to region mismatch."
            )

        # Prepare the new role data
        new_role_data = {
            "user": user,
            "organization": organization,
            "approved": True,
            "role": user_data.role,
            "approved_by": current_user,
            "created_by": current_user,
        }

        # Create the new role object
        new_role = Role.objects.create(**new_role_data)

        # Return the created role in the response
        return {
            "id": str(new_role.id),
            "user": {
                "id": str(new_role.user.id),
                "email": new_role.user.email,
                "first_name": new_role.user.first_name,
                "last_name": new_role.user.last_name,
            },
            "organization": {
                "id": str(new_role.organization.id),
                "name": new_role.organization.name,
            },
            "role": new_role.role,
            "approved": new_role.approved,
            "approved_by": {
                "id": str(new_role.approved_by.id),
                "email": new_role.approved_by.email,
            },
            "created_by": {
                "id": str(new_role.created_by.id),
                "email": new_role.created_by.email,
            },
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.error("Error occurred while adding user to organization: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /organizations/{organization_id}/roles/{role_id}/approve
def approve_role(organization_id: str, role_id, current_user):
    """Approve a role within an organization."""
    # Check if the current user is an org admin for the organization
    if not is_org_admin(current_user, organization_id):
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    # Validate that the role_id is a valid UUID
    if not is_valid_uuid(role_id):
        raise HTTPException(status_code=404, detail="Role not found")

    # Validate that the organization_id is a valid UUID
    if not is_valid_uuid(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        # Fetch the role within the organization
        role = Role.objects.filter(organization_id=organization_id, id=role_id).first()

        if role:
            # Approve the role and set the approvedBy field to the current user
            role.approved = True
            role.approved_by = current_user
            role.save()

            return {"status": "success", "message": "Role approved successfully"}

        raise HTTPException(status_code=404, detail="Role not found")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST: /organizations/{organization_id}/roles/{role_id}/remove
def remove_role(organization_id: str, role_id, current_user):
    """Remove a role within an organization."""
    # Check if the current user is an org admin for the organization
    if not is_org_admin(current_user, organization_id):
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    # Validate that the role_id is a valid UUID
    if not is_valid_uuid(role_id):
        raise HTTPException(status_code=404, detail="Role not found")

    # Validate that the organization_id is a valid UUID
    if not is_valid_uuid(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        # Attempt to delete the role within the organization
        role = Role.objects.get(organization_id=organization_id, id=role_id)

        result = role.delete()

        # If no role was deleted, raise a 404
        if result[0] == 0:
            raise HTTPException(status_code=404, detail="Role not found")

        return {
            "status": "success",
            "message": "Role removed successfully",
            "role_deleted": serialize_role(role),
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST: /organizations/{organization_id}/granularScans/{scan_id}/update
def update_org_scan(organization_id: str, scan_id, scan_data, current_user):
    """Enable or disable a scan for a particular organization."""
    # Validate organization_id is a valid UUID
    if not is_valid_uuid(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check if the current user is either an org admin or a global write admin
    if not (
        is_org_admin(current_user, organization_id)
        or is_global_write_admin(current_user)
    ):
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    # Validate scan_id is a valid UUID
    if not is_valid_uuid(scan_id):
        raise HTTPException(status_code=404, detail="Scan not found")

    try:
        # Fetch the scan that is granular and user-modifiable
        scan = Scan.objects.filter(
            id=scan_id, is_granular=True, is_user_modifiable=True
        ).first()
        if not scan:
            raise HTTPException(
                status_code=404, detail="Scan not found or not modifiable"
            )

        # Fetch the organization and its related granular scans
        organization = (
            Organization.objects.prefetch_related("granular_scans")
            .filter(id=organization_id)
            .first()
        )
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check the "enabled" field in the request body
        if not scan_data.enabled:
            enabled = False
        else:
            enabled = scan_data.enabled

        # Add the scan to the organization's granular scans if enabled and not already present
        if enabled:
            if not organization.granular_scans.filter(id=scan_id).exists():
                organization.granular_scans.add(scan)
        # Remove the scan from the organization's granular scans if disabled and present
        else:
            if organization.granular_scans.filter(id=scan_id).exists():
                organization.granular_scans.remove(scan)

        # Save the updated organization
        organization.save()

        if isinstance(organization.pending_domains, str):
            pending_domains = json.loads(organization.pending_domains)
        elif isinstance(organization.pending_domains, list):
            pending_domains = organization.pending_domains
        else:
            pending_domains = []

        # Return a success response
        return {
            "id": str(organization.id),
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
            "acronym": organization.acronym,
            "name": organization.name,
            "root_domains": organization.root_domains,
            "ip_blocks": organization.ip_blocks,
            "is_passive": organization.is_passive,
            "pending_domains": pending_domains,
            "country": organization.country,
            "state": organization.state,
            "region_id": organization.region_id,
            "state_fips": organization.state_fips,
            "state_name": organization.state_name,
            "county": organization.county,
            "county_fips": organization.county_fips,
            "type": organization.type,
            "granular_scans": [
                {
                    "id": str(scan.id),
                    "created_at": scan.created_at.isoformat(),
                    "updated_at": scan.updated_at.isoformat(),
                    "name": scan.name,
                    "arguments": scan.arguments,
                    "frequency": scan.frequency,
                    "last_run": scan.last_run.isoformat() if scan.last_run else None,
                    "is_granular": scan.is_granular,
                    "is_user_modifiable": scan.is_user_modifiable,
                    "is_single_scan": scan.is_single_scan,
                    "manual_run_pending": scan.manual_run_pending,
                }
                for scan in organization.granular_scans.all()
            ],
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


MAX_PAGE_SIZE = 200
SORT_MAP = {
    "name": "name",
    "state": "state",
    "region_id": "region_id",
    "created_at": "created_at",
}


# POST: /v2/organizations
def search_organizations_v2(payload, current_user):
    """List organizations that the user is a member of or has access to."""
    try:
        memberships = get_org_memberships(current_user)
        if not is_global_view_admin(current_user) and not memberships:
            return {"result": [], "count": 0}

        f = Q()
        if not is_global_view_admin(current_user) and not is_regional_admin(
            current_user
        ):
            f &= Q(id__in=memberships)

        f = apply_organization_filters(f, payload.filters or {})

        LOGGER.debug("FINAL Q OBJECT: %s", f)
        qs = Organization.objects.filter(f)
        LOGGER.debug("SQL: %s", str(qs.query))

        sort_field = SORT_MAP.get(payload.sort or "", None)
        direction = "" if (payload.order or "asc") == "asc" else "-"
        if sort_field:
            qs = qs.order_by("{}{}".format(direction, sort_field), "id")
        else:
            qs = qs.order_by("created_at", "id")

        page_size = min(max(payload.pageSize or 15, 1), MAX_PAGE_SIZE)
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(payload.page or 1)

        result = [
            {
                "id": str(org.id),
                "created_at": org.created_at.isoformat(),
                "updated_at": org.updated_at.isoformat(),
                "acronym": org.acronym,
                "name": org.name,
                "root_domains": org.root_domains,
                "ip_blocks": org.ip_blocks,
                "is_passive": org.is_passive,
                "pending_domains": org.pending_domains,
                "country": org.country,
                "state": org.state,
                "region_id": org.region_id,
                "state_fips": org.state_fips,
                "state_name": org.state_name,
                "county": org.county,
                "county_fips": org.county_fips,
                "type": org.type,
            }
            for org in page_obj
        ]
        return {"result": result, "count": paginator.count}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        LOGGER.error("Error occurred while listing organizations: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /search/organizations
def escape_special_characters(search_term: str) -> str:
    """Escape special characters in the search term."""
    special_chars = r"([\+\-\&\|\!\(\)\{\}\[\]\^\"\~\*\?\:\\])"
    return re.sub(special_chars, r"\\\1", search_term)


def search_organizations_task(search_body, current_user: User):
    """Handle the logic for searching organizations in Elasticsearch."""
    try:
        if current_user.user_type == UserType.STANDARD:
            raise HTTPException(status_code=403, detail="Unauthorized.")
        if current_user.user_type == UserType.REGIONAL_ADMIN:
            filtered_region_ids = set(search_body.regions or [])
            unauthorized_regions = {
                region_id
                for region_id in filtered_region_ids
                if not is_valid_region(region_id, current_user)
            }
            if unauthorized_regions:
                raise HTTPException(status_code=403, detail="Unauthorized.")
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user) and not get_org_memberships(
            current_user
        ):
            return []

        # Initialize Elasticsearch client
        client = ESClient()

        # Construct the Elasticsearch query

        query_body: Dict[str, Any] = {"query": {"bool": {"must": [], "filter": []}}}

        # Use match_all if searchTerm is empty
        if search_body.search_term.strip():
            sanitized_search_term = escape_special_characters(search_body.search_term)
            query_body["query"]["bool"]["must"].append(
                {
                    "query_string": {
                        "query": "*{}*".format(sanitized_search_term),
                        "fields": ["name"],
                        "fuzziness": "AUTO",
                        "analyze_wildcard": True,
                    }
                }
            )
        else:
            query_body["query"]["bool"]["must"].append({"match_all": {}})

        # Add region filters if provided
        if search_body.regions:
            query_body["query"]["bool"]["filter"].append(
                {"terms": {"region_id": search_body.regions}}
            )

        # Log the query for debugging
        LOGGER.debug("Query body: %s", query_body)

        # Execute the search
        search_results = client.search_organizations(query_body)

        return {"body": search_results}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        LOGGER.exception("Error occurred while searching organizations: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
