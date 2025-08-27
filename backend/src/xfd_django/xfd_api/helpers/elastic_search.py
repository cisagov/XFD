"""Elastic search methods."""
# Standard Python Libraries
import logging
from typing import Any, Dict, List, Optional

from ..schema_models.search import DomainSearchBody

LOGGER = logging.getLogger(__name__)

# Define non-keyword fields
NON_KEYWORD_FIELDS = {"updated_at", "created_at"}

# Shared severity groupings
REG_VALUES = [
    "Low",
    "low",
    "Medium",
    "medium",
    "High",
    "high",
    "Critical",
    "critical",
    "N/A",
]
NA_VALUES = ["N/A", "n/a", "Null", "null", "None", "none", "", "Undefined", "undefined"]


def build_from(current: int | None, results_per_page: int | None) -> Optional[int]:
    """Build from."""
    if not current or not results_per_page:
        return None
    return (current - 1) * results_per_page


def build_sort(
    sort_direction: str | None, sort_field: str | None
) -> Optional[List[Dict[str, Any]]]:
    """Build sort."""
    if not sort_direction or not sort_field:
        return None
    if sort_field in NON_KEYWORD_FIELDS:
        return [{sort_field: {"order": sort_direction}}]
    return [{"{}.keyword".format(sort_field): {"order": sort_direction}}]


def build_match(search_term: str | None) -> Dict[str, Any]:
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


def build_child_match(search_term: str | None) -> Dict[str, Any]:
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


def _nested(query: Dict[str, Any], path: str) -> Dict[str, Any]:
    """Wrap a query into a nested clause for a given path."""
    return {"nested": {"path": path, "query": query}}


def get_term_filter(term_filter):
    """
    Construct the appropriate term filter based on the filter's field and type.

    Handles 'any' and 'all' filter types, and manages nested fields appropriately.

    NOTE: For 'vulnerabilities.severity', this returns a dict with a special key
    '__post_filter__' so we can apply it via post_filter (to preserve facets).
    """
    field_path = term_filter["field"].split(".")
    search_type = "term"
    search: Dict[str, Any] = {}

    if term_filter["field"] in ["name", "ip"]:
        search_type = "wildcard"
    elif term_filter["field"] == "services.port":
        search_type = "match"
    elif term_filter["field"] == "organization.region_id":
        search_type = "terms"

    # --- Special handling for vulnerabilities.severity in post_filter ---
    if (
        term_filter["field"] == "vulnerabilities.severity"
        and term_filter["type"] == "any"
    ):
        values = term_filter.get("values") or []
        has_other = "Other" in values
        has_na = "N/A" in values
        # Explicit severities (excluding special buckets)
        explicit = [v for v in values if v not in set(NA_VALUES) and v != "Other"]

        should_clauses: List[Dict[str, Any]] = []

        if has_other:
            # "Other" = docs where nested severity exists AND is NOT in REG_VALUES + NA_VALUES
            should_clauses.append(
                _nested(
                    {
                        "bool": {
                            "must": [
                                {
                                    "exists": {
                                        "field": "vulnerabilities.severity.keyword"
                                    }
                                }
                            ],
                            "must_not": [
                                {
                                    "terms": {
                                        "vulnerabilities.severity.keyword": REG_VALUES
                                        + NA_VALUES
                                    }
                                }
                            ],
                        }
                    },
                    "vulnerabilities",
                )
            )

        if has_na:
            # "N/A" group = any of NA_VALUES OR nested row missing the field
            should_clauses.append(
                _nested(
                    {
                        "terms": {
                            "vulnerabilities.severity.keyword": NA_VALUES + explicit
                        }
                    },
                    "vulnerabilities",
                )
            )
            should_clauses.append(
                _nested(
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
                    "vulnerabilities",
                )
            )

        # Explicit severities (e.g., "Medium", "High", etc.)
        if explicit:
            should_clauses.append(
                _nested(
                    {"terms": {"vulnerabilities.severity.keyword": explicit}},
                    "vulnerabilities",
                )
            )

        if should_clauses:
            # Return as post_filter so aggs remain unaffected
            return {
                "__post_filter__": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1,
                    }
                }
            }
        # If no values, fall through to normal handling (no-op)

    # --- Normal filters (non-severity, or severity with 'all' if ever needed) ---
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

    # Wrap in nested when needed (excluding organization.region_id)
    if len(field_path) > 1 and term_filter["field"] != "organization.region_id":
        return {"nested": {"path": field_path[0], "query": search}}

    return search


def build_request_filter(filters, force_return_no_results):
    """
    Build both the regular filters and the post_filter.

    Returns: (filter_list, post_filter_clause or None)
    """
    if force_return_no_results:
        return [{"term": {"non_existent_field": ""}}], None

    filter_list: List[Dict[str, Any]] = []
    post_filters: List[Dict[str, Any]] = []

    for f in filters:
        built = get_term_filter(f)
        if "__post_filter__" in built:
            post_filters.append(built["__post_filter__"])
        else:
            filter_list.append(built)

    # Combine multiple post_filters with AND semantics
    post_filter_clause = None
    if post_filters:
        if len(post_filters) == 1:
            post_filter_clause = post_filters[0]
        else:
            post_filter_clause = {"bool": {"filter": post_filters}}

    return filter_list, post_filter_clause


def build_request(state: DomainSearchBody) -> Dict[str, Any]:
    """Build Elasticsearch request body."""
    current = state.current
    filters = state.filters or []
    results_per_page = state.resultsPerPage
    search_term = state.searchTerm
    sort_direction = state.sortDirection
    sort_field = state.sortField

    # Extract org filters from filters list
    orgs_in_filters = next(
        (f for f in filters if f["field"] == "organization_id"), None
    )

    # Remove organization_id filters from filters so they are handled separately
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
    filter_list, post_filter_clause = build_request_filter(
        refined_filters, should_return_no_results
    )
    LOGGER.info("Filters: %s", filter_list)
    if post_filter_clause:
        LOGGER.info("Post-filter: %s", post_filter_clause)

    # Base query
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
            "filter": filter_list,
        }
    }

    # Add organization filter if valid
    if orgs_in_filters and orgs_in_filters.get("values"):
        org_ids = [org["id"] for org in orgs_in_filters["values"] if "id" in org]
        if org_ids:
            query = {
                "bool": {
                    "must": [
                        {"terms": {"organization.id.keyword": org_ids}},
                        query,
                    ]
                }
            }

    # Final request body
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
                            "missing": "N/A",  # show missing as "N/A" in facets
                            "size": 50,
                        }
                    },
                    "cve": {"terms": {"field": "vulnerabilities.cve.keyword"}},
                },
            },
        },
        "query": query,
    }

    if post_filter_clause:
        body["post_filter"] = post_filter_clause
    if sort:
        body["sort"] = sort
    if size:
        body["size"] = size
    if from_ is not None:
        body["from"] = from_

    return body
