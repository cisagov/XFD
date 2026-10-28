"""Guarded Qualys administration operations for WAS resources."""

# Standard Python Libraries
from dataclasses import dataclass
from typing import Iterable

# Third-Party Libraries
# lxml is required for response types; all parsing uses the hardened helper below.
from lxml import etree  # nosec B410

# E only constructs escaped outbound XML and never parses input.
from lxml.builder import E  # nosec B410

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, QualysRequest


@dataclass(frozen=True)
class WebAppIdentity:
    """Qualys identity and tag associations for one exact web application."""

    webapp_id: str
    webapp_url: str
    tag_ids: tuple[str, ...]


class WebAppLookupCardinalityError(LookupError):
    """Indicate that an exact URL lookup did not return exactly one web app."""


class WebAppIdMissingError(LookupError):
    """Indicate that Qualys omitted the selected web application's ID."""


class WebAppUrlMismatchError(LookupError):
    """Indicate that Qualys returned a URL other than the requested exact URL."""


class WebAppTagDetailsMissingError(LookupError):
    """Indicate that Qualys omitted verbose tag IDs for the selected web app."""


def _serialize_xml(root: etree._Element) -> str:
    """Serialize an XML request while preserving escaped operator input."""
    return etree.tostring(root, encoding="unicode")


def _parse_xml(response_xml: str, error_message: str) -> etree._Element:
    """Parse one Qualys response without resolving DTDs or external entities."""
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        attribute_defaults=False,
        huge_tree=False,
    )
    try:
        # The parser disables DTD loading, entity resolution, and network access.
        root = etree.fromstring(  # nosec B320
            response_xml.encode("utf-8"),
            parser=parser,
        )
    except etree.XMLSyntaxError as error:
        raise RuntimeError(error_message) from error
    if root.getroottree().docinfo.doctype:
        raise RuntimeError(
            "{} DOCTYPE declarations are prohibited.".format(error_message)
        )
    return root


def _parse_response(response_xml: str, operation: str) -> etree._Element:
    """Validate a Qualys mutation response and return its parsed root."""
    root = _parse_xml(
        response_xml,
        "Qualys returned invalid XML for {}.".format(operation),
    )

    response_code = root.findtext("responseCode")
    if response_code != "SUCCESS":
        raise RuntimeError(
            "Qualys {} failed with response code {}.".format(
                operation,
                response_code or "UNKNOWN",
            )
        )
    return root


def build_webapp_lookup_payload(
    webapp_url: str,
    include_tag_details: bool = False,
) -> str:
    """Build an exact URL search, optionally requesting associated tag details."""
    request_elements = []
    if include_tag_details:
        request_elements.append(E.preferences(E.verbose("true")))
    request_elements.append(
        E.filters(
            E.Criteria(webapp_url, field="url", operator="EQUALS"),
        )
    )
    return _serialize_xml(E.ServiceRequest(*request_elements))


def find_webapp_id(client: QualysClient, webapp_url: str) -> str:
    """Return the Qualys web application ID for an exact URL."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/search/was/webapp",
            payload=build_webapp_lookup_payload(webapp_url),
            http_method="POST",
        )
    )
    root = _parse_xml(
        response_xml,
        "Qualys returned invalid XML while finding the web application.",
    )

    webapp_id = root.findtext("./data/WebApp/id")
    if not webapp_id:
        raise LookupError("Qualys did not find the supplied web application URL.")
    return webapp_id


def find_webapp_identity(client: QualysClient, webapp_url: str) -> WebAppIdentity:
    """Return one unambiguous exact-URL identity with its current tag IDs."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/search/was/webapp",
            payload=build_webapp_lookup_payload(
                webapp_url,
                include_tag_details=True,
            ),
            http_method="POST",
        )
    )
    root = _parse_xml(
        response_xml,
        "Qualys returned invalid XML while validating the web application.",
    )
    webapps = root.findall("./data/WebApp")
    if (root.findtext("count") or "").strip() != "1" or len(webapps) != 1:
        raise WebAppLookupCardinalityError(
            "Qualys exact URL lookup did not return exactly one web application."
        )
    webapp = webapps[0]
    returned_id = (webapp.findtext("id") or "").strip()
    returned_url = (webapp.findtext("url") or "").strip()
    tag_ids = tuple(
        dict.fromkeys(
            value.strip()
            for value in webapp.xpath("./tags//Tag/id/text()")
            if value.strip()
        )
    )
    if not returned_id:
        raise WebAppIdMissingError(
            "Qualys omitted the web application ID from the exact URL lookup."
        )
    if returned_url != webapp_url:
        raise WebAppUrlMismatchError(
            "Qualys returned a web application URL that did not exactly match."
        )
    if not tag_ids:
        raise WebAppTagDetailsMissingError(
            "Qualys omitted verbose web application tag IDs."
        )
    return WebAppIdentity(returned_id, returned_url, tag_ids)


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


def build_delete_webapp_payload(webapp_url: str, webapp_id: str | None = None) -> str:
    """Build a request that deletes an exact URL and optional stable identity."""
    criteria = [E.Criteria(webapp_url, field="url", operator="EQUALS")]
    if webapp_id is not None:
        criteria.append(E.Criteria(webapp_id, field="id", operator="EQUALS"))
    return _serialize_xml(
        E.ServiceRequest(
            E.filters(*criteria),
            E.data(
                E.WebApp(
                    E.removeFromSubscription("true"),
                )
            ),
        )
    )


def delete_webapp(
    client: QualysClient,
    webapp_url: str,
    webapp_id: str | None = None,
) -> None:
    """Delete one exact Qualys identity and remove its subscription."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/delete/was/webapp",
            payload=build_delete_webapp_payload(webapp_url, webapp_id),
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
