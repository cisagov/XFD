"""Test Pshtt Sync Endpoint."""
# Standard Python Libraries
from datetime import datetime
import hashlib
import json
import os
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

SALT = os.getenv("CHECKSUM_SALT", "default_salt")

dummy_pshtt_data = [
    {
        "pshtt_results_uid": "b2f1b487-c04c-44b9-9d3a-2b1d4e45f6d2",
        "organization_uid": "12c4afd8-3cb3-4a32-9cba-66cbd884f703",
        "sub_domain_uid": "6e3acd85-0f64-45a6-8f5a-0a7f8539d6c9",
        "data_source_uid": "5ecfd264-6b9b-43fb-b711-0ee2b37e9241",
        "date_scanned": "2025-06-15",
        "base_domain": "example.com",
        "base_domain_hsts_preloaded": True,
        "canonical_url": "https://example.com",
        "defaults_to_https": True,
        "domain": "example.com",
        "domain_enforces_https": True,
        "domain_supports_https": True,
        "domain_uses_strong_hsts": True,
        "downgrades_https": False,
        "hsts": True,
        "hsts_entire_domain": True,
        "hsts_header": "max-age=31536000; includeSubDomains; preload",
        "hsts_max_age": 31536000,
        "hsts_preload_pending": False,
        "hsts_preload_ready": True,
        "hsts_preloaded": True,
        "https_bad_chain": False,
        "https_bad_hostname": False,
        "https_cert_chain_length": 2,
        "https_client_auth_required": False,
        "https_custom_truststore_trusted": None,
        "https_expired_cert": False,
        "https_full_connection": True,
        "https_live": True,
        "https_probably_missing_intermediate_cert": False,
        "https_publicly_trusted": True,
        "https_self_signed_cert": False,
        "https_leaf_cert_expiration_date": "2026-07-01",
        "https_leaf_cert_issuer": "Let's Encrypt",
        "https_leaf_cert_subject": "CN=example.com",
        "https_root_cert_issuer": "ISRG Root X1",
        "ip": "93.184.216.34",
        "live": True,
        "notes": "",
        "redirect": True,
        "redirect_to": "https://www.example.com",
        "server_header": "Apache",
        "server_version": "2.4.57",
        "strictly_forces_https": True,
        "unknown_error": False,
        "valid_https": True,
        "ep_http_headers": {"status": "301 Moved Permanently"},
        "ep_http_server_header": "Apache",
        "ep_http_server_version": "2.4",
        "ep_https_headers": {"strict-transport-security": "max-age=31536000"},
        "ep_https_hsts_header": "max-age=31536000; includeSubDomains; preload",
        "ep_https_server_header": "Apache",
        "ep_https_server_version": "2.4",
        "ep_httpswww_headers": {"cache-control": "no-cache"},
        "ep_httpswww_hsts_header": "max-age=31536000",
        "ep_httpswww_server_header": "Apache",
        "ep_httpswww_server_version": "2.4",
        "ep_httpwww_headers": {"status": "200 OK"},
        "ep_httpwww_server_header": "Apache",
        "ep_httpwww_server_version": "2.4",
    },
    {
        "pshtt_results_uid": "8d819797-5e45-428b-a3e2-6acd65f96489",
        "organization_uid": "c90fdd17-8eaa-4fbd-b0e0-e80e9e26ef12",
        "sub_domain_uid": "f5a41466-cd5f-4d6c-83da-ba1f3e8e5f8d",
        "data_source_uid": "7d2a2fa5-b1e0-4c2e-aaf1-2f6fd75d9f45",
        "date_scanned": "2025-06-13",
        "base_domain": "mycooldomain.net",
        "base_domain_hsts_preloaded": False,
        "canonical_url": "http://mycooldomain.net",
        "defaults_to_https": False,
        "domain": "mycooldomain.net",
        "domain_enforces_https": False,
        "domain_supports_https": False,
        "domain_uses_strong_hsts": None,
        "downgrades_https": None,
        "hsts": None,
        "hsts_entire_domain": None,
        "hsts_header": None,
        "hsts_max_age": None,
        "hsts_preload_pending": None,
        "hsts_preload_ready": None,
        "hsts_preloaded": None,
        "https_bad_chain": None,
        "https_bad_hostname": None,
        "https_cert_chain_length": None,
        "https_client_auth_required": None,
        "https_custom_truststore_trusted": None,
        "https_expired_cert": None,
        "https_full_connection": None,
        "https_live": None,
        "https_probably_missing_intermediate_cert": None,
        "https_publicly_trusted": None,
        "https_self_signed_cert": None,
        "https_leaf_cert_expiration_date": None,
        "https_leaf_cert_issuer": None,
        "https_leaf_cert_subject": None,
        "https_root_cert_issuer": None,
        "ip": "198.51.100.17",
        "live": False,
        "notes": "Initial crawl; HTTPS not yet configured.",
        "redirect": False,
        "redirect_to": None,
        "server_header": "nginx",
        "server_version": "1.25.4",
        "strictly_forces_https": None,
        "unknown_error": None,
        "valid_https": None,
        "ep_http_headers": {"status": "200 OK"},
        "ep_http_server_header": "nginx",
        "ep_http_server_version": "1.25",
        "ep_https_headers": None,
        "ep_https_hsts_header": None,
        "ep_https_server_header": None,
        "ep_https_server_version": None,
        "ep_httpswww_headers": None,
        "ep_httpswww_hsts_header": None,
        "ep_httpswww_server_header": None,
        "ep_httpswww_server_version": None,
        "ep_httpwww_headers": {"status": "404 Not Found"},
        "ep_httpwww_server_header": "nginx",
        "ep_httpwww_server_version": "1.25",
    },
]


def create_checksum(data):
    """Create a SHA-256 checksum for the given data."""
    return hashlib.sha256((SALT + data).encode()).hexdigest()


client = TestClient(app)


# Test: post valid data with invalid checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_sync_invalid_checksum_should_return_500():
    """Test sync with invalid checksum."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    invalid_checksum = create_checksum(json.dumps(dummy_pshtt_data)) + "invstr"
    response = client.post(
        "/pshtt_sync",
        json={"data": dummy_pshtt_data},
        headers={
            "x-checksum": invalid_checksum,
            "Authorization": "Bearer {}".format(create_jwt_token(user)),
        },
    )
    assert response.status_code == 500


# Test: post valid data with missing checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_sync_missing_checksum_should_return_500():
    """Test sync with missing checksum."""
    user = user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    headers = {"Authorization": "Bearer {}".format(create_jwt_token(user))}
    response = client.post(
        "/pshtt_sync", data=json.dumps({"data": dummy_pshtt_data}), headers=headers
    )

    assert response.status_code == 500


# Test: post empty data should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_sync_missing_data_should_return_422():
    """Test sync with missing data."""
    user = user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    headers = {
        "Authorization": "Bearer {}".format(create_jwt_token(user)),
        "x-checksum": create_checksum(json.dumps(dummy_pshtt_data)),
    }
    response = client.post("/pshtt_sync", headers=headers)
    assert response.status_code == 422
