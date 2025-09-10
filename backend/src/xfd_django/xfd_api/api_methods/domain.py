"""Domain API."""

# Standard Python Libraries
import csv
import io
import logging

# Third-Party Libraries
from django.core.paginator import Paginator
from django.db.models import Prefetch
from fastapi import HTTPException, status
from xfd_mini_dl.models import Domain, DomainSearchView, Organization, Service

from ..auth import get_org_memberships, is_global_view_admin
from ..helpers.filter_helpers import apply_domain_filters, sort_direction
from ..helpers.s3_client import S3Client
from ..schema_models.domain import DomainSearch

LOGGER = logging.getLogger(__name__)


def get_domain_by_id(domain_id: str):
    """
    Get domain by id.

    Returns:
        object: a single Domain object.
    """
    try:
        domain = (
            Domain.objects.select_related("organization")
            .prefetch_related(
                "vulnerabilities",
                Prefetch(
                    "services",
                    queryset=Service.objects.only(
                        "id", "port", "service", "last_seen", "products"
                    ),
                ),
            )
            .filter(id=domain_id)
            .first()
        )
    except Exception as e:
        LOGGER.error("Error occurred while fetching domain by ID: %s", e)
        raise HTTPException(status_code=404, detail="Domain not found.")

    try:
        # The Domain model includes related fields (e.g., organization, vulnerabilities, services)
        # which are Django ORM objects themselves and cannot be directly serialized into JSON.
        # Serialize domain object and its relations
        domain_data = {
            "id": domain.id,
            "name": domain.name,
            "ip": domain.ip,
            "created_at": domain.created_at,
            "updated_at": domain.updated_at,
            "country": domain.country,
            "cloud_hosted": domain.cloud_hosted,
            "organization": {
                "id": domain.organization.id,
                "name": domain.organization.name,
            }
            if domain.organization
            else None,
            "vulnerabilities": [
                {
                    "id": vulnerability.id,
                    "scan_source": vulnerability.scan_source,
                    "title": vulnerability.title,
                    "severity": vulnerability.severity,
                    "description": vulnerability.description,
                    "state": vulnerability.state,
                    "created_at": vulnerability.created_at,
                }
                for vulnerability in domain.vulnerabilities.all()
            ],
            "services": [
                {
                    "id": service.id,
                    "port": service.port,
                    "last_seen": service.last_seen,
                    "products": service.products,
                }
                for service in domain.services.all()
            ],
        }
        return domain_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def search_domains(domain_search: DomainSearch, current_user):
    """List domains by search filter."""
    try:
        domains = DomainSearchView.objects.order_by(
            sort_direction(domain_search.sort, domain_search.order)
        )

        # Apply global user permission filters
        if (
            not is_global_view_admin(current_user)
            and not current_user.user_type == "regionalAdmin"
        ):
            orgs = get_org_memberships(current_user)
            if not orgs:
                return [], 0
            domains = domains.filter(organization_id__in=orgs)

        # Regional Admins can only view vulnerabilities in their region
        if current_user.user_type == "regionalAdmin" and current_user.region_id:
            # Get all organization IDs in this region
            region_org_ids = list(
                Organization.objects.filter(
                    region_id=current_user.region_id
                ).values_list("id", flat=True)
            )

            domains = domains.filter(organization_id__in=region_org_ids)

        # Apply filters if provided
        if domain_search.filters:
            domains = apply_domain_filters(domains, domain_search.filters)

        # Handle pagination
        page_size = domain_search.pageSize
        if page_size == -1:
            page_obj = domains
        else:
            page_size = page_size or 15
            paginator = Paginator(domains, page_size)
            page_obj = paginator.get_page(domain_search.page)

        # Build result
        result = []
        for d in page_obj:
            result.append(
                {
                    "id": d.domain_id,
                    "name": d.name,
                    "ip": d.ip,
                    "created_at": d.created_at,
                    "updated_at": d.updated_at,
                    "country": d.country,
                    "cloud_hosted": d.cloud_hosted,
                    "organization": {
                        "id": d.organization_id,
                        "name": d.organization_name,
                    },
                    "ports_preview": d.ports_preview,
                    "services_preview": d.services_preview,
                    "services_count": d.services_count,
                    "vulnerabilities_count": d.vulnerabilities_count,
                    "webpages": 0,
                }
            )

        # Return
        if page_size == -1:
            return result, len(result)
        else:
            return result, paginator.count

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def export_domains(domain_search: DomainSearch, current_user):
    """Export domains into a CSV and upload to S3."""
    try:
        # Set pageSize to -1 to fetch all domains without pagination
        domain_search.page_size = -1

        # Fetch domains using search_domains function
        domains, count = search_domains(domain_search, current_user)

        # If no domains, generate empty CSV
        if not domains:
            csv_content = "name,ip,id,createdAt,updatedAt,organization\n"
        else:
            # Process domains to flatten organization name,
            # ports as string, products as unique string
            processed_domains = []
            for domain in domains:
                organization_name = (
                    domain.organization.name if domain.organization else ""
                )

                processed_domains.append(
                    {
                        "name": domain.name,
                        "ip": domain.ip,
                        "id": str(domain.id),
                        "created_at": domain.created_at.isoformat()
                        if domain.created_at
                        else "",
                        "updated_at": domain.updated_at.isoformat()
                        if domain.updated_at
                        else "",
                        "organization": organization_name,
                    }
                )

            # Define CSV fields
            csv_fields = [
                "name",
                "ip",
                "id",
                "created_at",
                "updated_at",
                "organization",
            ]

            # Generate CSV content using csv module
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=csv_fields)
            writer.writeheader()
            for domain in processed_domains:
                writer.writerow(domain)
            csv_content = output.getvalue()

        # Initialize S3 client
        client = S3Client()

        # Save CSV to S3
        url = client.save_csv(csv_content, "domains")

        return {"url": url}

    except Exception as e:
        # Log the exception for debugging (optional)
        LOGGER.error("Error exporting domains: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
