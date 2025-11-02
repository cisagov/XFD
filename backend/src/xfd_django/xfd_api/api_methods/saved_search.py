"""Saved Search API."""


# Standard Python Libraries
from datetime import datetime, timezone
import logging
import uuid

# Third-Party Libraries
from django.http import JsonResponse
from fastapi import HTTPException, status
from xfd_mini_dl.models import SavedSearch, User

LOGGER = logging.getLogger(__name__)


def validate_name(value: str):
    """Validate name."""
    name = value.strip()
    if name == "":
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    all_saved_searches = SavedSearch.objects.all()
    for search in all_saved_searches:
        if search.name.strip() == name:
            raise HTTPException(status_code=400, detail="Name already exists")


def create_saved_search(request):
    """Create saved search."""
    # 1) Validate the provided name
    validate_name(request.get("name"))

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

        # 3) Create the SavedSearch record
        search = SavedSearch.objects.create(
            name=request.get("name"),
            count=request.get("count", 0),
            sort_direction=request.get("sort_direction", ""),
            sort_field=request.get("sort_field", ""),
            search_term=request.get("search_term", ""),
            search_path=request.get("search_path", ""),
            filters=filters,
            created_by=request.get("created_by_id"),
        )

        # 4) Build the response
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

    # 5) Process filter values helper
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

    # 6) Apply updates and save
    saved_search.name = request["name"]
    saved_search.updated_at = datetime.now(timezone.utc)
    saved_search.search_term = request["search_term"]
    saved_search.sort_direction = request["sort_direction"]
    saved_search.sort_field = request["sort_field"]
    saved_search.count = request["count"]
    saved_search.search_path = request["search_path"]
    saved_search.filters = filters
    saved_search.save()

    # 7) Build and return response
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
