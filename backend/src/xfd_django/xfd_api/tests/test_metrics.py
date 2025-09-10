"""Tests for Metrics Dashboard endpoints."""

# Standard Python Libraries
from datetime import datetime, timedelta

# Third-Party Libraries
from django.db import transaction
from django.utils import timezone
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.schema_models.scan import SCAN_SCHEMA
from xfd_django.asgi import app
from xfd_mini_dl.models import Organization, Scan, ScanResult, User, UserType

client = TestClient(app)


# --------------------------
# Fixtures (scoped locally)
# --------------------------


@pytest.fixture
def user():
    """Create a user for auth header."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="test-user-{}@example.com".format(int(datetime.utcnow().timestamp())),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    yield user
    user.delete()


def _make_org(name):
    org = Organization.objects.create(
        name=name,
        root_domains=["example.com"],
        ip_blocks=[],
        is_passive=False,
    )
    transaction.commit()
    return org


def _pick_scan_names_from_schema():
    """Pick one non-global scan name (required) and one global scan (optional)."""
    non_global = None
    global_name = None
    for name, schema in SCAN_SCHEMA.items():
        if (
            hasattr(schema, "global_scan")
            and schema.global_scan is False
            and non_global is None
        ):
            non_global = name
        if (
            hasattr(schema, "global_scan")
            and schema.global_scan is True
            and global_name is None
        ):
            global_name = name
        if non_global is not None and global_name is not None:
            break
    return non_global, global_name


def _make_scan(name, total_orgs=0, freq=7):
    scan = Scan.objects.create(
        name=name,
        frequency=freq,
        last_run=timezone.now(),
        total_orgs=total_orgs,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    transaction.commit()
    return scan


def _make_result(scan, org, status, dt):
    # Use *_id to avoid needing full model instances if FK constraints are simple.
    ScanResult.objects.create(
        scan_id=scan.id,
        organization_id=org.id,
        http_status=status,
        scanned_at=dt,
    )


# ------------------------------------------------------
# /metrics/scans — list_scans_org_count_by_status
# ------------------------------------------------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_scans_org_count_by_status_counts_and_window_filter(user):
    """Counts distinct orgs per status for non-global scans and filters by window."""
    non_global_name, global_name = _pick_scan_names_from_schema()
    if non_global_name is None:
        pytest.skip("No non-global scan found in SCAN_SCHEMA; cannot test endpoint.")

    # Create orgs
    org_a = _make_org("Acme Corp")
    org_b = _make_org("Beta LLC")
    org_c = _make_org("Gamma Inc")

    # Create scans
    ng_scan = _make_scan(non_global_name, total_orgs=3, freq=1)

    # Optional global scan (to ensure it is excluded)
    g_scan = None
    if global_name is not None:
        g_scan = _make_scan(global_name, total_orgs=2, freq=1)

    now = timezone.now()
    today_mid = now.replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday_mid = (now - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    too_old = (now - timedelta(days=10)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    # In-window results for non-global scan:
    # - status 200 for two distinct orgs today
    # - status 404 for one org yesterday
    _make_result(ng_scan, org_a, 200, today_mid)
    _make_result(ng_scan, org_b, 200, today_mid)
    _make_result(ng_scan, org_c, 404, yesterday_mid)

    # Out-of-window result that should be excluded (older than 3-day window we will query)
    _make_result(ng_scan, org_a, 200, too_old)

    # Some results for global scan (should not appear at all)
    if g_scan is not None:
        _make_result(g_scan, org_a, 200, today_mid)
        _make_result(g_scan, org_b, 404, today_mid)

    transaction.commit()

    # Call endpoint with a small window that excludes the "too_old" record
    response = client.get(
        "/metrics/scans",
        params={"window_days": 3},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["metrics_window_days"] == 3

    # Find our non-global scan in the response
    scans = data["scans"]
    returned_ids = {s["id"] for s in scans}

    assert (
        str(ng_scan.id) in returned_ids
    ), "Non-global scan should be included in response."

    if g_scan is not None:
        assert (
            str(g_scan.id) not in returned_ids
        ), "Global scan should be excluded from response."

    # Validate org_counts_by_status for the non-global scan
    ng = [s for s in scans if s["id"] == str(ng_scan.id)][0]
    counts = {c["http_status"]: c["org_count"] for c in ng["org_counts_by_status"]}

    # Expect distinct org counts for each status (in-window only)
    assert counts.get(200) == 2, "HTTP 200 should have 2 distinct orgs."
    assert counts.get(404) == 1, "HTTP 404 should have 1 distinct org."
    # The old 200 record should not inflate counts because it is outside the window
    # (and also distinct org counting would not be affected unless it was a new org).


# -----------------------------------------------------------------
# /metrics/scans/{scan_id} — get_scan_daily_status_counts
# -----------------------------------------------------------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_scan_daily_status_counts_groups_by_date_and_status(user):
    """Aggregates by date per status for a scan and reports the correct window."""
    # Any scan will do (global or not) for this endpoint
    non_global_name, _ = _pick_scan_names_from_schema()
    if non_global_name is None:
        pytest.skip("No scan name available in SCAN_SCHEMA to create a Scan.")

    scan = _make_scan(non_global_name, total_orgs=3, freq=1)

    # Orgs are only needed because ScanResult references organization_id
    org_a = _make_org("Acme Corp")
    org_b = _make_org("Beta LLC")
    org_c = _make_org("Gamma Inc")

    now = timezone.now()
    today_mid = now.replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday_mid = (now - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    # Create daily rows (these are counted as raw rows, not distinct orgs)
    # Today: two 200s
    _make_result(scan, org_a, 200, today_mid)
    _make_result(scan, org_b, 200, today_mid)
    # Yesterday: one 200 and one 404
    _make_result(scan, org_b, 200, yesterday_mid)
    _make_result(scan, org_c, 404, yesterday_mid)

    transaction.commit()

    window_days = 3
    response = client.get(
        "/metrics/scans/{}".format(scan.id),
        params={"window_days": window_days},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["id"] == str(scan.id)
    assert payload["metrics_window_days"] == window_days

    # Build a map: status -> {date -> count}
    status_map = {}
    for entry in payload["daily_status_counts"]:
        status = entry["http_status"]
        status_map[status] = {dc["date"]: dc["count"] for dc in entry["daily_counts"]}

    today_str = today_mid.date().strftime("%Y-%m-%d")
    yday_str = yesterday_mid.date().strftime("%Y-%m-%d")

    # Validate counts:
    # 200 -> today:2, yesterday:1
    assert (
        status_map.get(200, {}).get(today_str) == 2
    ), "Expected 2 rows for HTTP 200 today."
    assert (
        status_map.get(200, {}).get(yday_str) == 1
    ), "Expected 1 row for HTTP 200 yesterday."
    # 404 -> yesterday:1
    assert (
        status_map.get(404, {}).get(yday_str) == 1
    ), "Expected 1 row for HTTP 404 yesterday."
