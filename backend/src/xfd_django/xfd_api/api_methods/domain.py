"""
Domain API.

"""

# Standard Python Libraries
import csv

# Third-Party Libraries
from django.core.paginator import Paginator
from fastapi import HTTPException

from ..helpers.s3_client import export_to_csv
from ..models import Domain, Organization, Service, Vulnerability
from ..schema_models.domain import DomainFilters, DomainSearch


def filter_domains(domains, domain_filters: DomainFilters):
    """
    Filter domains
    Arguments:
        domains: A list of all domains, sorted
        domain_filters: Value to filter the domains table by
    Returns:
        object: a list of Domain objects
    """
    try:
        if domain_filters.port is not None:
            services_by_port = Service.objects.values("domainId").filter(
                port=domain_filters.port
            )
            domains = domains.filter(id__in=services_by_port)
        if domain_filters.service != "":
            service_by_id = Service.objects.values("domainId").get(
                id=domain_filters.service
            )
            domains = domains.filter(id=service_by_id["domainId"])
        if domain_filters.reverseName != "":
            domains_by_reverse_name = Domain.objects.values("id").filter(
                reverseName=domain_filters.reverseName
            )
            domains = domains.filter(id__in=domains_by_reverse_name)
        if domain_filters.ip != "":
            domains_by_ip = Domain.objects.values("id").filter(ip=domain_filters.ip)
            domains = domains.filter(id__in=domains_by_ip)
        if domain_filters.organization != "":
            domains_by_org = Domain.objects.values("id").filter(
                organizationId_id=domain_filters.organization
            )
            domains = domains.filter(id__in=domains_by_org)
        if domain_filters.organizationName != "":
            organization_by_name = Organization.objects.values("id").filter(
                name=domain_filters.organizationName
            )
            domains = domains.filter(organizationId_id__in=organization_by_name)
        if domain_filters.vulnerabilities != "":
            vulnerabilities_by_id = Vulnerability.objects.values("domainId").filter(
                id=domain_filters.vulnerabilities
            )
            domains = domains.filter(id__in=vulnerabilities_by_id)

        return domains
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


def sort_direction(sort, order):
    try:
        # Fetch all domains in list
        if sort == "ASC":
            return sort
        elif sort == "DSC":
            return "-" + order
        else:
            raise ValueError
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Invalid sort direction supplied")


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
        sort_direction(domain_search.sort, domain_search.order)

        domains = Domain.objects.all().order_by(
            sort_direction(domain_search.sort, domain_search.order)
        )
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

            return export_to_csv(paginator, domains, "testing", True)
        else:
            raise ValueError("DomainFilters cannot be NoneType")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
