"""Saved Search API"""


# Standard Python Libraries
from datetime import datetime
import json
import uuid

# Third-Party Libraries
from django.http import JsonResponse
from fastapi import HTTPException

from ..models import SavedSearch


def create_saved_search(request):
    data = json.loads(request.body)
    search = SavedSearch.objects.create(
        name=data["name"],
        count=data["count"],
        sort_direction=data["sortDirection"],
        sort_field=data["sortField"],
        search_term=data["searchTerm"],
        search_path=data["searchPath"],
        filters=data["filters"],
        create_vulnerabilities=data["createVulnerabilities"],
        vulnerability_template=data.get("vulnerabilityTemplate"),
        created_by=request.user,
    )
    return JsonResponse({"status": "Created", "search": search.id}, status=201)


def list_saved_searches():
    """List all saved searches."""
    try:
        saved_searches = SavedSearch.objects.all()
        saved_search_list = []
        for search in saved_searches:
            print(str(saved_search_list))
            response = {
                "id": str(search.id),
                "created_at": search.createdAt,
                "updated_at": search.updatedAt,
                "name": search.name,
                "search_term": search.searchTerm,
                "sort_direction": search.sortDirection,
                "sort_field": search.sortField,
                "count": search.count,
                "filters": search.filters,
                "search_path": search.searchPath,
                "createdBy_id": search.createdById.id,
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
            "created_at": saved_search.createdAt,
            "updated_at": saved_search.updatedAt,
            "name": saved_search.name,
            "search_term": saved_search.searchTerm,
            "sort_direction": saved_search.sortDirection,
            "sort_field": saved_search.sortField,
            "count": saved_search.count,
            "filters": saved_search.filters,
            "search_path": saved_search.searchPath,
            "createdBy_id": saved_search.createdById.id,
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
    saved_search.searchTerm = request["search_term"]

    saved_search.save()
    response = {
        "id": saved_search.id,
        "created_at": saved_search.createdAt,
        "updated_at": saved_search.updatedAt,
        "name": saved_search.name,
        "search_term": saved_search.searchTerm,
        "sort_direction": saved_search.sortDirection,
        "sort_field": saved_search.sortField,
        "count": saved_search.count,
        "filters": saved_search.filters,
        "search_path": saved_search.searchPath,
        "createdBy_id": saved_search.createdById.id,
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
