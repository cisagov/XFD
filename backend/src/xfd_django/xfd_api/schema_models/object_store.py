"""Schema to support Object Store API endpoints."""

# Third-Party Libraries
from pydantic import BaseModel, Field


class ObjectStorePresignedUrlRequest(BaseModel):
    """Object Store Presigned Url Request Model.

    Args:
        BaseModel (_type_): _description_
    """

    bucket_name: str = Field(..., description="Name of the bucket")
    object_key: str = Field(..., description="Key (path) to the object")


class ObjectStorePresignedUrlResponse(BaseModel):
    """Object Store Presigned Url Response Model.

    Args:
        BaseModel (_type_): _description_
    """

    url: str = Field(..., description="Presigned URL for accessing the object")
