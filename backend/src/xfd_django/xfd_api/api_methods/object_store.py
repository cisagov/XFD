"""API methods to support Object Store endpoints."""

# Standard Python Libraries
import os

# Third-Party Libraries
from fastapi import HTTPException
from xfd_api.helpers.s3_client import S3Client
from xfd_api.schema_models.object_store import (
    ObjectStorePresignedUrlRequest,
    ObjectStorePresignedUrlResponse,
)

ALLOWED_BUCKETS = os.getenv("ALLOWED_BUCKETS")


def get_object_store_presigned_url(
    request_user, body: ObjectStorePresignedUrlRequest
) -> ObjectStorePresignedUrlResponse:
    """Get presigned Object Store URL.

    Args:
        request_user (_type_): _description_
        body (ObjectStorePresignedUrlRequest): _description_

    Raises:
        HTTPException: _description_

    Returns:
        ObjectStorePresignedUrlResponse: _description_
    """
    if ALLOWED_BUCKETS and body.bucket_name not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=403, detail="Unauthorized bucket access.")

    s3_client = S3Client()
    presigned_url = s3_client.get_presigned_url(
        bucket_name=body.bucket_name, object_key=body.object_key
    )

    return ObjectStorePresignedUrlResponse(url=presigned_url)
