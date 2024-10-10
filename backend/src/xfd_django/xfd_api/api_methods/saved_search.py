"""Saved Search API"""


# Standard Python Libraries
import json
import uuid

# Third-Party Libraries
from django.http import JsonResponse
from fastapi import HTTPException

from ..models import SavedSearch

PAGE_SIZE = 20


# def create_saved_search(request):
#     data = json.loads(request.body)
#     search = SavedSearch.objects.create(
#         name=data["name"],
#         count=data["count"],
#         sort_direction=data["sortDirection"],
#         sort_field=data["sortField"],
#         search_term=data["searchTerm"],
#         search_path=data["searchPath"],
#         filters=data["filters"],
#         create_vulnerabilities=data["createVulnerabilities"],
#         vulnerability_template=data.get("vulnerabilityTemplate"),
#         created_by=request.user,
#     )
#     return JsonResponse({"status": "Created", "search": search.id}, status=201)


def list_saved_searches():
    """List all saved searches."""
    try:
        saved_searches = SavedSearch.objects.all()
        count = saved_searches.count()
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
        saved_search = SavedSearch.objects.all()
        for search in saved_search:
            if str(search.id) == search_id:
                return search

        # search = SavedSearch.objects.get(id=search_id, created_by=request.user)
        # data = {
        #     "id": str(search.id),
        #     "name": search.name,
        #     "count": search.count,
        #     "sort_direction": search.sort_direction,
        #     "sort_field": search.sort_field,
        #     "search_term": search.search_term,
        #     "search_path": search.search_path,
        #     "filters": search.filters,
        #     "create_vulnerabilities": search.create_vulnerabilities,
        #     "vulnerability_template": search.vulnerability_template,
        #     "created_by": search.created_by.id,
        # }
        # return JsonResponse(data)
    except SavedSearch.DoesNotExist as e:
        raise HTTPException(status_code=404, detail=str(e))


# def update_saved_search(request, search_id):
#     if not uuid.UUID(search_id):
#         raise HTTPException(status_code=404, detail={"error": "Invalid UUID"})

#     try:
#         search = SavedSearch.objects.get(id=search_id, created_by=request.user)
#     except SavedSearch.DoesNotExist as e:
#         return HTTPException(status_code=404, detail=str(e))

#     data = json.loads(request.body)
#     search.name = data.get("name", search.name)
#     search.count = data.get("count", search.count)
#     search.sort_direction = data.get("sortDirection", search.sort_direction)
#     search.sort_field = data.get("sortField", search.sort_field)
#     search.search_term = data.get("searchTerm", search.search_term)
#     search.search_path = data.get("searchPath", search.search_path)
#     search.filters = data.get("filters", search.filters)
#     search.create_vulnerabilities = data.get(
#         "createVulnerabilities", search.create_vulnerabilities
#     )
#     search.vulnerability_template = data.get(
#         "vulnerabilityTemplate", search.vulnerability_template
#     )
#     search.save()
#     return JsonResponse({"status": "Updated", "search": search.id}, status=200)


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
