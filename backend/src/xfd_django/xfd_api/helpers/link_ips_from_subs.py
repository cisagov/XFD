"""Link sub-domains and IPs from sub-domain lookups."""
# Standard Python Libraries
import datetime
import logging
import socket

# Third-Party Libraries
from django.core.exceptions import ObjectDoesNotExist
import dns.resolver
from xfd_api.helpers.asset_inserts import create_or_update_ip
from xfd_mini_dl.models import Cidr, Organization, SubDomains

LOGGER = logging.getLogger(__name__)
DATE = datetime.datetime.now(datetime.timezone.utc)


def get_matching_cidr(ip, org):
    """Return cidr that contains the ip owned by the org."""
    try:
        # Use .get() to find a single CIDR network that contains the IP
        matching_cidr = Cidr.objects.get(
            network__net_contains_or_equals=ip,  # PostgreSQL `<<` operator is used internally for the "contains" query
            cidrorgs__organization=org,
            cidrorgs__current=True,
        )
        return matching_cidr
    except ObjectDoesNotExist:
        # If no matching CIDR is found, return None
        return None
    except Exception as e:
        LOGGER.warning(e)
        return None


def resolve_domain(domain, nameservers=None):
    """Identify ips linked to a given domain."""
    ip_addresses = set()
    if not nameservers:
        nameservers = ["8.8.8.8"]
    # Create a resolver instance and optionally set a custom DNS server
    resolver = dns.resolver.Resolver()

    # If custom DNS servers are provided, use them
    if nameservers:
        resolver.nameservers = nameservers

    try:
        # Resolve IPv4 addresses (A records)
        ipv4_answers = dns.resolver.resolve(domain, "A")
        for rdata in ipv4_answers:
            ip_addresses.add((rdata.address, "IPv4"))
    except dns.resolver.NoAnswer:
        pass
    except dns.exception.DNSException:
        pass

    try:
        # Resolve IPv6 addresses (AAAA records)
        ipv6_answers = dns.resolver.resolve(domain, "AAAA")
        for rdata in ipv6_answers:
            ip_addresses.add((rdata.address, "IPv6"))
    except dns.resolver.NoAnswer:
        pass
    except dns.exception.DNSException:
        pass

    return ip_addresses


def get_ips_and_type_dns(subdomain, org):
    """Get Ips associated with a provided sub-domain using dns.resolver."""
    ip_info = []
    ip_set = resolve_domain(subdomain, ["8.8.8.8", "8.8.4.4"])
    for ip_address, version in ip_set:
        cidr = get_matching_cidr(ip_address, org)
        if cidr:
            LOGGER.warning(
                "Found matching cidr for %s: %s", str(ip_address), cidr.network
            )
            ip_info.append((ip_address, version, cidr))
    return ip_info


def get_ips_and_type_socket(subdomain, org):
    """Get Ips associated with a provided sub-domain using socket."""
    # Initialize an empty list to store results
    ip_info = []

    try:
        # Get address information for the subdomain
        results = socket.getaddrinfo(subdomain, None)

        # Iterate over the results and classify each IP
        for result in results:
            family, socktype, proto, canonname, sockaddr = result

            ip_address = sockaddr[0]

            cidr = get_matching_cidr(ip_address, org)
            if cidr:
                LOGGER.info(
                    "Found matching cidr for %s: %s", str(ip_address), cidr.network
                )

            # Check if the address family is AF_INET (IPv4) or AF_INET6 (IPv6)
            if family == socket.AF_INET:
                ip_type = "IPv4"
            elif family == socket.AF_INET6:
                ip_type = "IPv6"
            else:
                continue

            # Append the IP and type as a tuple to the list
            ip_info.append((ip_address, ip_type))

    except socket.gaierror as e:
        LOGGER.error("Error resolving the subdomain %s: %s", subdomain, e)

    return ip_info


def link_ip_from_domain(sub, org):
    """Link IP from domain."""
    ips = get_ips_and_type_dns(sub.sub_domain, org)

    if not ips:
        return 0
    for ip, ip_type, cidr in ips:
        create_or_update_ip(
            {
                "ip": str(ip),
                "organization": org,
                "ip_version": ip_type,
                "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
                "current": True,
                "from_cidr": True,
                "origin_cidr": cidr,
            },
            {
                "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
                "current": True,
            },
            sub,
        )

    return 1


def connect_ips_from_subs(orgs_list=list[Organization]):
    """For each org, find all ips associated with its sub_domains and link them in the ips_subs table."""
    # Get P&E organizations DataFram
    LOGGER.info("Linking Ips from subdomains")
    # num_orgs = len(orgs_list)

    # Loop through orgs
    org_count = 1
    for org in orgs_list:
        # Connect to database
        # LOGGER.warning(
        #     "Linkingon %s, %d/%d",
        #     org.acronym,
        #     org_count,
        #     num_orgs,
        # )

        # Query sub-domains
        subdomains = SubDomains.objects.filter(current=True, organization=org)
        LOGGER.info("Number of Sub-domains: %d", len(subdomains))

        for sub_row in subdomains:
            sub_domain = sub_row.sub_domain
            if sub_domain == "Null_Sub":
                continue
            link_ip_from_domain(sub_row, org)

        org_count += 1
