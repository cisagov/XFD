"""Test sync."""

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
from xfd_api.utils.csv_utils import create_checksum
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

SALT = os.getenv("CHECKSUM_SALT", "default_salt")
client = TestClient(app)


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


# Test: post valid data with invalid checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_dns_twist_sync_invalid_checksum_should_return_500():
    """Test sync with invalid checksum."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    invalid_checksum = create_checksum(dummy_org_data) + "invstr"
    response = client.post(
        "/dns_twist_sync",
        json={"data": dummy_org_data},
        headers={
            "x-checksum": invalid_checksum,
            "Authorization": "Bearer {}".format(create_jwt_token(user)),
        },
    )
    assert response.status_code == 500


# Test: post valid data with missing checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_dns_twist_sync_missing_checksum_should_return_500():
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
        "/dns_twist_sync", json={"data": dummy_org_data}, headers=headers
    )
    assert response.status_code == 500


# Test: post empty data should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_dns_twist_sync_missing_data_should_return_422():
    """Test sync with missing data."""
    user = user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    serialized = json.dumps(dummy_org_data, default=str, sort_keys=True)
    salted_checksum = hashlib.sha256((SALT + serialized).encode()).hexdigest()
    headers = {
        "Authorization": "Bearer {}".format(create_jwt_token(user)),
        "x-salted-checksum": salted_checksum,
    }
    response = client.post("/dns_twist_sync", headers=headers)
    assert response.status_code == 422
