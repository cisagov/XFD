"""Saved Search API."""


# Standard Python Libraries
from datetime import datetime, timezone
import logging
import uuid

# Third-Party Libraries
from django.http import JsonResponse
from fastapi import HTTPException, status
from xfd_api.api_methods.organization import get_all_region_ids
from xfd_api.api_methods.search import (
    extract_org_ids_from_filters,
    extract_region_ids_from_filters,
    is_valid_org,
    is_valid_region,
)
from xfd_api.auth import is_global_view_admin, is_regional_admin
from xfd_mini_dl.models import SavedSearch, User

LOGGER = logging.getLogger(__name__)


def validate_name(value: str, current_user):
    """Validate name."""
    name = value.strip()
    if name == "":
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    if SavedSearch.objects.filter(name=name, created_by=current_user).exists():
        raise HTTPException(status_code=400, detail="Name already exists")


def validate_filter_access(filters, current_user):
    """
    Validate that a standard user can only save search/filters for organizations/regions they have access to.

    Raise 403 if they try to save a filter they don't have access to.
    """
    filters = filters or []
    # 1) global users have access to all filters":
    if is_global_view_admin(current_user) or is_regional_admin(current_user):
        return filters

    # 2) Get user's requested orgs and regions
    requested_region_ids = set(extract_region_ids_from_filters(filters or []))
    requested_org_ids = set(extract_org_ids_from_filters(filters or []))

    # 3) Determine unauthorized orgs and regions
    unauthorized_regions = {
        region_id
        for region_id in requested_region_ids
        if not is_valid_region(region_id, current_user)
    }

    unauthorized_orgs = {
        org_id for org_id in requested_org_ids if not is_valid_org(org_id, current_user)
    }

    # 4) Raise errors if unauthorized access is detected
    if unauthorized_orgs:
        raise HTTPException(
            status_code=403,
            detail="Cannot save filters for organizations you do not have access to.",
        )
    if unauthorized_regions:
        raise HTTPException(
            status_code=403,
            detail="Cannot save filters for regions you do not have access to.",
        )

    # 5) All good, return filters
    return filters


def prevent_default_standard_filters(filters, current_user):
    """Prevent standard users from saving default filters."""
    filters = filters or []
    # 1) global users have access to all filters:
    if is_global_view_admin(current_user) or is_regional_admin(current_user):
        return filters

    # 2) Get user's requested orgs and regions
    requested_region_ids = set(extract_region_ids_from_filters(filters or []))
    requested_org_ids = set(extract_org_ids_from_filters(filters or []))

    # 3) Determine default orgs and regions
    default_regions = {
        region_id
        for region_id in requested_region_ids
        if is_valid_region(region_id, current_user)
    }

    default_orgs = {
        org_id for org_id in requested_org_ids if is_valid_org(org_id, current_user)
    }

    # 4) Check for default filters
    if default_regions:
        raise HTTPException(
            status_code=403,
            detail="Cannot save default region filter.",
        )
    if default_orgs:
        raise HTTPException(
            status_code=403,
            detail="Cannot save default organization filter.",
        )

    # 5) All good, return filters
    return filters


def prevent_default_admin_filters(filters, current_user):
    """Prevent admin users from saving default filters."""
    filters = filters or []

    requested_region_ids = set(extract_region_ids_from_filters(filters or []))

    admin_default_regions = set(get_all_region_ids(current_user))

    # 2) Check for default filters
    if requested_region_ids == admin_default_regions:
        raise HTTPException(
            status_code=403,
            detail="Cannot save default region filter for admin users.",
        )
    return filters


def create_saved_search(request, current_user):
    """Create saved search."""
    # 1) Validate the provided name
    validate_name(request.get("name"), current_user)

    try:
        # 2) Process filter values when selecting organizations
        def process_filter_values(values):
            processed_values = []
            for value in values:
                if isinstance(value, dict):
                    processed_values.append(
                        {
                            "id": value.get("id"),
                            "name": value.get("name"),
                            "region_id": value.get("region_id"),
                            "root_domains": value.get("root_domains", []),
                        }
                    )
                else:
                    processed_values.append(value)
            return processed_values

        filters = [
            {
                "type": f.type,
                "field": f.field,
                "values": process_filter_values(f.values),
            }
            for f in request.get("filters", [])
        ]

        # 3) Prevent saving default filters for admin users
        if is_global_view_admin(current_user) or is_regional_admin(current_user):
            filters = prevent_default_admin_filters(filters, current_user)

        # 4) Prevent saving org and region filters for standard users
        filters = prevent_default_standard_filters(filters, current_user)

        # 3) Validate filter access: prevent filter injection attacks by standard users
        filters = validate_filter_access(filters, current_user)

        # 5) Create the SavedSearch record
        search = SavedSearch.objects.create(
            name=request.get("name"),
            count=request.get("count", 0),
            sort_direction=request.get("sort_direction", ""),
            sort_field=request.get("sort_field", ""),
            search_term=request.get("search_term", ""),
            search_path=request.get("search_path", ""),
            filters=filters,
            created_by=current_user,
        )

        # 6) Build the response
        response = {
            "id": str(search.id),
            "created_at": search.created_at,
            "updated_at": search.updated_at,
            "name": search.name,
            "search_term": search.search_term,
            "sort_direction": search.sort_direction,
            "sort_field": search.sort_field,
            "count": search.count,
            "filters": search.filters,
            "search_path": search.search_path,
            "created_by_id": search.created_by.id,
        }

        return response

    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise

    except Exception as e:
        LOGGER.exception("Error creating saved search: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def list_saved_searches(user):
    """List all saved searches for the current user."""
    # 1) Ensure user exists and is valid
    if not hasattr(user, "id"):
        raise HTTPException(status_code=404, detail="User not found")

    try:
        all_saved_searches = SavedSearch.objects.filter(created_by=user)
        saved_search_list = [
            {
                "id": str(search.id),
                "created_at": search.created_at,
                "updated_at": search.updated_at,
                "name": search.name,
                "search_term": search.search_term,
                "sort_direction": search.sort_direction,
                "sort_field": search.sort_field,
                "count": search.count,
                "filters": search.filters,
                "search_path": search.search_path,
                "created_by_id": search.created_by.id,
            }
            for search in all_saved_searches
        ]
        return {"result": saved_search_list, "count": len(saved_search_list)}

    except User.DoesNotExist:
        # unlikely here since `user` came from Depends(get_current_active_user)
        raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        # logger.exception(...) to capture the real error internally
        raise HTTPException(status_code=500, detail="Could not list saved searches")


def get_saved_search(saved_search_id, user):
    """Get saved search."""
    # 1) Validate UUID format
    try:
        uuid.UUID(saved_search_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid saved search ID")

    # 2) Deny globalView users without leaking role names
    if user.user_type == "globalView":
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 3) Fetch record or return 404
    try:
        saved_search = SavedSearch.objects.get(id=saved_search_id)
    except SavedSearch.DoesNotExist:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 4) Enforce ownership
    if saved_search.created_by.id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 5) Return safe payload
    response = {
        "id": str(saved_search.id),
        "created_at": saved_search.created_at,
        "updated_at": saved_search.updated_at,
        "name": saved_search.name,
        "search_term": saved_search.search_term,
        "sort_direction": saved_search.sort_direction,
        "sort_field": saved_search.sort_field,
        "count": saved_search.count,
        "filters": saved_search.filters,
        "search_path": saved_search.search_path,
        "created_by_id": saved_search.created_by.id,
    }
    return response


def update_saved_search(request, user):
    """Update saved search."""
    # 1) Validate UUID format
    try:
        uuid.UUID(request["saved_search_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid saved search ID")

    # 2) Fetch the saved search or return 404
    try:
        saved_search = SavedSearch.objects.get(id=request["saved_search_id"])
    except SavedSearch.DoesNotExist:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 3) Enforce ownership
    if saved_search.created_by.id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 4) Validate name is not empty
    name_value = request["name"].strip()
    if not name_value:
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    # 5) Check for name uniqueness excluding the current saved search
    if (
        SavedSearch.objects.filter(name__iexact=name_value, created_by=user)
        .exclude(id=saved_search.id)
        .exists()
    ):
        raise HTTPException(
            status_code=400, detail="User already has a saved search with this name."
        )

    # 6) Process filter values helper
    def process_filter_values(values):
        processed_values = []
        for value in values:
            if isinstance(value, dict):
                processed_values.append(
                    {
                        "id": value.get("id"),
                        "name": value.get("name"),
                        "region_id": value.get("region_id"),
                        "root_domains": value.get("root_domains", []),
                    }
                )
            else:
                processed_values.append(value)
        return processed_values

    filters = [
        {
            "type": f.type,
            "field": f.field,
            "values": process_filter_values(f.values),
        }
        for f in request.get("filters", [])
    ]

    # 7) Prevent saving default filters for admin users
    if is_global_view_admin(user) or is_regional_admin(user):
        filters = prevent_default_admin_filters(filters, user)

    # 8) Prevent saving region and organization filters for standard users
    filters = prevent_default_standard_filters(filters, user)

    # 7) Validate filter access: prevent filter injection attacks by standard users
    filters = validate_filter_access(filters, user)

    # 9) Apply updates and save
    saved_search.name = request["name"]
    saved_search.updated_at = datetime.now(timezone.utc)
    saved_search.search_term = request["search_term"]
    saved_search.sort_direction = request["sort_direction"]
    saved_search.sort_field = request["sort_field"]
    saved_search.count = request["count"]
    saved_search.search_path = request["search_path"]
    saved_search.filters = filters
    saved_search.save()

    # 10) Build and return response
    response = {
        "name": saved_search.name,
        "search_term": saved_search.search_term,
        "sort_direction": saved_search.sort_direction,
        "sort_field": saved_search.sort_field,
        "count": saved_search.count,
        "filters": filters,
        "search_path": saved_search.search_path,
    }
    return response


def delete_saved_search(saved_search_id, user):
    """Delete saved search by id."""
    # 1) Validate UUID format
    try:
        uuid.UUID(saved_search_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid saved search ID")

    # 2) Fetch or return generic 404
    try:
        search = SavedSearch.objects.get(id=saved_search_id)
    except SavedSearch.DoesNotExist:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 3) Enforce ownership
    if search.created_by.id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")

    # 4) Perform delete
    try:
        search.delete()
    except Exception:
        # logger.exception(exc)  # log internally
        raise HTTPException(status_code=500, detail="Could not delete saved search")

    # 5) Return success response
    return JsonResponse(
        {
            "status": "success",
            "message": f"Saved search id:{saved_search_id} deleted.",
        }
    )
