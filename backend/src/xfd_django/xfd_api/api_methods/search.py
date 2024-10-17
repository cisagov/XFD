# api_methods/search.py
# Standard Python Libraries
import csv
from io import StringIO
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
import boto3
from elasticsearch import Elasticsearch
from fastapi import HTTPException
from pydantic import BaseModel
from xfd_api.auth import (
    get_org_memberships,
    get_tag_organizations,
    is_global_view_admin,
)
from xfd_api.helpers.elastic_search import build_request


class Filter(BaseModel):
    field: str
    values: List[str]
    type: str


class SearchBody(BaseModel):
    current: int
    results_per_page: int
    search_term: str
    sort_direction: str
    sort_field: str
    filters: List[Filter]
    organization_ids: Optional[List[UUID]] = None
    organization_id: Optional[UUID] = None
    tag_id: Optional[UUID] = None


def get_options(search_body: SearchBody, event) -> Dict[str, Any]:
    """Determine options for filtering based on organization ID or tag ID."""
    if search_body.organizationId and (
        search_body.organizationId in get_org_memberships(event)
        or is_global_view_admin(event)
    ):
        options = {
            "organizationIds": [search_body.organizationId],
            "matchAllOrganizations": False,
        }
    elif search_body.tagId:
        options = {
            "organizationIds": get_tag_organizations(event, search_body.tagId),
            "matchAllOrganizations": False,
        }
    else:
        options = {
            "organizationIds": get_org_memberships(event),
            "matchAllOrganizations": is_global_view_admin(event),
        }
    return options


def fetch_all_results(
    filters: Dict[str, Any], options: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Fetch all search results from Elasticsearch."""
    client = Elasticsearch()
    RESULTS_PER_PAGE = 1000
    results = []
    current = 1
    while True:
        request = build_request(
            {**filters, "current": current, "resultsPerPage": RESULTS_PER_PAGE}, options
        )
        current += 1
        try:
            search_results = client.search(index="domains", body=request)
        except Exception as e:
            print(f"Elasticsearch search error: {e}")
            continue
        if len(search_results["hits"]["hits"]) == 0:
            break
        results.extend([res["_source"] for res in search_results["hits"]["hits"]])
    return results


def export(search_body: SearchBody, event) -> Dict[str, Any]:
    """Export the search results into a CSV and upload to S3."""
    options = get_options(search_body, event)
    results = fetch_all_results(search_body.dict(), options)

    # Process results for CSV
    for res in results:
        res["organization"] = res.get("organization", {}).get("name", "")
        res["ports"] = ", ".join(
            [str(service["port"]) for service in res.get("services", [])]
        )
        products = {}
        for service in res.get("services", []):
            for product in service.get("products", []):
                if product.get("name"):
                    products[product["name"].lower()] = product["name"] + (
                        f" {product['version']}" if product.get("version") else ""
                    )
        res["products"] = ", ".join(products.values())

    # Create CSV
    csv_buffer = StringIO()
    fieldnames = [
        "name",
        "ip",
        "id",
        "ports",
        "products",
        "createdAt",
        "updatedAt",
        "organization",
    ]
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

    # Save to S3 # TODO: Replace with heler logic
    s3 = boto3.client("s3")
    bucket_name = "your-bucket-name"
    csv_key = "domains.csv"
    s3.put_object(Bucket=bucket_name, Key=csv_key, Body=csv_buffer.getvalue())

    # Generate a presigned URL to access the CSV
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": csv_key}, ExpiresIn=3600
    )

    return {"url": url}


def search(search_body: SearchBody, event) -> Dict[str, Any]:
    """Perform a search on Elasticsearch and return results."""
    options = get_options(search_body, event)
    request = build_request(search_body.dict(), options)

    client = Elasticsearch()
    try:
        search_results = client.search(index="domains", body=request)
    except Exception as e:
        print(f"Elasticsearch search error: {e}")
        raise HTTPException(status_code=500, detail="Elasticsearch query failed")

    return search_results["hits"]
