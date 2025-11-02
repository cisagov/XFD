"""Get Ips per organization."""
# Third-Party Libraries
from xfd_mini_dl.models import Ip


def get_ips_by_cidr(organization_id):
    """
    Retrieve a list of IPs associated with CIDRs owned by the specified organization.

    Filters:
    - The IP's origin_cidr must not be null.
    - The CIDR must belong to the given organization via M2M.
    - The IP must have Shodan results.
    - The IP must be current.
    """
    ip_qs = Ip.objects.filter(
        origin_cidr__isnull=False,
        origin_cidr__organizations__id=organization_id,
        has_shodan_results=True,
        current=True,
    ).values_list("ip", flat=True)

    return list(ip_qs)
