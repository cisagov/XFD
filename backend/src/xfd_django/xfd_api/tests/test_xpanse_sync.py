"""Test sync."""

# Standard Python Libraries
from datetime import datetime
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.utils.csv_utils import create_checksum
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)


dummy_org_data = {
    "data": [
        {
            "xpanse_business_unit_uid": "4d2d84ab-f06b-411f-9f58-a3fd59a389cb",
            "entity_name": "Springfield Unified School District [SUSDCA]",
            "cyhy_db_name": "SUSDCA",
            "state": "CA",
            "county": "Spring County",
            "city": "Springfield",
            "sector": "Government Facilities",
            "entity_type": "Local Education Agency",
            "region": "Region 9",
            "rating": 75,
            "alerts": [
                {
                    "xpanse_alert_uid": "123abcde-456f-7890-9abc-def123456789",
                    "time_pulled_from_xpanse": "2025-04-24T07:20:13.100000+00:00",
                    "alert_id": "3001234",
                    "detection_timestamp": "2025-01-10T05:45:00.000000+00:00",
                    "alert_name": "Insecure Web Application at 192.0.2.10:8080",
                    "description": "Detected insecure HTTP configuration on an exposed web application. Recommend transitioning to HTTPS.",
                    "host_name": "192.0.2.10",
                    "alert_action": "NOT_AVAILABLE",
                    "action_pretty": "N/A",
                    "action_country": ["US"],
                    "action_remote_port": [8080],
                    "starred": False,
                    "external_id": "abc123-def456",
                    "related_external_id": "abc123",
                    "alert_occurrence": 0,
                    "severity": "high",
                    "matching_status": "MATCHED",
                    "local_insert_ts": "2025-01-10T05:45:00.000000+00:00",
                    "last_modified_ts": "2025-01-10T05:45:01.000000+00:00",
                    "case_id": 900123,
                    "event_timestamp": ["2025-01-10T05:44:00.000000+00:00"],
                    "alert_type": "Web Application",
                    "resolution_status": "STATUS_230_REOPENED",
                    "resolution_comment": None,
                    "tags": ["BU:Springfield Unified School District [SUSDCA]"],
                    "last_observed": "2025-04-22T12:00:00+00:00",
                    "country_codes": ["US"],
                    "cloud_providers": ["AWS"],
                    "ipv4_addresses": ["192.0.2.10"],
                    "domain_names": ["school.springfield.edu"],
                    "service_ids": ["srv-001"],
                    "website_ids": None,
                    "asset_ids": ["asset-001"],
                    "certificate": {
                        "issuerName": "Let's Encrypt",
                        "subjectOrg": "Springfield Schools",
                        "subjectName": "school.springfield.edu",
                        "serialNumber": "1234567890",
                        "validNotAfter": 2300000000000,
                        "validNotBefore": 1680000000000,
                    },
                    "port_protocol": "TCP",
                    "attack_surface_rule_name": "Insecure HTTP Exposure",
                    "remediation_guidance": "Move the web application to HTTPS to avoid exposure of credentials.",
                    "asset_identifiers": [
                        {
                            "domain": "school.springfield.edu",
                            "httpPath": "/admin",
                            "portNumber": 8080,
                            "certificate": {
                                "issuerName": "Let's Encrypt",
                                "subjectName": "school.springfield.edu",
                                "serialNumber": "1234567890",
                                "validNotAfter": 2300000000000,
                                "validNotBefore": 1680000000000,
                            },
                            "ipv4Address": "192.0.2.10",
                            "ipv6Address": None,
                            "lastObserved": 1745390000000,
                            "portProtocol": "TCP",
                            "firstObserved": 1686300000000,
                        }
                    ],
                    "assets": [],
                    "services": [
                        {
                            "xpanse_service_uid": "srvuid-001",
                            "service_id": "srv-001",
                            "service_name": "WebUI at 192.0.2.10:8080",
                            "service_type": "HttpService",
                            "ip_address": ["192.0.2.10"],
                            "domain": ["school.springfield.edu"],
                            "externally_detected_providers": ["AWS"],
                            "is_active": "Active",
                            "first_observed": "2023-06-01T09:00:00+00:00",
                            "last_observed": "2025-04-22T12:00:00+00:00",
                            "port": 8080,
                            "protocol": "TCP",
                            "active_classifications": ["HttpExposed"],
                            "inactive_classifications": [],
                            "discovery_type": "DirectlyDiscovered",
                            "externally_inferred_vulnerability_score": 7.5,
                            "externally_inferred_cves": ["CVE-2023-12345"],
                            "service_key": "192.0.2.10:8080",
                            "service_key_type": "IP",
                            "sub_domains": [],
                            "cves": [],
                        }
                    ],
                }
            ],
        },
        {
            "xpanse_business_unit_uid": "7af3de90-ffa1-4b45-b3f3-d24fd22d97c1",
            "entity_name": "Bayview Township IT Services [BTITS]",
            "cyhy_db_name": "BTITS",
            "state": "FL",
            "county": "Bay County",
            "city": "Bayview",
            "sector": "Information Technology",
            "entity_type": "Town Government",
            "region": "Region 4",
            "rating": 88,
            "alerts": [],
        },
        {
            "xpanse_business_unit_uid": "2ec1f964-33c3-4b2f-9188-4c1f880bc8a7",
            "entity_name": "Evergreen Health Authority [EHAWA]",
            "cyhy_db_name": "EHAWA",
            "state": "WA",
            "county": "Evergreen County",
            "city": "Evergreen",
            "sector": "Health and Public Health",
            "entity_type": "Public Health Organization",
            "region": "Region 10",
            "rating": 91,
            "alerts": [
                {
                    "xpanse_alert_uid": "fedcba98-7654-3210-ffed-cba987654321",
                    "time_pulled_from_xpanse": "2025-04-24T08:00:00.000000+00:00",
                    "alert_id": "3012345",
                    "detection_timestamp": "2025-03-15T12:00:00.000000+00:00",
                    "alert_name": "Outdated SSH Server at 198.51.100.12:22",
                    "description": "An outdated version of OpenSSH was found exposed to the internet, which could be vulnerable.",
                    "host_name": "198.51.100.12",
                    "alert_action": "NOT_AVAILABLE",
                    "action_pretty": "N/A",
                    "action_country": ["US"],
                    "action_remote_port": [22],
                    "starred": False,
                    "external_id": "ssh-2025-01",
                    "related_external_id": "ssh-2025",
                    "alert_occurrence": 1,
                    "severity": "low",
                    "matching_status": "MATCHED",
                    "local_insert_ts": "2025-03-15T12:00:00.000000+00:00",
                    "last_modified_ts": "2025-03-15T12:01:00.000000+00:00",
                    "case_id": 903456,
                    "event_timestamp": ["2025-03-15T11:59:00.000000+00:00"],
                    "alert_type": "SSH Exposure",
                    "resolution_status": "STATUS_100_OPEN",
                    "resolution_comment": None,
                    "tags": ["BU:Evergreen Health Authority [EHAWA]"],
                    "last_observed": "2025-04-23T00:00:00+00:00",
                    "country_codes": ["US"],
                    "cloud_providers": ["Azure"],
                    "ipv4_addresses": ["198.51.100.12"],
                    "domain_names": [],
                    "service_ids": ["srv-ssh-001"],
                    "website_ids": None,
                    "asset_ids": ["asset-ssh-001"],
                    "certificate": None,
                    "port_protocol": "TCP",
                    "attack_surface_rule_name": "Outdated SSH",
                    "remediation_guidance": "Update OpenSSH to the latest secure version to avoid known exploits.",
                    "asset_identifiers": [],
                    "assets": [],
                    "services": [
                        {
                            "xpanse_service_uid": "srvuid-ssh-001",
                            "service_id": "srv-ssh-001",
                            "service_name": "OpenSSH at 198.51.100.12:22",
                            "service_type": "SshService",
                            "ip_address": ["198.51.100.12"],
                            "domain": [],
                            "externally_detected_providers": ["Azure"],
                            "is_active": "Active",
                            "first_observed": "2023-08-10T10:00:00+00:00",
                            "last_observed": "2025-04-23T00:00:00+00:00",
                            "port": 22,
                            "protocol": "TCP",
                            "active_classifications": ["OutdatedSoftware"],
                            "inactive_classifications": [],
                            "discovery_type": "DirectlyDiscovered",
                            "externally_inferred_vulnerability_score": 5.0,
                            "externally_inferred_cves": ["CVE-2022-1234"],
                            "service_key": "198.51.100.12:22",
                            "service_key_type": "IP",
                            "sub_domains": [],
                            "cves": [],
                        }
                    ],
                }
            ],
        },
    ]
}


# Test: post valid data with invalid checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_xpanse_sync_invalid_checksum_should_return_500():
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
        "/xpanse-sync",
        json=dummy_org_data,
        headers={
            "x-checksum": invalid_checksum,
            "Authorization": "Bearer {}".format(create_jwt_token(user)),
        },
    )
    assert response.status_code == 500


# Test: post valid data with missing checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_xpanse_sync_missing_checksum_should_return_500():
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
    response = client.post("/xpanse-sync", json=dummy_org_data, headers=headers)
    assert response.status_code == 500


# Test: post empty data should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_xpanse_sync_missing_data_should_return_422():
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
        "x-checksum": create_checksum(dummy_org_data),
    }
    response = client.post("/xpanse-sync", headers=headers)
    assert response.status_code == 422
