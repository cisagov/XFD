"""Cpe API."""

# Third-Party Libraries
from fastapi import HTTPException

# from xfd_api.schema_models import Cpe
from xfd_mini_dl.models import Cpe


def get_cpes_by_id(cpe_id):
    """Get Cpe by id."""
    try:
        cpe = Cpe.objects.get(id=cpe_id)
        return cpe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
