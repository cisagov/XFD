"""Saved Search API"""


# Standard Python Libraries
from datetime import datetime, timezone
import json
import uuid

# Third-Party Libraries
from django.http import JsonResponse
from fastapi import HTTPException

from ..models import SavedSearch, User
from ..schema_models.saved_search import SavedSearchFilters


def empty_string_check(name):
    if name == "":
        raise HTTPException(status_code=400, detail="Name cannot be empty")


def create_saved_search(request):
    try:
        user = User.objects.get(id=request.get("createdById"))
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    search = SavedSearch.objects.create(
        id=uuid.uuid4(),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        name=request.get("name"),
        count=request.get("count", 0),  # Default to 0 if count does not exist
        sortDirection=request.get("sortDirection", ""),
        sortField=request.get("sortField", ""),
        searchTerm=request.get("searchTerm", ""),
        searchPath=request.get("searchPath", ""),
        filters=[
            {
                "type": "any",
                "field": request.get("field", "organization.regionId"),
                "values": [request.get("regionId")],
            }
        ],
        createdById=user,
    )

    search.save()
    return JsonResponse({"status": "Created", "search": search.id}, status=201)


def list_saved_searches():
    """List all saved searches."""
    try:
        saved_searches = SavedSearch.objects.all()
        saved_search_list = []
        for search in saved_searches:
            filters_without_type = []
            for filter in search.filters:
                # Exclude the "type" field by constructing a new dictionary without it
                filter_without_type = {
                    "field": filter["field"],  # Keep field
                    "values": filter["values"],  # Keep values
                }
                filters_without_type.append(filter_without_type)

            response = {
                "id": str(search.id),
                "createdAt": search.createdAt,
                "updatedAt": search.updatedAt,
                "name": search.name,
                "searchTerm": search.searchTerm,
                "sortDirection": search.sortDirection,
                "sortField": search.sortField,
                "count": search.count,
                "filters": filters_without_type,
                "searchPath": search.searchPath,
                "createdById": search.createdById.id,
            }
            saved_search_list.append(response)

        return list(saved_search_list)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


def get_saved_search(search_id):
    if not uuid.UUID(search_id):
        raise HTTPException({"error": "Invalid UUID"}, status=404)

    try:
        saved_search = SavedSearch.objects.get(id=search_id)
        response = {
            "id": str(saved_search.id),
            "createdAt": saved_search.createdAt,
            "updatedAt": saved_search.updatedAt,
            "name": saved_search.name,
            "searchTerm": saved_search.searchTerm,
            "sortDirection": saved_search.sortDirection,
            "sortField": saved_search.sortField,
            "count": saved_search.count,
            "filters": saved_search.filters,
            "searchPath": saved_search.searchPath,
            "createdById": saved_search.createdById.id,
        }
        return response
    except SavedSearch.DoesNotExist as e:
        raise HTTPException(status_code=404, detail=str(e))


def update_saved_search(request):
    if not uuid.UUID(request["saved_search_id"]):
        raise HTTPException(status_code=404, detail={"error": "Invalid UUID"})

    try:
        saved_search = SavedSearch.objects.get(id=request["saved_search_id"])

    #         search = SavedSearch.objects.get(id=search_id, created_by=request.user)
    except SavedSearch.DoesNotExist as e:
        return HTTPException(status_code=404, detail=str(e))

    saved_search.name = request["name"]
    saved_search.updatedAt = datetime.now()
    saved_search.searchTerm = request["searchTerm"]

    saved_search.save()
    response = {
        "id": saved_search.id,
        "createdAt": saved_search.createdAt,
        "updatedAt": saved_search.updatedAt,
        "name": saved_search.name,
        "searchTerm": saved_search.searchTerm,
        "sortDirection": saved_search.sortDirection,
        "sortField": saved_search.sortField,
        "count": saved_search.count,
        "filters": saved_search.filters,
        "searchPath": saved_search.searchPath,
        "createdById": saved_search.createdById.id,
    }

    return response


def delete_saved_search(search_id):
    """Delete saved search by id."""
    if not uuid.UUID(search_id):
        raise HTTPException(status_code=404, detail={"error": "Invalid UUID"})

    try:
        search = SavedSearch.objects.get(id=search_id)
        search.delete()
        return JsonResponse(
            {"status": "success", "message": f"Saved search id:{search_id} deleted."}
        )
    except SavedSearch.DoesNotExist as e:
        raise HTTPException(status_code=404, detail=str(e))
