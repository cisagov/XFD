"""Guarded Qualys administration operations for WAS resources."""

# Standard Python Libraries
from typing import Iterable

# Third-Party Libraries
from lxml import etree
from lxml.builder import E

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, QualysRequest


def _serialize_xml(root: etree._Element) -> str:
    """Serialize an XML request while preserving escaped operator input."""
    return etree.tostring(root, encoding="unicode")


def _parse_response(response_xml: str, operation: str) -> etree._Element:
    """Validate a Qualys mutation response and return its parsed root."""
    try:
        root = etree.fromstring(response_xml.encode("utf-8"))
    except etree.XMLSyntaxError as error:
        raise RuntimeError(
            "Qualys returned invalid XML for {}.".format(operation)
        ) from error

    response_code = root.findtext("responseCode")
    if response_code != "SUCCESS":
        raise RuntimeError(
            "Qualys {} failed with response code {}.".format(
                operation,
                response_code or "UNKNOWN",
            )
        )
    return root


def build_webapp_lookup_payload(webapp_url: str) -> str:
    """Build a Qualys request that finds a web application by exact URL."""
    return _serialize_xml(
        E.ServiceRequest(
            E.filters(
                E.Criteria(webapp_url, field="url", operator="EQUALS"),
            )
        )
    )


def find_webapp_id(client: QualysClient, webapp_url: str) -> str:
    """Return the Qualys web application ID for an exact URL."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/search/was/webapp",
            payload=build_webapp_lookup_payload(webapp_url),
            http_method="POST",
        )
    )
    try:
        root = etree.fromstring(response_xml.encode("utf-8"))
    except etree.XMLSyntaxError as error:
        raise RuntimeError(
            "Qualys returned invalid XML while finding the web application."
        ) from error

    webapp_id = root.findtext("./data/WebApp/id")
    if not webapp_id:
        raise LookupError("Qualys did not find the supplied web application URL.")
    return webapp_id


def build_tag_update_payload(tag_id: str, action: str) -> str:
    """Build an add or remove tag request for a Qualys web application."""
    if action not in {"add", "remove"}:
        raise ValueError("Tag update action must be add or remove.")
    tag_action = etree.Element(action)
    tag_action.append(E.Tag(E.id(tag_id)))
    return _serialize_xml(
        E.ServiceRequest(
            E.data(
                E.WebApp(
                    E.tags(tag_action),
                )
            )
        )
    )


def update_webapp_tag(
    client: QualysClient,
    webapp_id: str,
    tag_id: str,
    action: str,
) -> None:
    """Add or remove one Qualys tag from a web application."""
    response_xml = client.request(
        QualysRequest(
            endpoint="update/was/webapp/{}".format(webapp_id),
            payload=build_tag_update_payload(tag_id, action),
            http_method="POST",
        )
    )
    _parse_response(response_xml, "web application tag update")


def build_false_positive_payload(finding_id: str, comment: str) -> str:
    """Build a request that marks one Qualys finding as a false positive."""
    return _serialize_xml(
        E.ServiceRequest(
            E.data(
                E.Finding(
                    E.id(finding_id),
                    E.ignoredReason("FALSE_POSITIVE"),
                    E.ignoredComment(comment),
                )
            )
        )
    )


def mark_false_positive(
    client: QualysClient,
    finding_id: str,
    comment: str,
) -> None:
    """Mark one Qualys WAS finding as a false positive."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/ignore/was/finding",
            payload=build_false_positive_payload(finding_id, comment),
            http_method="POST",
        )
    )
    _parse_response(response_xml, "false-positive update")


def build_delete_webapp_payload(webapp_url: str) -> str:
    """Build a request that deletes a web application by exact URL."""
    return _serialize_xml(
        E.ServiceRequest(
            E.filters(
                E.Criteria(webapp_url, field="url", operator="EQUALS"),
            ),
            E.data(
                E.WebApp(
                    E.removeFromSubscription("true"),
                )
            ),
        )
    )


def delete_webapp(client: QualysClient, webapp_url: str) -> None:
    """Delete one Qualys web application and remove its subscription."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/delete/was/webapp",
            payload=build_delete_webapp_payload(webapp_url),
            http_method="POST",
        )
    )
    _parse_response(response_xml, "web application deletion")


def build_reactivate_webapp_payload(
    webapp_url: str,
    tag_ids: Iterable[str],
) -> str:
    """Build a request that reactivates a web application with tags."""
    normalized_tag_ids = list(tag_ids)
    if not normalized_tag_ids:
        raise ValueError("At least one Qualys tag ID is required.")
    tag_set = E.set(*(E.Tag(E.id(tag_id)) for tag_id in normalized_tag_ids))
    return _serialize_xml(
        E.ServiceRequest(
            E.data(
                E.WebApp(
                    E.name(webapp_url),
                    E.url(webapp_url),
                    E.reactivateIfExists("true"),
                    E.tags(tag_set),
                )
            )
        )
    )


def reactivate_webapp(
    client: QualysClient,
    webapp_url: str,
    tag_ids: Iterable[str],
) -> None:
    """Reactivate one Qualys web application and replace its tag set."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/create/was/webapp",
            payload=build_reactivate_webapp_payload(webapp_url, tag_ids),
            http_method="POST",
        )
    )
    _parse_response(response_xml, "web application reactivation")
