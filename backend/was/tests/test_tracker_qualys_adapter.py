"""Tests for the tracker Qualys compatibility adapter."""

# Standard Python Libraries
import sys
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
from lxml.builder import E

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysRequest
from was_reports.tracker.qualys_adapter import (
    SETUP_MODULE_NAME,
    TrackerQualysAdapter,
    install_tracker_setup_module,
)


class TrackerQualysAdapterTests(unittest.TestCase):
    """Validate tracker calls through the environment-backed client."""

    def tearDown(self) -> None:
        """Remove the injected compatibility module after each test."""
        sys.modules.pop(SETUP_MODULE_NAME, None)

    def test_request_converts_xml_and_delegates_to_qualys_client(self) -> None:
        """Convert tracker XML builders into WAS-owned Qualys requests."""
        client = Mock()
        client.request.return_value = "<ServiceResponse />"
        adapter = TrackerQualysAdapter(client)
        request_xml = E.ServiceRequest(E.filters())

        response = adapter.request(
            "search/was/wasscan",
            request_xml,
            http_method="post",
        )

        self.assertEqual(response, "<ServiceResponse />")
        qualys_request = client.request.call_args.args[0]
        self.assertEqual(
            qualys_request,
            QualysRequest(
                endpoint="search/was/wasscan",
                payload="<ServiceRequest><filters/></ServiceRequest>",
                http_method="post",
            ),
        )

    @patch(
        "was_reports.tracker.qualys_adapter.create_qualys_client"
    )
    def test_install_uses_environment_backed_client(
        self,
        mock_create_qualys_client,
    ) -> None:
        """Install tracker dependencies without creating a config file."""
        client = Mock()
        mock_create_qualys_client.return_value = client

        setup_module = install_tracker_setup_module()

        mock_create_qualys_client.assert_called_once_with()
        self.assertIs(sys.modules[SETUP_MODULE_NAME], setup_module)
        self.assertIs(setup_module.qgc.client, client)
        self.assertTrue(callable(setup_module.log_exception))


if __name__ == "__main__":
    unittest.main()
