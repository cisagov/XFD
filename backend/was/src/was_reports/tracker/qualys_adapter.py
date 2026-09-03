"""Adapt legacy tracker Qualys calls to the WAS-owned API client."""

# Standard Python Libraries
import logging
import sys
from types import ModuleType
from typing import Any

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.qualys.qualys_client import (
    QualysClient,
    QualysRequest,
    create_qualys_client,
)

LOGGER = logging.getLogger(__name__)
SETUP_MODULE_NAME = "set_up"


class TrackerQualysAdapter:
    """Expose the tracker request interface through the WAS Qualys client."""

    def __init__(self, client: QualysClient) -> None:
        """Initialize the adapter with a WAS-owned Qualys client."""
        self.client = client

    def request(
        self,
        api_call: str,
        data: Any = None,
        http_method: str | None = None,
    ) -> str:
        """Execute one tracker request using environment-backed credentials."""
        payload = data
        if etree.iselement(data):
            payload = etree.tostring(data).decode("utf-8")
        return self.client.request(
            QualysRequest(
                endpoint=api_call,
                payload=payload,
                http_method=http_method,
            )
        )


def log_tracker_exception(exception: Exception, **context: Any) -> None:
    """Log tracker failures and non-sensitive operational context to stdout."""
    LOGGER.error(
        "WAS tracker operation failed with %s. Context: %s",
        type(exception).__name__,
        context,
        exc_info=exception,
    )


def install_tracker_setup_module(
    client: QualysClient | None = None,
) -> ModuleType:
    """Install an in-memory tracker setup module without filesystem config."""
    setup_module = ModuleType(SETUP_MODULE_NAME)
    setup_module.qgc = TrackerQualysAdapter(client or create_qualys_client())
    setup_module.log_exception = log_tracker_exception
    sys.modules[SETUP_MODULE_NAME] = setup_module
    return setup_module
