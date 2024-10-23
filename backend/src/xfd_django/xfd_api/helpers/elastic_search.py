# Standard Python Libraries
from typing import Any, Dict


def build_request(
    searchBody: Dict[str, Any], options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build an Elasticsearch query from the search body and options.

    :param searchBody: The body containing search parameters such as current page, resultsPerPage,
                       searchTerm, sortField, sortDirection, filters, etc.
    :param options: Additional options for filtering by organizations, etc.
    :return: The Elasticsearch query.
    """
    # Pagination
    current_page = searchBody.get("current", 1)
    results_per_page = searchBody.get("resultsPerPage", 20)

    # Search term
    search_term = searchBody.get("searchTerm", "")

    # Sorting
    sort_field = searchBody.get("sortField", "createdAt")
    sort_direction = searchBody.get("sortDirection", "desc")

    # Filters
    filters = searchBody.get("filters", [])

    # Organization filtering
    organization_ids = options.get("organizationIds", [])

    # Elasticsearch query
    query = {
        "from": (current_page - 1) * results_per_page,
        "size": results_per_page,
        "sort": [{sort_field: {"order": sort_direction}}],
        "query": {"bool": {"must": [{"match": {"_all": search_term}}], "filter": []}},
    }

    # Apply filters
    for filter_item in filters:
        field = filter_item.get("field")
        values = filter_item.get("values", [])
        filter_type = filter_item.get("type", "any")

        if filter_type == "any":
            query["query"]["bool"]["filter"].append({"terms": {field: values}})
        elif filter_type == "range":
            query["query"]["bool"]["filter"].append({"range": {field: values}})

    # Apply organization filters
    if organization_ids:
        query["query"]["bool"]["filter"].append(
            {"terms": {"organization.Id": organization_ids}}
        )

    return query
