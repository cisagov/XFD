"""Tests for Metrics Dashboard endpoints."""
from __future__ import annotations

# Standard Python Libraries
from datetime import UTC, date, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

# Third-Party Libraries
from django.db import transaction
from django.utils import timezone as dj_timezone
from fastapi.testclient import TestClient
import pytest
from xfd_api.api_methods.export_customer_metrics import (
    _default_fieldnames,
    export_customer_metrics,
)
from xfd_api.auth import create_jwt_token
from xfd_api.schema_models.scan import SCAN_SCHEMA
from xfd_api.tasks import metrics as metrics_mod
from xfd_django.asgi import app
from xfd_mini_dl.models import (
    CustomerMetrics,
    Organization,
    Role,
    Scan,
    ScanResult,
    User,
    UserType,
)

# -------------------------------------------------------------------
# Global test config
# -------------------------------------------------------------------

client = TestClient(app)

pytestmark = pytest.mark.django_db(
    transaction=True, databases=["default", "mini_data_lake"]
)

FIXED_NOW = datetime(2025, 9, 4, 12, 0, 0, tzinfo=dt_timezone.utc)


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture(autouse=True)
def freeze_time(monkeypatch):
    """Freeze both Django and metrics' timezone to a fixed UTC instant."""
    monkeypatch.setattr(metrics_mod.dj_timezone, "now", lambda: FIXED_NOW)
    monkeypatch.setattr("django.utils.timezone.now", lambda: FIXED_NOW)


@pytest.fixture
def user() -> User:
    """Admin user for Authorization header."""
    u = User.objects.create(
        first_name="",
        last_name="",
        email="test-user-{}@example.com".format(int(datetime.now(UTC).timestamp())),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    yield u
    u.delete()


@pytest.fixture
def clock() -> tuple[datetime, datetime, date]:
    """Return (start_dt, end_dt, target_date) for 'yesterday' in UTC."""
    return metrics_mod._yesterday_utc()


@pytest.fixture
def python_avg_pending(monkeypatch):
    """Monkeypatch _collect_mean_wait_time_for_pending_users to return decimal days."""

    def _impl(end_dt_inner: datetime):
        end_date = end_dt_inner.date()
        region_expr = metrics_mod._region_int_from_char("region_id")
        rows = (
            User.objects.filter(invite_pending=True, created_at__lte=end_dt_inner)
            .annotate(region_num=region_expr)
            .values("region_num", "created_at")
        )
        buckets: dict[int | None, list[int]] = {}
        for r in rows:
            region = r["region_num"]
            days = (end_date - r["created_at"].date()).days
            buckets.setdefault(region, []).append(days)

        out: dict[int | None, dict[str, Decimal | int]] = {}
        for region, vals in buckets.items():
            if not vals:
                continue
            avg_days = Decimal(sum(vals)) / Decimal(len(vals))
            out[region] = {"pending_count": len(vals), "avg_wait": avg_days}
        return out

    monkeypatch.setattr(metrics_mod, "_collect_mean_wait_time_for_pending_users", _impl)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def run_task():
    """Invoke the daily metrics job with the usual (event, context) no-ops."""
    return metrics_mod.collect_and_upsert_customer_metrics({}, {})


def force_created_at(user: User, ts: datetime) -> User:
    """Set created_at precisely (bypasses auto_now_add)."""
    User.objects.filter(pk=user.pk).update(created_at=ts)
    user.refresh_from_db()
    return user


def value_in_days(value) -> float:
    """Normalize timedelta/Decimal/float/int to a float days value."""
    if hasattr(value, "total_seconds"):
        return value.total_seconds() / 86400.0
    return float(value)


def parse_csv(csv_bytes: bytes) -> tuple[list[str], list[list[str]]]:
    """Return (header, rows) from CSV bytes."""
    lines = [line for line in csv_bytes.decode("utf-8").splitlines() if line.strip()]
    header = lines[0].split(",") if lines else []
    rows = [ln.split(",") for ln in lines[1:]]
    return header, rows


def at_noon(dt: datetime) -> datetime:
    """Return a copy of dt at noon (12:00:00) the same day."""
    return dt.replace(hour=12, minute=0, second=0, microsecond=0)


def _make_org(name: str) -> Organization:
    """Create and return a simple Organization."""
    org = Organization.objects.create(
        name=name,
        root_domains=["example.com"],
        ip_blocks=[],
        is_passive=False,
    )
    transaction.commit()
    return org


def _pick_scan_names_from_schema() -> tuple[str | None, str | None]:
    """Pick one non-global scan (required) and one global scan (optional)."""
    non_global = None
    global_name = None
    for name, schema in SCAN_SCHEMA.items():
        if getattr(schema, "global_scan", None) is False and non_global is None:
            non_global = name
        if getattr(schema, "global_scan", None) is True and global_name is None:
            global_name = name
        if non_global and global_name:
            break
    return non_global, global_name


def _make_scan(name: str, total_orgs: int = 0, freq: int = 7) -> Scan:
    """Create and return a simple Scan."""
    scan = Scan.objects.create(
        name=name,
        frequency=freq,
        last_run=dj_timezone.now(),
        total_orgs=total_orgs,
        created_at=dj_timezone.now(),
        updated_at=dj_timezone.now(),
    )
    transaction.commit()
    return scan


def _make_result(scan: Scan, org: Organization, status: int, dt: datetime) -> None:
    """Create a ScanResult for the given scan, org, status, and scanned_at datetime."""
    ScanResult.objects.create(
        scan_id=scan.id,
        organization_id=org.id,
        http_status=status,
        scanned_at=dt,
    )


# -------------------------------------------------------------------
# Metrics endpoints
# -------------------------------------------------------------------
def test_metrics_customers_csv_endpoint(user: User):
    """Test /metrics/customers endpoint returns CSV with auth."""
    metrics_mod.collect_and_upsert_customer_metrics({}, {})

    resp = client.get(
        "/metrics/customers",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "Content-Disposition" in resp.headers


def test_list_scans_org_count_by_status_counts_and_window_filter(user: User):
    """Test /metrics/scans endpoint with org_count_by_status and window_days."""
    non_global_name, global_name = _pick_scan_names_from_schema()
    if non_global_name is None:
        pytest.skip("No non-global scan found in SCAN_SCHEMA; cannot test endpoint.")

    org_a, org_b, org_c = (
        _make_org("Acme Corp"),
        _make_org("Beta LLC"),
        _make_org("Gamma Inc"),
    )
    ng_scan = (
        _make_scan(non_global_name, total_orgs=3, freq=1) if non_global_name else None
    )
    g_scan = _make_scan(global_name, total_orgs=2, freq=1) if global_name else None

    now = dj_timezone.now()
    today_mid = at_noon(now)
    yesterday_mid = at_noon(now - timedelta(days=1))
    too_old = at_noon(now - timedelta(days=10))

    _make_result(ng_scan, org_a, 200, today_mid)
    _make_result(ng_scan, org_b, 200, today_mid)
    _make_result(ng_scan, org_c, 404, yesterday_mid)
    _make_result(ng_scan, org_a, 200, too_old)  # excluded by window

    if g_scan:
        _make_result(g_scan, org_a, 200, today_mid)
        _make_result(g_scan, org_b, 404, today_mid)

    transaction.commit()

    resp = client.get(
        "/metrics/scans",
        params={"window_days": 3},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["metrics_window_days"] == 3
    scans = data["scans"]
    ids = {s["id"] for s in scans}

    assert str(ng_scan.id) in ids
    if g_scan:
        assert str(g_scan.id) not in ids

    ng = next(s for s in scans if s["id"] == str(ng_scan.id))
    counts = {c["http_status"]: c["org_count"] for c in ng["org_counts_by_status"]}
    assert counts.get(200) == 2
    assert counts.get(404) == 1


def test_get_scan_daily_status_counts_groups_by_date_and_status(user: User):
    """Test /metrics/scans/{scan_id} endpoint with daily_status_counts."""
    non_global_name, _ = _pick_scan_names_from_schema()
    if non_global_name is None:
        pytest.skip("No scan name available in SCAN_SCHEMA to create a Scan.")

    scan = (
        _make_scan(non_global_name, total_orgs=3, freq=1) if non_global_name else None
    )
    org_a, org_b, org_c = _make_org("Acme"), _make_org("Beta"), _make_org("Gamma")

    now = dj_timezone.now()
    today_mid = at_noon(now)
    yday_mid = at_noon(now - timedelta(days=1))

    _make_result(scan, org_a, 200, today_mid)
    _make_result(scan, org_b, 200, today_mid)
    _make_result(scan, org_b, 200, yday_mid)
    _make_result(scan, org_c, 404, yday_mid)
    transaction.commit()

    window_days = 3
    resp = client.get(
        "/metrics/scans/{}".format(scan.id),
        params={"window_days": window_days},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == str(scan.id)
    assert payload["metrics_window_days"] == window_days

    status_map: dict[int, dict[str, int]] = {}
    for entry in payload["daily_status_counts"]:
        status_map[entry["http_status"]] = {
            dc["date"]: dc["count"] for dc in entry["daily_counts"]
        }

    today_str, yday_str = today_mid.date().isoformat(), yday_mid.date().isoformat()
    assert status_map.get(200, {}).get(today_str) == 2
    assert status_map.get(200, {}).get(yday_str) == 1
    assert status_map.get(404, {}).get(yday_str) == 1


# -------------------------------------------------------------------
# CustomerMetrics task
# -------------------------------------------------------------------


def test_creates_rows_for_all_regions_including_null(clock):
    """Test that all regions 1..10 and NULL are created with zero counts."""
    _start, _end, target_date = clock
    result = run_task()
    rows = CustomerMetrics.objects.filter(date=target_date).order_by("region")
    assert result["date"] == target_date
    assert rows.count() == len(metrics_mod.REGIONS)
    for region in (None, 1, 10):
        cm = rows.get(region=region)
        assert cm.active_orgs_without_users == 0
        assert cm.external_active_orgs == 0
        assert cm.external_retired_orgs == 0
        assert cm.external_users == 0
        assert cm.cisa_users == 0
        assert cm.users_without_org == 0
        assert cm.users_created == 0
        assert cm.users_approved == 0
        assert cm.users_invite_pending == 0
        assert cm.active_users == 0
        assert cm.mean_approval_time is None


def test_active_orgs_and_external_org_filters(clock):
    """Test active_orgs_without_users, external_active_orgs, external_retired_orgs counts."""
    Organization.objects.create(
        acronym="EXT1", retired=False, region_id="1", name="Ext Active"
    )
    Organization.objects.create(
        acronym="DHS_ABC", retired=False, region_id="1", name="DHS Active"
    )
    Organization.objects.create(
        acronym="EXT_RET", retired=True, region_id="1", name="Ext Retired"
    )
    u = User.objects.create(
        first_name="A",
        last_name="B",
        full_name="A B",
        email="a@example.org",
        user_type=UserType.STANDARD,
        region_id="1",
    )
    Role.objects.create(user=u, organization=Organization.objects.get(acronym="EXT1"))
    _s, _e, target_date = clock
    run_task()
    cm = CustomerMetrics.objects.get(date=target_date, region=1)
    assert cm.active_orgs_without_users == 1
    assert cm.external_active_orgs == 1
    assert cm.external_retired_orgs == 1


def test_external_and_cisa_users(clock):
    """Test external_users and cisa_users counts."""
    User.objects.create(
        first_name="Ext",
        last_name="U",
        full_name="Ext U",
        email="vendor@example.com",
        user_type=UserType.STANDARD,
        region_id="2",
    )
    User.objects.create(
        first_name="Dhs",
        last_name="U",
        full_name="Dhs U",
        email="someone@dhs.gov",
        user_type=UserType.STANDARD,
        region_id="2",
    )
    User.objects.create(
        first_name="Admin",
        last_name="U",
        full_name="Admin U",
        email="admin@vendor.com",
        user_type=UserType.GLOBAL_ADMIN,
        region_id="2",
    )
    User.objects.create(
        first_name="Cisa",
        last_name="U",
        full_name="Cisa U",
        email="person@cisa.dhs.gov",
        user_type=UserType.STANDARD,
        region_id="2",
    )
    _s, _e, target_date = clock
    run_task()
    cm = CustomerMetrics.objects.get(date=target_date, region=2)
    assert cm.external_users == 1
    assert cm.cisa_users == 1


def test_users_without_org_and_active_users_30d(clock):
    """Test users_without_org and active_users (30-day window)."""
    start_dt, end_dt, target_date = clock
    threshold = end_dt - timedelta(days=30)
    User.objects.create(
        first_name="No",
        last_name="Org",
        full_name="No Org",
        email="noorg@example.com",
        user_type=UserType.STANDARD,
        region_id="3",
        last_logged_in=end_dt - timedelta(days=5),
    )
    u_with_org = User.objects.create(
        first_name="Has",
        last_name="Org",
        full_name="Has Org",
        email="hasorg@example.com",
        user_type=UserType.STANDARD,
        region_id="3",
        last_logged_in=threshold - timedelta(seconds=1),
    )
    org = Organization.objects.create(
        acronym="EXT3", retired=False, region_id="3", name="Org 3"
    )
    Role.objects.create(user=u_with_org, organization=org)
    run_task()
    cm = CustomerMetrics.objects.get(date=target_date, region=3)
    assert cm.users_without_org == 1
    assert cm.active_users == 1


def test_users_created_and_approved_window_bounds(clock):
    """Test users_created and users_approved counts with window bounds."""
    start_dt, end_dt, target_date = clock
    u_in = User.objects.create(
        first_name="New",
        last_name="User",
        full_name="New User",
        email="new@ex.com",
        user_type=UserType.STANDARD,
        region_id="4",
        date_approved=start_dt + timedelta(hours=1),
    )
    force_created_at(u_in, start_dt + timedelta(minutes=1))
    u_end = User.objects.create(
        first_name="Late",
        last_name="User",
        full_name="Late User",
        email="late@ex.com",
        user_type=UserType.STANDARD,
        region_id="4",
        date_approved=end_dt,
    )
    force_created_at(u_end, end_dt)
    u_old = User.objects.create(
        first_name="Old",
        last_name="User",
        full_name="Old User",
        email="old@ex.com",
        user_type=UserType.STANDARD,
        region_id="4",
        date_approved=start_dt - timedelta(seconds=1),
    )
    force_created_at(u_old, start_dt - timedelta(seconds=1))
    run_task()
    cm = CustomerMetrics.objects.get(date=target_date, region=4)
    assert cm.users_created == 1
    assert cm.users_approved == 1


def test_pending_count_and_mean_approval_time(clock, python_avg_pending):
    """Test users_invite_pending and mean_approval_time calculations."""
    _s, end_dt, target_date = clock
    u1 = User.objects.create(
        first_name="P1",
        last_name="U",
        full_name="P1 U",
        email="p1@ex.com",
        user_type=UserType.STANDARD,
        region_id="5",
        invite_pending=True,
    )
    force_created_at(u1, end_dt - timedelta(days=2))
    u2 = User.objects.create(
        first_name="P2",
        last_name="U",
        full_name="P2 U",
        email="p2@ex.com",
        user_type=UserType.STANDARD,
        region_id="5",
        invite_pending=True,
    )
    force_created_at(u2, end_dt - timedelta(days=4))
    run_task()
    cm = CustomerMetrics.objects.get(date=target_date, region=5)
    assert cm.users_invite_pending == 2
    assert cm.mean_approval_time is not None
    assert abs(value_in_days(cm.mean_approval_time) - 3.0) < 1e-6


def test_idempotent_update_or_create(clock):
    """Test that running the task twice updates existing rows."""
    _s, _e, target_date = clock
    first = run_task()
    second = run_task()
    expected = len(metrics_mod.REGIONS)
    assert CustomerMetrics.objects.filter(date=target_date).count() == expected
    assert first["created"] == expected and first["updated"] == 0
    assert second["created"] == 0 and second["updated"] == expected


# -------------------------------------------------------------------
# CSV export around CustomerMetrics
# -------------------------------------------------------------------


def test_export_csv_default_fieldnames_filters_yesterday_only(clock):
    """Test export_customer_metrics with default fieldnames and date filtering."""
    _s, _e, target_date = clock
    run_task()
    older_date = target_date - timedelta(days=2)
    CustomerMetrics.objects.create(date=older_date, region=None)
    CustomerMetrics.objects.create(date=older_date, region=1)

    filename, csv_bytes = export_customer_metrics()
    assert filename == "cyhy_dashboard_customer_metrics_{}.csv".format(
        target_date.isoformat()
    )

    header, rows = parse_csv(csv_bytes)
    expected_header = [
        f for f in _default_fieldnames(CustomerMetrics) if f not in ("id", "created_at")
    ]
    assert header == expected_header
    assert len(rows) == len(metrics_mod.REGIONS)


def test_export_csv_with_explicit_fields_and_values(clock):
    """Test export_customer_metrics with explicit fieldnames and known zero values."""
    _s, _e, target_date = clock
    run_task()
    cols = ("date", "region", "users_invite_pending")
    filename, csv_bytes = export_customer_metrics(fieldnames=cols)
    assert filename.endswith("{}.csv".format(target_date.isoformat()))

    header, rows = parse_csv(csv_bytes)
    assert header == list(cols)
    assert len(rows) == len(metrics_mod.REGIONS)
    for idx in (0, len(rows) - 1):
        assert rows[idx][0] == target_date.isoformat()
        assert rows[idx][2] == "0"


def test_export_csv_raises_on_missing_date_field_candidates(clock):
    """Test export_customer_metrics raises ValueError if no date field found."""
    run_task()
    with pytest.raises(ValueError):
        export_customer_metrics(
            date_field_candidates=("does_not_exist", "also_missing")
        )
