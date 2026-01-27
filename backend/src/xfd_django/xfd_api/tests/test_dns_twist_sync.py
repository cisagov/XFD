"""Test dns_twist_sync (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
import hashlib
from http.cookies import SimpleCookie
import json
import os
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_api.utils.csv_utils import create_checksum
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

SALT = os.getenv("CHECKSUM_SALT", "default_salt")
client = TestClient(app)

CSRF_HEADER_NAME = "X-CSRF-Token"


dummy_org_data = [
    {
        "acronym": "ORG001",
        "domain_permutations": [
            {
                "blocklist_attack_count": 0,
                "blocklist_report_count": 0,
                "data_source": "00000000-0000-0000-0000-000000000001",
                "date_active": "2025-05-05",
                "date_observed": "2025-05-05",
                "domain_permutation": "extranet.fake-domain1.example",
                "dshield_attack_count": 0,
                "dshield_record_count": 0,
                "fuzzer": "subdomain",
                "ipv4": "0.0.0.1",
                "ipv6": "",
                "mail_server": "",
                "malicious": False,
                "name_server": "ns.fakeparking.com",
                "organization": "00000000-0000-0000-0000-000000000100",
                "ssdeep_score": "",
                "sub_domain": None,
                "suspected_domain_uid": "00000000-0000-0000-0000-000000000101",
            },
            {
                "blocklist_attack_count": 0,
                "blocklist_report_count": 0,
                "data_source": "00000000-0000-0000-0000-000000000001",
                "date_active": "2025-05-05",
                "date_observed": "2025-05-05",
                "domain_permutation": "extranet.fake-domain2.example",
                "dshield_attack_count": 0,
                "dshield_record_count": 0,
                "fuzzer": "subdomain",
                "ipv4": "0.0.0.2",
                "ipv6": "",
                "mail_server": "",
                "malicious": False,
                "name_server": "",
                "organization": "00000000-0000-0000-0000-000000000100",
                "ssdeep_score": "",
                "sub_domain": None,
                "suspected_domain_uid": "00000000-0000-0000-0000-000000000102",
            },
            {
                "blocklist_attack_count": 0,
                "blocklist_report_count": 0,
                "data_source": "00000000-0000-0000-0000-000000000001",
                "date_active": "2025-05-05",
                "date_observed": "2025-05-05",
                "domain_permutation": "extranet.fake-domain3.example",
                "dshield_attack_count": 0,
                "dshield_record_count": 0,
                "fuzzer": "tld-swap",
                "ipv4": "0.0.0.3",
                "ipv6": "",
                "mail_server": "",
                "malicious": False,
                "name_server": "ns.fakeaftermarket.com",
                "organization": "00000000-0000-0000-0000-000000000100",
                "ssdeep_score": "",
                "sub_domain": None,
                "suspected_domain_uid": "00000000-0000-0000-0000-000000000103",
            },
            {
                "blocklist_attack_count": 0,
                "blocklist_report_count": 0,
                "data_source": "00000000-0000-0000-0000-000000000001",
                "date_active": "2025-05-05",
                "date_observed": "2025-05-05",
                "domain_permutation": "extranet.fake-domain4.example",
                "dshield_attack_count": 0,
                "dshield_record_count": 0,
                "fuzzer": "tld-swap",
                "ipv4": "0.0.0.4",
                "ipv6": "",
                "mail_server": "",
                "malicious": False,
                "name_server": "",
                "organization": "00000000-0000-0000-0000-000000000100",
                "ssdeep_score": "",
                "sub_domain": None,
                "suspected_domain_uid": "00000000-0000-0000-0000-000000000104",
            },
            {
                "blocklist_attack_count": 0,
                "blocklist_report_count": 0,
                "data_source": "00000000-0000-0000-0000-000000000001",
                "date_active": "2025-05-05",
                "date_observed": "2025-05-05",
                "domain_permutation": "extranet.fake-domain5.example",
                "dshield_attack_count": 0,
                "dshield_record_count": 0,
                "fuzzer": "tld-swap",
                "ipv4": "0.0.0.5",
                "ipv6": "",
                "mail_server": "",
                "malicious": False,
                "name_server": "",
                "organization": "00000000-0000-0000-0000-000000000100",
                "ssdeep_score": "",
                "sub_domain": None,
                "suspected_domain_uid": "00000000-0000-0000-0000-000000000105",
            },
        ],
        "id": "00000000-0000-0000-0000-000000000100",
        "name": "Fake Organization",
    }
]


# =============================================================================
# Cookie auth + CSRF helpers
# =============================================================================
def _apply_set_cookie_headers_to_client(resp: StarletteResponse) -> None:
    """Copy Set-Cookie headers from a Starlette response into the TestClient cookie jar."""
    set_cookie_headers = resp.headers.getlist("set-cookie")
    if not set_cookie_headers:
        raise AssertionError(
            "No Set-Cookie headers were set by set_auth_and_csrf_cookies()"
        )

    for set_cookie in set_cookie_headers:
        c: SimpleCookie = SimpleCookie()
        c.load(set_cookie)
        for name, morsel in c.items():
            client.cookies.set(name, morsel.value)


def _prime_client_auth_and_csrf(user: User) -> None:
    """Prime TestClient with auth + csrf cookies using production helper."""
    token = create_jwt_token(user)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"host", b"testserver"),
            (b"x-forwarded-proto", b"http"),
        ],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
    }
    req = StarletteRequest(scope)
    resp = StarletteResponse()

    set_auth_and_csrf_cookies(resp, token, req)
    _apply_set_cookie_headers_to_client(resp)


def _csrf_headers() -> dict:
    """Find the CSRF cookie and echo it back in the CSRF header."""
    csrf_cookie_name = None
    for k in client.cookies.keys():
        lk = k.lower()
        if "csrf" in lk or "xsrf" in lk:
            csrf_cookie_name = k
            break

    if not csrf_cookie_name:
        raise AssertionError(
            f"No CSRF cookie found. Cookies present: {list(client.cookies.keys())}"
        )

    csrf_val = client.cookies.get(csrf_cookie_name)
    if not csrf_val:
        raise AssertionError(f"CSRF cookie '{csrf_cookie_name}' had no value")

    return {CSRF_HEADER_NAME: csrf_val}


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_dns_twist_sync_invalid_checksum_should_return_500():
    """Post valid data with invalid checksum should return 500."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    client.cookies.clear()
    _prime_client_auth_and_csrf(user)

    invalid_checksum = create_checksum(dummy_org_data) + "invstr"

    response = client.post(
        "/dns_twist_sync",
        json={"data": dummy_org_data},
        headers={
            **_csrf_headers(),
            "x-checksum": invalid_checksum,
        },
    )

    assert response.status_code == 500


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_dns_twist_sync_missing_checksum_should_return_500():
    """Post valid data with missing checksum should return 500."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    client.cookies.clear()
    _prime_client_auth_and_csrf(user)

    response = client.post(
        "/dns_twist_sync",
        json={"data": dummy_org_data},
        headers=_csrf_headers(),  # CSRF satisfied, but checksum missing -> expect 500 like before
    )
    assert response.status_code == 500


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_dns_twist_sync_missing_data_should_return_422():
    """Post missing body data should return 422 (validation error)."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    client.cookies.clear()
    _prime_client_auth_and_csrf(user)

    serialized = json.dumps(dummy_org_data, default=str, sort_keys=True)
    salted_checksum = hashlib.sha256((SALT + serialized).encode()).hexdigest()

    response = client.post(
        "/dns_twist_sync",
        headers={
            **_csrf_headers(),
            "x-salted-checksum": salted_checksum,
        },
        # no json/body -> should be 422 just like your original intent
    )
    assert response.status_code == 422
