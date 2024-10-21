# Third-Party Libraries
from fastapi import HTTPException

from ..models import Domain, Organization, Service, Vulnerability
from ..schema_models.domain import Domain, DomainFilters
from ..schema_models.vulnerability import Vulnerability, VulnerabilityFilters


def sort_direction(sort, order):
    """
    Adds the sort direction modifier.
    If sort =
        ASC - return order field unmodified to sort in ascending order.
        DSC - returns & prepend '-' to the order field to sort in descending order.
    """
    try:
        # Fetch all domains in list
        if sort == "ASC":
            return order
        elif sort == "DSC":
            return "-" + order
        else:
            raise ValueError
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Invalid sort direction supplied")


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
        print("DEBUG")
        if domain_filters.port:
            print(f"port: {domain_filters.port}")
            services_by_port = Service.objects.values("domainId").filter(
                port=domain_filters.port
            )
            if services_by_port.exists():
                domains = domains.filter(id__in=services_by_port)
        if domain_filters.service:
            print(f"service: {domain_filters.service}")
            service_by_id = Service.objects.values("domainId").filter(
                id__in=domain_filters.service
            )
            if service_by_id.exists():
                domains = domains.filter(id=service_by_id)
        if domain_filters.reverseName:
            print(f"reverseName: {domain_filters.reverseName}")
            domains_by_reverse_name = Domain.objects.values("id").filter(
                reverseName=domain_filters.reverseName
            )
            if domains_by_reverse_name.exists():
                domains = domains.filter(id__in=domains_by_reverse_name)
        if domain_filters.ip:
            print(f"ip: {domain_filters.ip}")
            domains_by_ip = Domain.objects.values("id").filter(ip=domain_filters.ip)
            if domains_by_ip.exists():
                domains = domains.filter(id__in=domains_by_ip)
        if domain_filters.organization:
            print(f"organization: {domain_filters.organization}")
            domains_by_org = Domain.objects.values("id").filter(
                organizationId_id=domain_filters.organization
            )
            if domains_by_org.exists():
                domains = domains.filter(id__in=domains_by_org)
        if domain_filters.organizationName:
            print(f"organizationName: {domain_filters.organizationName}")
            organization_by_name = Organization.objects.values("id").filter(
                name=domain_filters.organizationName
            )
            if organization_by_name.exists():
                domains = domains.filter(organizationId_id__in=organization_by_name)
        if domain_filters.vulnerabilities:
            print(f"vulnerabilities: {domain_filters.vulnerabilities}")
            vulnerabilities_by_id = Vulnerability.objects.values("domainId").filter(
                id=domain_filters.vulnerabilities
            )
            if vulnerabilities_by_id.exists():
                domains = domains.filter(id__in=vulnerabilities_by_id)

        return domains
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def filter_vulnerabilities(
    vulnerabilities, vulnerability_filters: VulnerabilityFilters
):
    """
    Filter vulnerabilitie
    Arguments:
        vulnerabilities: A list of all vulnerabilities, sorted
        vulnerability_filters: Value to filter the vulnberabilities table by
    Returns:
        object: a list of Vulnerability objects
    """
    try:
        if vulnerability_filters.id:
            print(f"id: {vulnerability_filters.id}")
            vulnerability_by_id = Vulnerability.objects.values("id").get(
                id=vulnerability_filters.id
            )
            vulnerabilities = vulnerabilities.filter(id=vulnerability_by_id("id"))
        if vulnerability_filters.title:
            print(f"title: {vulnerability_filters.title}")
            vulnerabilities_by_title = Vulnerability.objects.values("id").filter(
                title=vulnerability_filters.title
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_title)
        if vulnerability_filters.domain:
            print(f"domain: {vulnerability_filters.domain}")
            vulnerabilities_by_domain = Vulnerability.objects.values("id").filters(
                domainId=vulnerability_filters.domain
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_domain)
        if vulnerability_filters.severity:
            print(f"severity: {vulnerability_filters.severity}")
            vulnerabilities_by_severity = Vulnerability.objects.values("id").filter(
                severity=vulnerability_filters.severity
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_severity)
        if vulnerability_filters.cpe:
            print(f"cpe: {vulnerability_filters.cpe}")
            vulnerabilities_by_cpe = Vulnerability.objects.values("id").filter(
                cpe=vulnerability_filters.cpe
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_cpe)
        if vulnerability_filters.state:
            print(f"state: {vulnerability_filters.state}")
            vulnerabilities_by_state = Vulnerability.objects.values("id").filter(
                state=vulnerability_filters.state
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_state)
        if vulnerability_filters.organization:
            print(f"organization: {vulnerability_filters.organization}")
            domains = Domain.objects.all()
            domains_by_organization = Domain.objects.values("id").filter(
                organizationId_id=vulnerability_filters.organization
            )
            domains = domains.filter(id__in=domains_by_organization)
            vulnerabilities_by_domain = Vulnerability.objects.values("id").filter(
                id__in=domains
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_domain)
        if vulnerability_filters.isKev:
            print(f"isKev: {vulnerability_filters.isKev}")
            vulnerabilities_by_is_kev = Vulnerability.objects.values("id").filter(
                isKev=vulnerability_filters.isKev
            )
            vulnerabilities = vulnerabilities.filter(id__in=vulnerabilities_by_is_kev)
            print(f"vulnerabilities: {vulnerabilities}")
        return vulnerabilities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
