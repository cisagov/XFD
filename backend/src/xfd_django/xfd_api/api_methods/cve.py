"""
Cve API.

"""

# Third-Party Libraries
from fastapi import HTTPException

from ..models import Cve


def get_cves_by_id(cve_id):
    """
    Get Cve by id.
    Returns:
        object: a single Cve object.
    """
    try:
        cve = Cve.objects.get(id=cve_id)
        return cve
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_cves_by_name(cve_name):
    """
    Get Cve by name.
    Returns:
        object: a single Cpe object.
    """
    try:
        cve = Cve.objects.get(name=cve_name)
        return cve
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
