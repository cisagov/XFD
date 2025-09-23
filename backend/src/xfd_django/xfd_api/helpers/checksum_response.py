"""Helper to build a JSONResponse with a checksum header."""
# Standard Python Libraries
import hashlib
import json
import os

# Third-Party Libraries
from fastapi import Response, status
from fastapi.responses import JSONResponse

SALT = os.getenv("CHECKSUM_SALT", "default_salt")


def build_checksum_response(
    response_body: dict,
    response: Response,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    """
    Build a JSONResponse with an X-Salted-Checksum header.

    Args:
        response_body: Dictionary to serialize and include in the response.
        response: FastAPI Response object (headers will be updated).
        status_code: HTTP status code to return (default 200).

    Returns:
        JSONResponse with body and checksum header.
    """
    serialized = json.dumps(response_body, default=str, sort_keys=True)
    checksum = hashlib.sha256((SALT + serialized).encode()).hexdigest()
    response.headers["X-Salted-Checksum"] = checksum

    return JSONResponse(
        status_code=status_code,
        content=response_body,
        headers={"X-Salted-Checksum": checksum},
    )
