"""Search methods."""
# Standard Python Libraries
import csv
import io
import logging
from typing import Any, Dict, List

# Third-Party Libraries
from fastapi import HTTPException, status
from xfd_api.auth import (
    get_organization_region,
    get_tag_organizations,
    is_global_view_admin,
    is_regional_admin_for_organization,
)
from xfd_api.helpers.elastic_search import build_request
from xfd_api.helpers.s3_client import S3Client
from xfd_api.tasks.es_client import ESClient
from xfd_mini_dl.models import Role

from ..schema_models.search import DomainSearchBody

# Configure logging
LOGGER = logging.getLogger(__name__)


async def get_options(search_body, user) -> Dict[str, Any]:
    """Get Elastic Search options."""
    if search_body.organization_id and (
        search_body.organization_id in get_org_memberships(user)
        or is_global_view_admin(user)
    ):
        return {
            "organization_ids": [search_body.organization_id],
            "match_all_organizations": False,
        }
    if search_body.tag_id:
        return {
            "organization_ids": get_tag_organizations(user, search_body.tag_id),
            "match_all_organizations": False,
        }

    return {
        "organization_ids": get_org_memberships(user),
        "match_all_organizations": is_global_view_admin(user),
    }


async def fetch_all_results(
    search_body: DomainSearchBody,
    client: ESClient,
) -> List[Dict[str, Any]]:
    """Fetch all results from Elasticsearch."""
    results: List[Any] = []
    current = 1
    RESULTS_PER_PAGE = 1000

    while True:
        paginated_body = DomainSearchBody(
            **{
                "current": current,
                "results_per_page": RESULTS_PER_PAGE,
                "filters": search_body.filters,
                "search_term": search_body.searchTerm,
                "sort_direction": search_body.sortDirection,
                "sort_field": search_body.sortField,
            }
        )

        request = build_request(paginated_body)

        try:
            response = client.search_domains(request)
        except Exception as e:
            LOGGER.exception("Elasticsearch error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error querying Elasticsearch.",
            )

        hits = response.get("hits", {}).get("hits", [])
        if not hits:
            break

        results.extend(hit["_source"] for hit in hits)
        current += 1

    return results


async def fetch_all_results_scroll(
    search_body: DomainSearchBody,
    client: ESClient,
    page_size: int = 1000,
    scroll_keepalive: str = "2m",
) -> list[dict]:
    """Fetch all results from Elasticsearch using the scroll API."""
    results: list[dict] = []
    scroll_id = None

    # Build base request using your existing function
    body = build_request(search_body)

    # Scroll-specific tweaks
    body.pop("from", None)
    body["size"] = page_size
    body.pop("aggs", None)
    body.pop("highlight", None)

    try:
        resp = client.search_domains(body=body, scroll=scroll_keepalive)
        scroll_id = resp.get("_scroll_id")
        hits = resp.get("hits", {}).get("hits", [])

        while hits:
            results.extend(h["_source"] for h in hits if "_source" in h)

            resp = client.scroll_domains(
                scroll_id=scroll_id, keepalive=scroll_keepalive
            )
            scroll_id = resp.get("_scroll_id", scroll_id)
            hits = resp.get("hits", {}).get("hits", [])

    except Exception as e:
        LOGGER.exception("Elasticsearch scroll error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error streaming results from Elasticsearch.",
        )
    finally:
        if scroll_id:
            try:
                client.clear_scroll_domains(scroll_id=scroll_id)
            except Exception:
                LOGGER.warning("Failed to clear scroll_id %s", scroll_id)

    return results


def process_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process Elasticsearch results into the desired format."""
    processed_results = []
    for res in results:
        res["organization"] = (
            res["organization"]["name"] if "organization" in res else None
        )
        res["ports"] = ", ".join(
            str(service["port"]) for service in res.get("services", [])
        )

        products = {}
        for service in res.get("services", []):
            for product in service.get("products", []):
                if "name" in product:
                    product_name = product["name"].lower()
                    product_version = product.get("version", "")
                    products[product_name] = "{} {}".format(
                        product["name"], product_version
                    ).strip()

        res["products"] = ", ".join(products.values())
        processed_results.append(res)

    return processed_results


def generate_csv(results: List[Dict[str, Any]], fields: List[str]) -> str:
    """Generate a CSV from the processed results."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue()


def extract_org_ids_from_filters(filters: List[dict]) -> List[str]:
    """Extract the passed org ids from the filters."""
    for f in filters:
        if f["field"] == "organization_id":
            return [
                org["id"]
                for org in f["values"]
                if isinstance(org, dict) and "id" in org
            ]
    return []


def extract_region_ids_from_filters(filters: List[dict]) -> List[str]:
    """Extract region_ids from teh filters."""
    for f in filters:
        if f["field"] == "organization.region_id":
            return f["values"]
    return []


def get_org_memberships(current_user) -> list[str]:
    """Return the organization IDs that a user is a member of."""
    # Check if the user has a 'roles' attribute and it's not None

    roles = Role.objects.filter(user_id=current_user.id)
    return [str(role.organization.id) for role in roles if role.organization]


def is_valid_org(org_id: str, user) -> bool:
    """Validate the user is authorized to see the organization's data."""
    if is_global_view_admin(user):
        return True
    elif user.user_type == "regionalAdmin":
        return is_regional_admin_for_organization(user, org_id)
    else:
        return str(org_id) in get_org_memberships(user)


def is_valid_region(region_id: str, user) -> bool:
    """Validate user is allowed to see specified region."""
    if is_global_view_admin(user):
        return True
    elif user.user_type == "regionalAdmin":
        return region_id == user.region_id
    else:
        user_orgs = get_org_memberships(user)
        user_regions = {get_organization_region(org_id) for org_id in user_orgs}
        return region_id in user_regions


def clean_and_authorize_filters(search_body: DomainSearchBody, current_user):
    """Clean up the passed filters and validate authentication."""
    filters = search_body.filters or []

    # Remove existing org/region filters
    non_org_filters = [
        f
        for f in filters
        if f["field"] not in ("organization_id", "organization.region_id")
    ]

    new_filters = list(non_org_filters)

    if is_global_view_admin(current_user):
        # For global admins, keep all filters intact (no validation)
        # So just return early with filters untouched
        return

    elif current_user.user_type == "regionalAdmin" and current_user.region_id:
        region_id = current_user.region_id

        # Always inject region filter
        new_filters.append(
            {"field": "organization.region_id", "values": [region_id], "type": "any"}
        )

        # Include only the orgs that are in-region
        requested_org_ids = set(extract_org_ids_from_filters(filters))

        valid_org_ids = {
            org_id
            for org_id in requested_org_ids
            if is_regional_admin_for_organization(current_user, org_id)
        }

        if valid_org_ids:
            new_filters.append(
                {
                    "field": "organization_id",
                    "values": [{"id": org_id} for org_id in valid_org_ids],
                    "type": "any",
                }
            )
    else:
        # Standard user: allowed orgs only
        requested_org_ids = set(extract_org_ids_from_filters(filters))
        allowed_orgs = set(get_org_memberships(current_user))

        # Use requested orgs if present and valid; otherwise, default to all
        if requested_org_ids:
            valid_org_ids = requested_org_ids & allowed_orgs
        else:
            valid_org_ids = allowed_orgs

        allowed_regions = {get_organization_region(org_id) for org_id in allowed_orgs}

        new_filters.append(
            {
                "field": "organization_id",
                "values": [{"id": org_id} for org_id in valid_org_ids],
                "type": "any",
            }
        )

        new_filters.append(
            {
                "field": "organization.region_id",
                "values": list(allowed_regions),
                "type": "any",
            }
        )

    search_body.filters = new_filters


# POST: /search
async def search_post(search_body: DomainSearchBody, current_user):
    """Handle Elastic Search request with strict authorization."""
    if current_user.invite_pending:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # --- Extract all explicitly requested orgs and regions ---
    filtered_region_ids = set(
        extract_region_ids_from_filters(search_body.filters or [])
    )
    all_requested_orgs = set(extract_org_ids_from_filters(search_body.filters or []))

    # --- Explicit access check before continuing ---
    # return get_org_memberships(current_user)

    unauthorized_orgs = {
        org_id
        for org_id in all_requested_orgs
        if not is_valid_org(org_id, current_user)
    }
    unauthorized_regions = {
        region_id
        for region_id in filtered_region_ids
        if not is_valid_region(region_id, current_user)
    }

    if unauthorized_orgs:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if unauthorized_regions:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # --- Sanitize filters to enforce user scope ---
    clean_and_authorize_filters(search_body, current_user)

    # --- Build and execute Elasticsearch query ---
    es_query = build_request(search_body)
    client = ESClient()
    response = client.search_domains(body=es_query)
    # Format response to match the required structure
    result = {
        "took": response["took"],
        "timed_out": response["timed_out"],
        "_shards": response["_shards"],
        "hits": {
            "total": response["hits"]["total"],
            "max_score": response["hits"].get("max_score"),
            "hits": [
                {
                    "_index": hit["_index"],
                    "_type": hit["_type"],
                    "_id": hit["_id"],
                    "_score": hit.get("_score"),
                    "_source": hit["_source"],
                    "sort": hit.get("sort", []),
                    "inner_hits": hit.get("inner_hits", {}),
                }
                for hit in response["hits"]["hits"]
            ],
        },
        "aggregations": response.get("aggregations", {}),
    }

    return result


# POST: /search/export
async def search_export(search_body: DomainSearchBody, current_user) -> Dict[str, Any]:
    """Export the search results into a CSV and upload to S3."""
    # Block for pending users.
    if current_user.invite_pending:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # --- Extract all explicitly requested orgs and regions ---
    filtered_region_ids = set(
        extract_region_ids_from_filters(search_body.filters or [])
    )
    all_requested_orgs = set(extract_org_ids_from_filters(search_body.filters or []))

    # --- Explicit access check before continuing ---
    unauthorized_orgs = {
        org_id
        for org_id in all_requested_orgs
        if not is_valid_org(org_id, current_user)
    }
    unauthorized_regions = {
        region_id
        for region_id in filtered_region_ids
        if not is_valid_region(region_id, current_user)
    }

    if unauthorized_orgs:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if unauthorized_regions:
        raise HTTPException(status_code=403, detail="Unauthorized")
    clean_and_authorize_filters(search_body, current_user)

    # Fetch results from Elasticsearch
    client = ESClient()
    results = await fetch_all_results_scroll(search_body, client)

    # Process results for CSV
    processed_results = process_results(results)

    # Define CSV fields
    csv_fields = [
        "name",
        "ip",
        "id",
        "ports",
        "products",
        "created_at",
        "updated_at",
        "organization",
        "screenshot",
        "censys_certificates_results",
        "ip_only",
        "vulnerabilities",
        "cloud_hosted",
        "reverse_name",
        "subdomain_source",
        "country",
        "ssl",
        "parent_join",
        "discovered_by",
        "from_cidr",
        "from_root_domain",
        "trustymail_results",
        "asn",
        "synced_at",
        "is_fceb",
        "services",
        "suggest",
    ]

    # Generate CSV content
    csv_content = generate_csv(processed_results, csv_fields)

    # Upload to S3
    s3_client = S3Client()
    try:
        csv_url = s3_client.save_csv(csv_content, "domains")
    except Exception as e:
        LOGGER.exception("S3 upload error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"url": csv_url}
