"""Elastic search methods."""
# Standard Python Libraries
from typing import Any, Dict, List, Optional

# Define non-keyword fields
NON_KEYWORD_FIELDS = {"updated_at", "created_at"}


def build_from(current: int, results_per_page: int) -> Optional[int]:
    """Build from."""
    if not current or not results_per_page:
        return None
    return (current - 1) * results_per_page


def build_sort(sort_direction: str, sort_field: str) -> Optional[List[Dict[str, Any]]]:
    """Build sort."""
    if not sort_direction or not sort_field:
        return None
    if sort_field in NON_KEYWORD_FIELDS:
        return [{sort_field: {"order": sort_direction}}]
    return [{"{}.keyword".format(sort_field): {"order": sort_direction}}]


def build_match(search_term: str) -> Dict[str, Any]:
    """Build match."""
    if search_term:
        return {
            "query_string": {
                "query": search_term,
                "analyze_wildcard": True,
                "fields": ["*"],
            }
        }
    return {"match_all": {}}


def build_child_match(search_term: str) -> Dict[str, Any]:
    """Build child match."""
    return build_match(search_term)


def get_term_filter_value(field, field_value):
    """
    Determine the appropriate term filter value based on the field and its value.

    Handles specific cases for boolean values, 'organization.region_id', numeric values, the 'name' field, and 'vulnerabilities.severity'.
    """
    if field_value in ["false", "true"]:
        return {field: field_value == "true"}
    if field == "organization.region_id":
        return {field: field_value}
    if isinstance(field_value, (int, float)):
        return {field: field_value}
    if field == "name" and field_value and "*" not in field_value:
        field_value = "*{}*".format(field_value)
    if field == "vulnerabilities.severity":
        return {field: field_value.lower()}
    return {"{}.keyword".format(field): field_value}


def get_term_filter(term_filter):
    """
    Construct the appropriate term filter based on the filter's field and type.

    Handles 'any' and 'all' filter types, and manages nested fields appropriately.
    """
    field_path = term_filter["field"].split(".")
    search_type = "term"
    search = {}

    if term_filter["field"] in ["name", "ip"]:
        search_type = "wildcard"
    elif term_filter["field"] == "services.port":
        search_type = "match"
    elif term_filter["field"] == "organization.region_id":
        search_type = "terms"

    reg_values = [
        "Low",
        "low",
        "Medium",
        "medium",
        "High",
        "high",
        "Critical",
        "critical",
    ]
    na_values = [
        "N/A",
        "n/a",
        "Null",
        "null",
        "None",
        "none",
        "",
        "Undefined",
        "undefined",
    ]

    if term_filter["type"] == "any":
        if term_filter["field"] == "organization.region_id" and term_filter["values"]:
            search = {
                "bool": {
                    "should": [
                        {
                            search_type: get_term_filter_value(
                                term_filter["field"], term_filter["values"]
                            )
                        }
                    ],
                    "minimum_should_match": 1,
                }
            }

        # Handle grouping of N/A values for 'vulnerabilities.severity' field. #

        elif (
            term_filter["field"] == "vulnerabilities.severity"
            and "N/A" in term_filter["values"]
        ):
            search = {
                "bool": {
                    "should": [
                        {"terms": {"vulnerabilities.severity.keyword": na_values}},
                        {
                            "bool": {
                                "must_not": [
                                    {
                                        "exists": {
                                            "field": "vulnerabilities.severity.keyword"
                                        }
                                    }
                                ]
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                }
            }
        # Handle grouping of 'Other' values for 'vulnerabilities.severity' field. #
        elif (
            term_filter["field"] == "vulnerabilities.severity"
            and "Other" in term_filter["values"]
        ):
            search = {
                "bool": {
                    "must_not": [
                        {
                            "terms": {
                                "vulnerabilities.severity.keyword": reg_values
                                + na_values
                            }
                        },
                        {
                            "bool": {
                                "must_not": [
                                    {
                                        "exists": {
                                            "field": "vulnerabilities.severity.keyword"
                                        }
                                    }
                                ]
                            }
                        },
                    ],
                }
            }

        else:
            search = {
                "bool": {
                    "should": [
                        {
                            search_type: get_term_filter_value(
                                term_filter["field"], value
                            )
                        }
                        for value in term_filter["values"]
                    ],
                    "minimum_should_match": 1,
                }
            }
    elif term_filter["type"] == "all":
        search = {
            "bool": {
                "filter": [
                    {search_type: get_term_filter_value(term_filter["field"], value)}
                    for value in term_filter["values"]
                ]
            }
        }

    if len(field_path) > 1 and term_filter["field"] != "organization.region_id":
        return {"nested": {"path": field_path[0], "query": search}}

    return search


def build_request_filter(filters, force_return_no_results):
    """
    Build the request filter for Elasticsearch queries.

    If force_return_no_results is True, returns a filter that matches no results.
    Otherwise, processes each filter using get_term_filter.
    """
    if force_return_no_results:
        return {"term": {"non_existent_field": ""}}

    return [get_term_filter(f) for f in filters]


def build_request(state, options: Dict[str, Any]) -> Dict[str, Any]:
    """Build request."""
    print(options)
    current = state.current
    filters = state.filters or []
    results_per_page = state.results_per_page
    search_term = state.searchTerm
    sort_direction = state.sortDirection
    sort_field = state.sortField

    orgs_in_filters = next(
        (f for f in filters if f["field"] == "organization_id"), None
    )
    refined_filters = (
        [f for f in filters if f["field"] != "organization_id"]
        if orgs_in_filters
        else filters
    )

    should_return_no_results = len(filters) == 0

    sort = build_sort(sort_direction, sort_field)
    match = build_match(search_term)
    size = results_per_page
    from_ = build_from(current, results_per_page)
    filter_ = build_request_filter(refined_filters, should_return_no_results)

    query = {
        "bool": {
            "must": [
                {"match": {"parent_join": "domain"}},
                {
                    "bool": {
                        "should": [
                            match,
                            {
                                "has_child": {
                                    "type": "webpage",
                                    "query": build_child_match(search_term),
                                    "inner_hits": {
                                        "_source": ["webpage_url"],
                                        "highlight": {
                                            "fragment_size": 50,
                                            "number_of_fragments": 3,
                                            "fields": {"webpage_body": {}},
                                        },
                                    },
                                }
                            },
                        ]
                    }
                },
            ],
            "filter": filter_,
        }
    }

    if orgs_in_filters:
        query = {
            "bool": {
                "must": [
                    {
                        "terms": {
                            "organization.id.keyword": [
                                org["id"] for org in orgs_in_filters["values"]
                            ]
                        }
                    },
                    query,
                ]
            }
        }

    body = {
        "highlight": {
            "fragment_size": 200,
            "number_of_fragments": 1,
            "fields": {"name": {}},
        },
        "aggs": {
            "name": {"terms": {"field": "name.keyword"}},
            "from_root_domain": {"terms": {"field": "from_root_domain.keyword"}},
            "organization": {"terms": {"field": "organization.name.keyword"}},
            # The following commented-out code is to be used for future .x releases.
            # Returning org id and region id with facets will allow for a full range of dynamic filters.
            # "organization_id": {
            #   "terms": {"field": "organization.id.keyword"}
            # },
            # "region": {"terms": {"field": "organization.region_id.keyword"}},
            "services": {
                "nested": {"path": "services"},
                "aggs": {
                    "port": {"terms": {"field": "services.port"}},
                    "name": {"terms": {"field": "services.service.keyword"}},
                    "products": {
                        "nested": {"path": "products"},
                        "aggs": {
                            "cpe": {"terms": {"field": "services.products.cpe.keyword"}}
                        },
                    },
                },
            },
            "vulnerabilities": {
                "nested": {"path": "vulnerabilities"},
                "aggs": {
                    "severity": {
                        "terms": {
                            "field": "vulnerabilities.severity.keyword",
                            "missing": "null",
                            "size": 50,
                        }
                    },
                    "cve": {"terms": {"field": "vulnerabilities.cve.keyword"}},
                },
            },
        },
        "query": query,
    }

    if sort:
        body["sort"] = sort
    if size:
        body["size"] = size
    if from_ is not None:
        body["from"] = from_

    return body
