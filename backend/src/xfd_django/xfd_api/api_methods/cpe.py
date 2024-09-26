"""
Cpe API.

"""

# Third-Party Libraries
from fastapi import HTTPException

from ..models import Cpe


def get_cpes_by_id(cpe_id):
    """
    Get Cpe by id.
    Returns:
        object: a single Cpe object.
    """
    try:
        cpe = Cpe.objects.get(id=cpe_id)
        return cpe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
