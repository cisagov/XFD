"""Get root domain per organization."""
# Third-Party Libraries
from django.db.models import Q
from xfd_mini_dl.models import SubDomains


def get_root_domains(organization_id):
    """
    Retrieve the list of root domain names for the specified organization.

    Query SubDomains table where is_root_domain is True and enumerate_subs
    is either True or None.
    """
    root_qs = SubDomains.objects.filter(
        organization__id=organization_id, is_root_domain=True
    ).filter(Q(enumerate_subs=True) | Q(enumerate_subs=None))
    return [sd.sub_domain for sd in root_qs]
