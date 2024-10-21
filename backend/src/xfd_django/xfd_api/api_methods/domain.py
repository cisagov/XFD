"""
Domain API.

"""

# Standard Python Libraries
import csv

# Third-Party Libraries
from django.core.paginator import Paginator
from fastapi import HTTPException

from ..helpers.filter_helpers import filter_domains, sort_direction
from ..models import Domain
from ..schema_models.domain import DomainSearch


def get_domain_by_id(domain_id: str):
    """
    Get domain by id.
    Returns:
        object: a single Domain object.
    """
    try:
        domain = Domain.objects.get(id=domain_id)
        return domain
    except Domain.DoesNotExist:
        raise HTTPException(status_code=404, detail="Domain not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def search_domains(domain_search: DomainSearch):
    """
    List domains by search filter
    Arguments:
        domain_search: A DomainSearch object to filter by.
    Returns:
        object: A paginated list of Domain objects
    """
    try:
        # Fetch all domains in list
        if domain_search.order is not None:
            domains = Domain.objects.all().order_by(
                sort_direction(domain_search.sort, domain_search.order)
            )
        else:
            # Default sort order behavior
            domains = Domain.objects.all()

        if domain_search.filters is not None:
            results = filter_domains(domains, domain_search.filters)
            paginator = Paginator(results, domain_search.pageSize)

            return paginator.get_page(domain_search.page)
        else:
            raise ValueError("DomainFilters cannot be NoneType")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def export_domains(domain_search: DomainSearch):
    try:
        domains = Domain.objects.all().order_by(
            sort_direction(domain_search.sort, domain_search.order)
        )

        if domain_search.filters is not None:
            results = filter_domains(domains, domain_search.filters)
            paginator = Paginator(results, domain_search.pageSize)

            return paginator.get_page(domain_search.page)
            # TODO: Implement S3 client methods after collab with entire team.
            # return export_to_csv(paginator, domains, "testing", True)
        else:
            raise ValueError("DomainFilters cannot be NoneType")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
