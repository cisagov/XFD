"""Tests for guarded Qualys WAS administration operations."""

# Standard Python Libraries
import unittest
from unittest.mock import Mock

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.qualys.qualys_admin import (
    build_delete_webapp_payload,
    build_false_positive_payload,
    build_reactivate_webapp_payload,
    build_tag_update_payload,
    build_webapp_lookup_payload,
    delete_webapp,
    find_webapp_id,
    mark_false_positive,
    reactivate_webapp,
    update_webapp_tag,
)
from was_reports.qualys.qualys_client import QualysRequest


SUCCESS_RESPONSE = "<ServiceResponse><responseCode>SUCCESS</responseCode></ServiceResponse>"


class QualysAdminTests(unittest.TestCase):
    """Validate Qualys administration payloads and API calls."""

    def test_webapp_lookup_payload_escapes_url_characters(self) -> None:
        """Escape URL query characters instead of permitting XML injection."""
        payload = build_webapp_lookup_payload(
            "https://example.gov/path?first=1&second=<value>"
        )
        root = etree.fromstring(payload.encode("utf-8"))

        self.assertEqual(
            root.findtext("./filters/Criteria"),
            "https://example.gov/path?first=1&second=<value>",
        )
        self.assertIn("&amp;", payload)
        self.assertIn("&lt;value&gt;", payload)

    def test_find_webapp_id_uses_exact_legacy_search(self) -> None:
        """Find a web application through the exact URL search endpoint."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><count>1</count><data><WebApp><id>42</id>"
            "</WebApp></data></ServiceResponse>"
        )

        result = find_webapp_id(client, "https://example.gov")

        self.assertEqual(result, "42")
        request = client.request.call_args.args[0]
        self.assertEqual(request.endpoint, "/search/was/webapp")
        self.assertEqual(request.http_method, "POST")

    def test_find_webapp_id_rejects_missing_result(self) -> None:
        """Raise a lookup error when Qualys does not return a web app."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><count>0</count><data/></ServiceResponse>"
        )

        with self.assertRaisesRegex(LookupError, "did not find"):
            find_webapp_id(client, "https://missing.example.gov")

    def test_tag_payload_supports_add_and_remove(self) -> None:
        """Preserve both legacy web application tag mutations."""
        add_root = etree.fromstring(
            build_tag_update_payload("100", "add").encode("utf-8")
        )
        remove_root = etree.fromstring(
            build_tag_update_payload("100", "remove").encode("utf-8")
        )

        self.assertEqual(add_root.findtext("./data/WebApp/tags/add/Tag/id"), "100")
        self.assertEqual(
            remove_root.findtext("./data/WebApp/tags/remove/Tag/id"),
            "100",
        )

    def test_update_webapp_tag_calls_legacy_endpoint(self) -> None:
        """Submit a checked tag mutation to the legacy Qualys endpoint."""
        client = Mock()
        client.request.return_value = SUCCESS_RESPONSE

        update_webapp_tag(client, "42", "100", "add")

        request = client.request.call_args.args[0]
        self.assertEqual(request.endpoint, "update/was/webapp/42")
        self.assertEqual(request.http_method, "POST")

    def test_false_positive_payload_escapes_comment(self) -> None:
        """Safely encode a false-positive comment in the XML payload."""
        payload = build_false_positive_payload("123", "Reviewed & accepted <risk>.")
        root = etree.fromstring(payload.encode("utf-8"))

        self.assertEqual(root.findtext("./data/Finding/id"), "123")
        self.assertEqual(
            root.findtext("./data/Finding/ignoredReason"),
            "FALSE_POSITIVE",
        )
        self.assertEqual(
            root.findtext("./data/Finding/ignoredComment"),
            "Reviewed & accepted <risk>.",
        )

    def test_mark_false_positive_calls_legacy_endpoint(self) -> None:
        """Submit false-positive status through the legacy endpoint."""
        client = Mock()
        client.request.return_value = SUCCESS_RESPONSE

        mark_false_positive(client, "123", "Reviewed.")

        request = client.request.call_args.args[0]
        self.assertEqual(
            request,
            QualysRequest(
                endpoint="/ignore/was/finding",
                payload=build_false_positive_payload("123", "Reviewed."),
                http_method="POST",
            ),
        )

    def test_delete_payload_removes_subscription(self) -> None:
        """Preserve the legacy remove-from-subscription deletion behavior."""
        root = etree.fromstring(
            build_delete_webapp_payload("https://example.gov").encode("utf-8")
        )

        self.assertEqual(root.findtext("./filters/Criteria"), "https://example.gov")
        self.assertEqual(
            root.findtext("./data/WebApp/removeFromSubscription"),
            "true",
        )

    def test_delete_webapp_checks_response(self) -> None:
        """Reject a failed deletion without exposing the full API response."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><responseCode>INVALID_REQUEST</responseCode>"
            "<responseErrorDetails><errorMessage>Denied</errorMessage>"
            "</responseErrorDetails></ServiceResponse>"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "INVALID_REQUEST",
        ):
            delete_webapp(client, "https://example.gov")

    def test_reactivate_payload_sets_all_tags(self) -> None:
        """Preserve reactivation and replacement of the complete tag set."""
        root = etree.fromstring(
            build_reactivate_webapp_payload(
                "https://example.gov",
                ["100", "200"],
            ).encode("utf-8")
        )

        self.assertEqual(root.findtext("./data/WebApp/name"), "https://example.gov")
        self.assertEqual(root.findtext("./data/WebApp/url"), "https://example.gov")
        self.assertEqual(
            root.findtext("./data/WebApp/reactivateIfExists"),
            "true",
        )
        self.assertEqual(
            root.xpath("./data/WebApp/tags/set/Tag/id/text()"),
            ["100", "200"],
        )

        client = Mock()
        client.request.return_value = SUCCESS_RESPONSE
        reactivate_webapp(client, "https://example.gov", ["100"])
        self.assertEqual(
            client.request.call_args.args[0].endpoint,
            "/create/was/webapp",
        )


if __name__ == "__main__":
    unittest.main()
