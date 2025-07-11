"""Saved Search API."""


# Standard Python Libraries
from datetime import datetime, timezone
import uuid

# Third-Party Libraries
from django.http import JsonResponse
from fastapi import HTTPException
from xfd_mini_dl.models import SavedSearch, User


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
    validate_name(request.get("name"))
    try:
        # Process filter values when selecting organizations
        def process_filter_values(values):
            processed_values = []
            for value in values:
                if isinstance(value, dict):
                    # Include only the required fields
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

        search = SavedSearch.objects.create(
            name=request.get("name"),
            count=request.get("count", 0),  # Default to 0 if count does not exist
            sort_direction=request.get("sort_direction", ""),
            sort_field=request.get("sort_field", ""),
            search_term=request.get("search_term", ""),
            search_path=request.get("search_path", ""),
            filters=filters,
            created_by=request.get("created_by_id"),
        )

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

        search.save()
        return response

    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail=str(e))


def list_saved_searches(user):
    """List all saved searches."""
    try:
        all_saved_searches = SavedSearch.objects.all()
        saved_search_list = []
        for search in all_saved_searches:
            if search.created_by != user:
                continue
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
            saved_search_list.append(response)
        return {
            "result": list(saved_search_list),
            "count": len(list(saved_search_list)),
        }
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


def get_saved_search(saved_search_id, user):
    """Get saved search."""
    if user.user_type == "globalView":
        raise HTTPException(
            status_code=404, detail="Global View users cannot retrieve saved searches."
        )
    if not uuid.UUID(saved_search_id):
        raise HTTPException({"error": "Invalid UUID"})

    try:
        saved_search = SavedSearch.objects.get(id=saved_search_id)

        if saved_search.created_by.id != user.id:
            raise HTTPException(status_code=404, detail="Saved search not found")

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
    except SavedSearch.DoesNotExist as dne:
        raise HTTPException(status_code=404, detail=str(dne))
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


def update_saved_search(request, user):
    """Update saved search."""
    if not uuid.UUID(request["saved_search_id"]):
        raise HTTPException(status_code=404, detail={"error": "Invalid UUID"})
    try:
        # Process filter values when selecting organizations
        def process_filter_values(values):
            processed_values = []
            for value in values:
                if isinstance(value, dict):
                    # Include only the required fields
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

        saved_search = SavedSearch.objects.get(id=request["saved_search_id"])
        if saved_search.created_by.id != user.id:
            raise HTTPException(status_code=404, detail="Saved search not found")

        name = request["name"].strip()
        if name == "":
            raise HTTPException(status_code=400, detail="Name cannot be empty")

        saved_search.name = request["name"]
        saved_search.updated_at = datetime.now(timezone.utc)
        saved_search.search_term = request["search_term"]
        saved_search.save()
        response = {
            "name": saved_search.name,
            "search_term": saved_search.search_term,
            "sort_direction": saved_search.sort_direction,
            "sort_field": saved_search.sort_field,
            "count": saved_search.count,
            "filters": filters,
            "search_path": saved_search.search_path,
        }
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except SavedSearch.DoesNotExist as dne:
        raise HTTPException(status_code=404, detail=str(dne))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return response


def delete_saved_search(saved_search_id, user):
    """Delete saved search by id."""
    if not uuid.UUID(saved_search_id):
        raise HTTPException(status_code=404, detail={"error": "Invalid UUID"})
    try:
        search = SavedSearch.objects.get(id=saved_search_id)
        if search.created_by.id != user.id:
            raise HTTPException(status_code=404, detail="Saved search not found")
        search.delete()
        return JsonResponse(
            {
                "status": "success",
                "message": "Saved search id:{} deleted.".format(saved_search_id),
            }
        )
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except SavedSearch.DoesNotExist as dne:
        raise HTTPException(status_code=404, detail=str(dne))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
