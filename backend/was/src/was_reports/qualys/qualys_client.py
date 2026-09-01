"""Qualys API client boundary for WAS report generation."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from typing import Any, Optional

# First-Party Libraries
from was_reports.utils.qualys_config import (
    QualysCredentials,
    load_qualys_credentials_from_environment,
)


@dataclass(frozen=True)
class QualysRequest:
    """Description of one Qualys API request."""

    endpoint: str
    payload: Optional[str] = None
    http_method: Optional[str] = None


class QualysClient:
    """Small wrapper around the legacy Qualys API connection object."""

    def __init__(self, connection: Any):
        """Initialize the client with a Qualys API connection."""
        self._connection = connection

    def request(self, qualys_request: QualysRequest) -> str:
        """Execute a Qualys request using the legacy connection interface."""
        if qualys_request.payload is None and qualys_request.http_method is None:
            return self._connection.request(qualys_request.endpoint)

        if qualys_request.http_method is None:
            return self._connection.request(
                qualys_request.endpoint,
                qualys_request.payload,
            )

        if qualys_request.payload is None:
            return self._connection.request(
                qualys_request.endpoint,
                http_method=qualys_request.http_method,
            )

        return self._connection.request(
            qualys_request.endpoint,
            qualys_request.payload,
            http_method=qualys_request.http_method,
        )


def create_qualys_client(
    credentials: Optional[QualysCredentials] = None,
) -> QualysClient:
    """Create a Qualys client directly from environment-backed credentials."""
    resolved_credentials = credentials or load_qualys_credentials_from_environment()
    # Third-Party Libraries
    from qualysapi.connector import QGConnector

    connection = QGConnector(
        auth=(resolved_credentials.username, resolved_credentials.password),
        server=resolved_credentials.hostname,
    )
    return QualysClient(connection)
