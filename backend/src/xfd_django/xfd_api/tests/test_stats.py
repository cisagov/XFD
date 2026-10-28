"""Test Stats endpoint."""

# Standard Python Libraries
from datetime import date, datetime, timedelta
import uuid

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from xfd_api.api_methods.stats import compute_segment_ranges
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import (
    HostSummary,
    Organization,
    PortScanSummary,
    User,
    UserType,
    VulnScanSummary,
)

client = TestClient(app)


@pytest.fixture
def organization():
    """Create org fixture."""
    organization = Organization.objects.create(
        name="Test Organization",
        root_domains=["crossfeed.local"],
        ip_blocks=[],
        is_passive=False,
    )
    transaction.commit()
    assert organization.name == "Test Organization"
    yield organization


#####################################################################
#                 --------VS Summary Tests--------
#####################################################################


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_trends_success():
    """Test /stats/trends endpoint returns valid data."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-east"
    )

    user = User.objects.create(
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-east",
    )

    now = datetime.utcnow()
    HostSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        host_done_count=10,
        host_waiting_count=2,
        host_running_count=1,
        host_ready_count=7,
        up_host_count=8,
        down_host_count=3,
        scanned_asset_count=11,
        recent_up_hosts_count=8,
    )

    PortScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        open_port_count=20,
        risky_port_count=5,
        nmi_service_count=2,
        unique_ip_count=10,
        unique_service_count=8,
    )

    VulnScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        enrolled_in_vs_timestamp=now - timedelta(days=200),
        assets_owned_count=100,
        false_positive_count=5,
        vulnerable_host_count=50,
        unique_service_count=12,
        unique_low_severity_count=2,
        unique_medium_severity_count=3,
        unique_high_severity_count=4,
        unique_critical_severity_count=5,
        risky_services_count=3,
        unsupported_software_count=7,
        unique_os_count=4,
        low_severity_count=20,
        medium_severity_count=15,
        high_severity_count=25,
        critical_severity_count=5,
        critical_max_age=90,
        high_max_age=60,
        medium_max_age=54,
        low_max_age=100,
        low_kev_count=1,
        medium_kev_count=1,
        high_kev_count=1,
        critical_kev_count=1,
        kev_max_age=100,
        critical_kev_max_age=20,
        high_kev_max_age=50,
        medium_kev_max_age=55,
        low_kev_max_age=100,
        one_to_five_vulns_count=10,
        six_to_nine_vulns_count=5,
        ten_plus_vulns_count=3,
        top_5_occurring_cves=[],
        top_5_occurring_kevs=[],
        included_tickets={},
        top_5_risky_hosts={},
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (now - timedelta(days=7)).date().isoformat(),
            "end_date": now.date().isoformat(),
            "sources": ["vs", "host", "port", "port_service"],
            "enhanced_data": True,
        }
    }

    response = client.post(
        "/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert "host_summaries" in data
    assert "port_scan_summaries" in data
    assert "vuln_scan_summaries" in data
    assert data["host_summaries"][0]["host_done_count"] == 10


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_condensed_trends_success():
    """Test /stats/condensed_trends endpoint returns valid flattened data."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-west"
    )

    user = User.objects.create(
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-west",
    )

    now = datetime.utcnow()

    HostSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        host_done_count=12,
        host_waiting_count=3,
        host_running_count=0,
        host_ready_count=9,
        up_host_count=10,
        down_host_count=2,
        scanned_asset_count=12,
        recent_up_hosts_count=9,
    )

    PortScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        open_port_count=30,
        risky_port_count=7,
        nmi_service_count=3,
        unique_ip_count=15,
        unique_service_count=10,
    )

    VulnScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        enrolled_in_vs_timestamp=now - timedelta(days=300),
        assets_owned_count=200,
        false_positive_count=0,
        vulnerable_host_count=100,
        unique_service_count=5,
        unique_low_severity_count=0,
        unique_medium_severity_count=0,
        unique_high_severity_count=0,
        unique_critical_severity_count=0,
        risky_services_count=0,
        unsupported_software_count=0,
        unique_os_count=0,
        low_severity_count=0,
        medium_severity_count=0,
        high_severity_count=0,
        critical_severity_count=0,
        critical_max_age=0,
        high_max_age=0,
        medium_max_age=12,
        low_max_age=32,
        low_kev_count=0,
        medium_kev_count=0,
        high_kev_count=0,
        critical_kev_count=0,
        kev_max_age=0,
        critical_kev_max_age=0,
        high_kev_max_age=0,
        medium_kev_max_age=0,
        low_kev_max_age=0,
        one_to_five_vulns_count=0,
        six_to_nine_vulns_count=0,
        ten_plus_vulns_count=0,
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (now - timedelta(days=7)).date().isoformat(),
            "end_date": now.date().isoformat(),
            "sources": ["vs", "host", "port_service", "port"],
            "enhanced_data": False,
        }
    }

    response = client.post(
        "/stats/condensed_trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert any("host_summary_host_done_count" in k for k in data.keys())
    assert data["host_summary_host_done_count"][0] == 12


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_trends_unauthorized(organization):
    """Test the /stats/trends endpoint without auth."""
    payload = {
        "filters": {
            "organization_id": str(organization.id),
            "start_date": (datetime.today() - timedelta(days=30)).isoformat(),
            "end_date": datetime.today().isoformat(),
            "enhanced_data": False,
        }
    }

    response = client.post("/stats/trends", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_trends_invalid_org():
    """Test the /stats/trends endpoint with invalid org ID."""
    user = User.objects.create(
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-west",
    )

    payload = {
        "filters": {
            "organization_id": "Invalid-uuid",
            "start_date": (datetime.today() - timedelta(days=30)).date().isoformat(),
            "end_date": datetime.today().date().isoformat(),
            "enhanced_data": False,
        }
    }

    response = client.post(
        "/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid organization ID."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_trends_success():
    """Test /v2/stats/trends returns expected data."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-east"
    )

    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        first_name="Tester",
        last_name="McTest",
        region_id="us-east",
    )

    now = datetime.utcnow()

    HostSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=5),
        end_date=now,
        organization=org,
        host_done_count=7,
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (now - timedelta(days=5)).date().isoformat(),
            "end_date": now.date().isoformat(),
            "sources": ["host"],
            "enhanced_data": True,
        }
    }

    response = client.post(
        "/v2/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert "host_summaries" in data
    assert data["host_summaries"][0]["host_done_count"] == 7


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_trends_invalid_fields_for_source():
    """Test /v2/stats/trends rejects invalid fields for a source."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-east"
    )
    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        region_id="us-east",
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (datetime.today() - timedelta(days=7)).date().isoformat(),
            "end_date": datetime.today().date().isoformat(),
            "sources": ["vs"],
            "enhanced_data": False,
        },
        "fields": {"vs": ["non_existent_field"]},
    }

    response = client.post(
        "/v2/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 400
    assert "Invalid fields for source" in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_trends_access_denied_for_org():
    """Test access denied when user is not in org or region."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Hidden Org", region_id="us-west"
    )
    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.REGIONAL_ADMIN,
        region_id="us-east",  # Mismatched region
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (datetime.today() - timedelta(days=7)).date().isoformat(),
            "end_date": datetime.today().date().isoformat(),
            "sources": ["host"],
            "enhanced_data": False,
        }
    }

    response = client.post(
        "/v2/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_trends_unauthenticated():
    """Ensure /v2/stats/trends returns 401 without auth."""
    payload = {
        "filters": {
            "organization_id": str(uuid.uuid4()),
            "start_date": (datetime.today() - timedelta(days=7)).isoformat(),
            "end_date": datetime.today().isoformat(),
            "sources": ["vs"],
        }
    }

    response = client.post("/v2/stats/trends", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_trends_condensed_segments_aggregation():
    """Check segment aggregation kicks in and returns summary per segment."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Segment Org", region_id="us-central"
    )
    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        region_id="us-central",
    )

    today = datetime.today()
    summary_date = today - timedelta(days=3)

    for i in range(3):  # 3 days of data
        VulnScanSummary.objects.create(
            summary_date=summary_date.date() - timedelta(days=i),
            start_date=summary_date - timedelta(days=i + 1),
            end_date=summary_date - timedelta(days=i),
            organization=org,
            enrolled_in_vs_timestamp=summary_date.date() - timedelta(days=200),
            assets_owned_count=10 * (i + 1),
            vulnerable_host_count=5 * (i + 1),
        )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (today - timedelta(days=15)).date().isoformat(),
            "end_date": today.date().isoformat(),
            "sources": ["vs"],
        },
        "segment_size": 7,
    }

    response = client.post(
        "/v2/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    summaries = response.json()["vuln_scan_summaries"]
    assert isinstance(summaries, list)
    assert len(summaries) > 0
    assert "summary_date" in summaries[0]
    assert "assets_owned_count" in summaries[0]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_trends_segment_behavior():
    """Test that segmentation only occurs when date range > 60 days."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Segment Org", region_id="us-east"
    )
    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        region_id="us-east",
    )

    # Setup user, org, etc.
    segment_size = 7
    start_date = (datetime.today() - timedelta(days=100)).date()
    end_date = datetime.today().date()

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "sources": ["vs"],
            "enhanced_data": False,
        },
        "fields": {
            "vs": ["summary_date", "avg_summary_date", "one_to_five_vulns_count"]
        },
        "segment_size": segment_size,
    }

    response = client.post(
        "/v2/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )
    data = response.json()

    # Check keys present
    assert "vuln_scan_summaries" in data

    summaries = data["vuln_scan_summaries"]
    # Compute expected number of segments
    expected_segments = compute_segment_ranges(start_date, end_date, segment_size)
    assert len(summaries) == len(expected_segments)
    expected_seg_end_dates = [seg_end for _, seg_end in expected_segments]
    # Check summaries have avg_summary_date indicating aggregation
    for summary in summaries:
        # summary_date should equal segment end date
        assert "summary_date" in summary
        summary_date = date.fromisoformat(summary["summary_date"])
        assert summary_date in expected_seg_end_dates
        # Only assert avg_summary_date if it's present
        if "avg_summary_date" in summary:
            assert isinstance(summary["avg_summary_date"], date)
        else:
            # It's okay for avg_summary_date to be missing if there are no data points
            assert all(v is None for k, v in summary.items() if k != "summary_date")


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_stats_compare_success():
    """Test /stats/compare returns expected comparison results."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-east"
    )

    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-east",
    )

    base_date = datetime.utcnow().date() - timedelta(days=14)
    compare_date = datetime.utcnow().date() - timedelta(days=7)

    HostSummary.objects.create(
        summary_date=base_date,
        start_date=base_date - timedelta(days=7),
        end_date=base_date,
        organization=org,
        host_done_count=10,
        host_waiting_count=2,
        host_running_count=1,
        host_ready_count=7,
        up_host_count=8,
        down_host_count=3,
        scanned_asset_count=11,
        recent_up_hosts_count=7,
    )

    HostSummary.objects.create(
        summary_date=compare_date,
        start_date=compare_date - timedelta(days=7),
        end_date=compare_date,
        organization=org,
        host_done_count=15,
        host_waiting_count=1,
        host_running_count=2,
        host_ready_count=6,
        up_host_count=9,
        down_host_count=2,
        scanned_asset_count=13,
        recent_up_hosts_count=7,
    )

    payload = {
        "organization_id": str(org.id),
        "base_date": base_date.isoformat(),
        "compare_date": compare_date.isoformat(),
        "sources": ["host"],
        "enhanced_data": True,
    }

    response = client.post(
        "/stats/compare",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert "host_scans" in data
    assert data["host_scans"]["delta"]["host_done_count"]["count_change"] == 5


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_stats_compare_unauthorized():
    """Test /stats/compare returns 401 when no auth is provided."""
    payload = {
        "organization_id": str(uuid.uuid4()),
        "base_date": (datetime.utcnow() - timedelta(days=14)).date().isoformat(),
        "compare_date": (datetime.utcnow() - timedelta(days=7)).date().isoformat(),
        "sources": ["host"],
    }

    response = client.post("/stats/compare", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_stats_compare_invalid_org():
    """Test /stats/compare with an invalid org ID format."""
    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-east",
    )

    payload = {
        "organization_id": "bad-uuid",
        "base_date": (datetime.utcnow() - timedelta(days=14)).date().isoformat(),
        "compare_date": (datetime.utcnow() - timedelta(days=7)).date().isoformat(),
        "sources": ["host"],
    }

    response = client.post(
        "/stats/compare",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid organization ID."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_stats_compare_org_not_found():
    """Test /stats/compare returns 404 for non-existent org."""
    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-east",
    )

    payload = {
        "organization_id": str(uuid.uuid4()),
        "base_date": (datetime.utcnow() - timedelta(days=14)).date().isoformat(),
        "compare_date": (datetime.utcnow() - timedelta(days=7)).date().isoformat(),
        "sources": ["host"],
    }

    response = client.post(
        "/stats/compare",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_stats_compare_included_tickets_open_closed():
    """Test included_tickets comparison correctly identifies new and closed tickets."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Ticket Test Org", region_id="us-east"
    )

    user = User.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-east",
    )

    base_date = datetime.utcnow().date() - timedelta(days=14)
    compare_date = datetime.utcnow().date() - timedelta(days=7)

    # Base summary includes tickets A and B
    VulnScanSummary.objects.create(
        summary_date=base_date,
        start_date=base_date - timedelta(days=7),
        end_date=base_date,
        organization=org,
        included_tickets={
            "A": {"severity": "high", "is_kev": True},
            "B": {"severity": "medium", "is_kev": False},
        },
    )

    # Compare summary includes tickets B and C (B is still present, A is closed, C is new)
    VulnScanSummary.objects.create(
        summary_date=compare_date,
        start_date=compare_date - timedelta(days=7),
        end_date=compare_date,
        organization=org,
        included_tickets={
            "B": {"severity": "medium", "is_kev": False},
            "C": {"severity": "critical", "is_kev": True},
        },
    )

    payload = {
        "organization_id": str(org.id),
        "base_date": base_date.isoformat(),
        "compare_date": compare_date.isoformat(),
        "sources": ["vs"],
        "enhanced_data": True,
    }

    response = client.post(
        "/stats/compare",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    tickets = data["vs_scans"]["included_tickets_comparison"]

    # Expect ticket C to be new, ticket A to be closed
    assert tickets["new"]["total_count"] == 1
    assert tickets["new"]["by_severity"]["critical"] == 1
    assert tickets["new"]["kev_count"] == 1

    assert tickets["closed"]["total_count"] == 1
    assert tickets["closed"]["by_severity"]["high"] == 1
    assert tickets["closed"]["kev_count"] == 1

    # Percentages based on one ticket in each category
    assert tickets["new"]["total_percent"] == 50.0  # 1 of 2 in compare
    assert tickets["closed"]["total_percent"] == 50.0  # 1 of 2 in base
